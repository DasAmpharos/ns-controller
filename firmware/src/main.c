// ns-controller firmware: a wired Nintendo Switch Pro Controller driven by the brain over UART0.
//
// - USB: Pro Controller descriptors + handshake (procon.c), input report every 8 ms or on any state change.
// - UART0 (GP0 TX, GP1 RX, 1 Mbaud): framed protocol (link.c) -- SET_STATE, MACRO_LOAD/RUN/ABORT, STATUS, logs.
// - Keyframe player (player.c) plays brain macros and the built-in BOOTSEL test sequences on the microsecond clock.
// - Safety: if the brain goes quiet for 2 s and nothing is playing, everything is released. Watchdog 1 s.
#include <string.h>

#include "bootsel.h"
#include "hardware/watchdog.h"
#include "link.h"
#include "log.h"
#include "pico/bootrom.h"
#include "pico/stdlib.h"
#include "player.h"
#include "procon.h"
#include "sequences.h"
#include "serial.h"
#include "tusb.h"

#if defined(CYW43_WL_GPIO_LED_PIN)
#include "pico/cyw43_arch.h"
#endif

#define REPORT_INTERVAL_US 8000  // 0x30 keepalive, same as the Python/Go ports
#define BUTTON_POLL_US 20000  // BOOTSEL poll period (each poll briefly pauses flash access)
#define BUTTON_GAP_US 700000  // presses closer together than this count as one multi-press
#define STATS_INTERVAL_US 60000000
#define WATCHDOG_MS 1000
#define LOG_RESERVE 2048  // TX bytes kept free for protocol replies
#define REBOOT_MAGIC 0x6e734354  // in watchdog scratch[0]: the reboot was asked for

static procon_t s_pc;
static player_t s_player;
static link_t s_link;
static bool s_input_dirty;
static uint64_t s_last_report_us;
static int32_t s_brain_macro = -1;  // id of the brain macro playing, -1 for none / a built-in test
static uint64_t s_macro_start_us;
static bool s_safety_active;
static uint64_t s_now_us;

static struct {
    uint32_t rx;
    uint32_t rx_rumble;
    uint32_t tx_replies;
    uint32_t tx_reports;
    uint32_t mounts;
} s_stats;

static inline uint8_t timer_byte(uint64_t now_us) {
    return (uint8_t)(now_us / 5000);  // ticks every 5 ms, like the Python counter thread
}

static bool input_neutral(void) {
    const procon_input_t *in = &s_pc.input;
    return in->buttons == 0 && in->lx == PROCON_STICK_CENTER && in->ly == PROCON_STICK_CENTER &&
           in->rx == PROCON_STICK_CENTER && in->ry == PROCON_STICK_CENTER;
}

static void set_input(const procon_input_t *in) {
    if (memcmp(&s_pc.input, in, sizeof(*in)) != 0) {
        s_pc.input = *in;
        s_input_dirty = true;  // send a report now instead of waiting for the keepalive
    }
}

static void release_all(void) {
    procon_input_t neutral = {0, PROCON_STICK_CENTER, PROCON_STICK_CENTER, PROCON_STICK_CENTER, PROCON_STICK_CENTER};
    set_input(&neutral);
}

// ---- logging over the link -------------------------------------------------------------------------

static void log_sink(const char *line, size_t len) {
    uint8_t wire[LINK_MAX_WIRE];
    uint8_t payload[LINK_MAX_PAYLOAD];
    if (len > sizeof(payload) - 1) {
        len = sizeof(payload) - 1;
    }
    payload[0] = 1;  // info
    memcpy(payload + 1, line, len);
    size_t n = link_encode(MSG_LOG, 0, payload, len + 1, wire);
    serial_write(wire, n, LOG_RESERVE);  // dropped when the link is backed up: logs never block replies
}

// ---- LED -------------------------------------------------------------------------------------------

static bool s_led_ok;
static bool s_led_on;

static void led_init(void) {
#if defined(CYW43_WL_GPIO_LED_PIN)
    s_led_ok = cyw43_arch_init() == 0;  // Pico W: the LED hangs off the wireless chip
#elif defined(PICO_DEFAULT_LED_PIN)
    gpio_init(PICO_DEFAULT_LED_PIN);
    gpio_set_dir(PICO_DEFAULT_LED_PIN, GPIO_OUT);
    s_led_ok = true;
#endif
}

static void led_set(bool on) {
    if (!s_led_ok || on == s_led_on) {
        return;
    }
    s_led_on = on;
#if defined(CYW43_WL_GPIO_LED_PIN)
    cyw43_arch_gpio_put(CYW43_WL_GPIO_LED_PIN, on);
#elif defined(PICO_DEFAULT_LED_PIN)
    gpio_put(PICO_DEFAULT_LED_PIN, on);
#endif
}

// Blink codes:
//   fast blink (5 Hz)        not configured by a host
//   slow blink (1 Hz)        configured, waiting for the Switch to start input reports
//   solid, off during press  input reports flowing (blinks off whenever a button is held)
//   short flash every 2 s    USB suspended (console asleep)
static void led_task(uint64_t now_us) {
    uint32_t ms = (uint32_t)(now_us / 1000);
    bool on;
    if (tud_suspended()) {
        on = ms % 2000 < 50;
    } else if (!tud_mounted()) {
        on = (ms / 100) % 2;
    } else if (!s_pc.reports_enabled) {
        on = (ms / 500) % 2;
    } else {
        on = s_pc.input.buttons == 0;
    }
    led_set(on);
}

// ---- USB -------------------------------------------------------------------------------------------

static void usb_tx_task(uint64_t now_us) {
    if (!tud_hid_ready()) {
        return;
    }
    const uint8_t *reply = procon_tx_peek(&s_pc);
    if (reply) {
        if (tud_hid_report(0, reply, PROCON_REPORT_SIZE)) {
            log_hex("tx", reply, PROCON_REPORT_SIZE);
            procon_tx_pop(&s_pc);
            s_stats.tx_replies++;
        }
        return;
    }
    if (s_pc.reports_enabled && (s_input_dirty || now_us - s_last_report_us >= REPORT_INTERVAL_US)) {
        uint8_t report[PROCON_REPORT_SIZE];
        procon_build_input_report(&s_pc, timer_byte(now_us), report);
        if (tud_hid_report(0, report, PROCON_REPORT_SIZE)) {
            s_last_report_us = now_us;
            s_input_dirty = false;
            s_stats.tx_reports++;
        }
    }
}

void tud_mount_cb(void) {
    s_stats.mounts++;
    log_printf("usb: configured by host (mount #%lu)", (unsigned long)s_stats.mounts);
    procon_on_mount(&s_pc);
    s_input_dirty = false;
}

void tud_umount_cb(void) {
    log_printf("usb: unconfigured");
    s_pc.reports_enabled = false;
}

void tud_suspend_cb(bool remote_wakeup_en) {
    log_printf("usb: suspend (remote wakeup %s)", remote_wakeup_en ? "allowed" : "not allowed");
}

void tud_resume_cb(void) {
    log_printf("usb: resume");
}

uint16_t tud_hid_get_report_cb(uint8_t instance, uint8_t report_id, hid_report_type_t report_type, uint8_t *buffer,
                               uint16_t reqlen) {
    (void)instance;
    (void)buffer;
    (void)reqlen;
    log_printf("usb: GET_REPORT id %02x type %d (unsupported)", report_id, report_type);
    return 0;
}

void tud_hid_set_report_cb(uint8_t instance, uint8_t report_id, hid_report_type_t report_type, const uint8_t *buffer,
                           uint16_t bufsize) {
    (void)instance;
    (void)report_type;
    // Interrupt OUT endpoint: report_id is 0 and buffer[0] is the report ID.
    // Control SET_REPORT: TinyUSB strips the ID into report_id, so put it back.
    uint8_t pkt[PROCON_REPORT_SIZE + 1];
    uint16_t len;
    if (report_id) {
        if (bufsize > PROCON_REPORT_SIZE) {
            bufsize = PROCON_REPORT_SIZE;
        }
        pkt[0] = report_id;
        memcpy(pkt + 1, buffer, bufsize);
        len = (uint16_t)(bufsize + 1);
    } else {
        len = bufsize > sizeof(pkt) ? sizeof(pkt) : bufsize;
        memcpy(pkt, buffer, len);
    }
    if (len == 0) {
        return;
    }
    s_stats.rx++;
    if (pkt[0] == 0x10) {
        s_stats.rx_rumble++;  // rumble-only packets are frequent and uninteresting
    } else {
        log_hex("rx", pkt, len);
    }
    procon_handle_output(&s_pc, pkt, len, timer_byte(time_us_64()));
}

// ---- playing timelines (brain macros and built-in tests) --------------------------------------------

static void play(const sequence_t *seq, int32_t brain_id) {
    s_brain_macro = brain_id;
    s_macro_start_us = time_us_64();
    player_start(&s_player, seq, s_macro_start_us);
}

static void stop_playing(uint8_t result, const char *why) {
    if (!s_player.running) {
        return;
    }
    log_printf("macro: '%s' stopped (%s)", s_player.seq->name, why);
    player_stop(&s_player, &s_pc.input);
    s_input_dirty = true;
    if (s_brain_macro >= 0) {
        link_send_macro_done(&s_link, (uint16_t)s_brain_macro, result, s_macro_start_us,
                             (uint32_t)(time_us_64() - s_macro_start_us));
    }
    s_brain_macro = -1;
}

static void player_task(uint64_t now_us) {
    if (!s_player.running) {
        return;
    }
    if (!(s_pc.reports_enabled && tud_ready())) {
        stop_playing(MACRO_ABORTED, "Switch connection lost");
        return;
    }
    if (player_update(&s_player, now_us, &s_pc.input)) {
        s_input_dirty = true;  // send the new state immediately
    }
    if (!s_player.running) {
        if (s_brain_macro >= 0) {
            link_send_macro_done(&s_link, (uint16_t)s_brain_macro, MACRO_COMPLETED, s_macro_start_us,
                                 (uint32_t)(now_us - s_macro_start_us));
        } else {
            log_printf("test: '%s' done", s_player.seq->name);
        }
        s_brain_macro = -1;
    }
}

// ---- brain link callbacks ----------------------------------------------------------------------------

static void link_write(void *ctx, const uint8_t *data, size_t len) {
    (void)ctx;
    if (!serial_write(data, len, 0)) {
        log_printf("link: TX buffer full, reply dropped");
    }
}

static bool link_set_state(void *ctx, const procon_input_t *state) {
    (void)ctx;
    if (s_player.running) {
        return false;
    }
    set_input(state);
    return true;
}

static bool link_run(void *ctx, const sequence_t *seq, uint16_t id) {
    (void)ctx;
    if (s_player.running) {
        return false;
    }
    play(seq, id);
    return true;
}

static void link_abort(void *ctx) {
    (void)ctx;
    stop_playing(MACRO_ABORTED, "ABORT from brain");
    release_all();
}

static uint8_t status_flags(void) {
    uint8_t f = 0;
    f |= tud_mounted() ? STATUS_USB_MOUNTED : 0;
    f |= tud_suspended() ? STATUS_SUSPENDED : 0;
    f |= s_pc.reports_enabled ? STATUS_HANDSHAKE_DONE : 0;
    f |= (s_pc.reports_enabled && tud_ready() && s_now_us - s_last_report_us < 100000) ? STATUS_REPORTS_FLOWING : 0;
    f |= s_player.running ? STATUS_MACRO_RUNNING : 0;
    f |= s_safety_active ? STATUS_SAFETY_RELEASE : 0;
    return f;
}

static void link_status(void *ctx, link_status_t *out) {
    (void)ctx;
    out->flags = status_flags();
    out->uptime_ms = (uint32_t)(time_us_64() / 1000);
    out->macro_id = s_brain_macro >= 0 ? (uint16_t)s_brain_macro : 0;
    out->macro_index = s_player.running ? s_player.next : 0;
}

static void link_reboot(void *ctx, bool bootsel) {
    (void)ctx;
    log_printf("reboot%s requested", bootsel ? " to USB bootloader" : "");
    serial_flush(20000);  // the ACK must leave before we go
    if (bootsel) {
        reset_usb_boot(0, 0);
    }
    watchdog_hw->scratch[0] = REBOOT_MAGIC;
    watchdog_reboot(0, 0, 0);
    while (true) {
        tight_loop_contents();
    }
}

static const link_ops_t LINK_OPS = {link_write, link_set_state, link_run, link_abort, link_status, link_reboot};

static void link_task(uint64_t now_us) {
    uint8_t buf[256];
    size_t n;
    while ((n = serial_read(buf, sizeof(buf))) > 0) {
        link_rx(&s_link, buf, n, now_us);
    }
    // Safety release: the brain went quiet. A playing macro is allowed to finish (it ends neutral).
    bool silent = link_silent(&s_link, now_us);
    if (silent && !s_player.running && !input_neutral()) {
        log_printf("safety: no word from the brain for %d ms; releasing everything", LINK_SAFETY_TIMEOUT_US / 1000);
        release_all();
        s_safety_active = true;
    } else if (!silent) {
        s_safety_active = false;
    }
}

static void status_task(void) {
    static uint8_t last = 0xFF;
    uint8_t flags = status_flags();
    if (flags != last) {
        last = flags;
        link_send_status_changed(&s_link);
    }
}

// ---- BOOTSEL test sequences ---------------------------------------------------------------------------

static void on_presses(int count) {
    if (count < 1 || count > SEQUENCE_COUNT) {
        log_printf("test: %d presses; use 1-%d", count, SEQUENCE_COUNT);
        return;
    }
    if (!(s_pc.reports_enabled && tud_ready())) {
        log_printf("test: not connected to a Switch yet (LED should be solid first)");
        return;
    }
    const sequence_t *seq = &SEQUENCES[count - 1];
    log_printf("test: playing '%s' (%u keyframes)", seq->name, seq->count);
    play(seq, -1);
}

static void button_task(uint64_t now_us) {
    static uint64_t next_poll_us, last_edge_us;
    static bool was_pressed;
    static int presses;

    if (now_us < next_poll_us) {
        return;
    }
    next_poll_us = now_us + BUTTON_POLL_US;
    bool pressed = bootsel_pressed();
    if (pressed != was_pressed) {
        was_pressed = pressed;
        last_edge_us = now_us;
        if (pressed) {
            if (s_player.running) {
                stop_playing(MACRO_ABORTED, "BOOTSEL pressed");
                presses = -1;  // swallow this press
            } else if (presses >= 0) {
                presses++;
            }
        } else if (presses < 0) {
            presses = 0;
        }
    }
    if (!pressed && presses > 0 && now_us - last_edge_us > BUTTON_GAP_US) {
        on_presses(presses);
        presses = 0;
    }
}

static void stats_task(uint64_t now_us) {
    static uint64_t next_us = STATS_INTERVAL_US;
    if (now_us < next_us) {
        return;
    }
    next_us += STATS_INTERVAL_US;
    log_printf("stats: flags=0x%02x lights=0x%02x rx=%lu rumble=%lu replies=%lu inputs=%lu link_bad=%lu "
               "rx_overflow=%lu",
               status_flags(), s_pc.player_lights, (unsigned long)s_stats.rx, (unsigned long)s_stats.rx_rumble,
               (unsigned long)s_stats.tx_replies, (unsigned long)s_stats.tx_reports, (unsigned long)s_link.bad_frames,
               (unsigned long)serial_rx_overflows());
}

int main(void) {
    uint8_t reset_reason = 0;  // power on
    if (watchdog_caused_reboot()) {
        reset_reason = watchdog_hw->scratch[0] == REBOOT_MAGIC ? 2 : 1;  // asked for / watchdog
    }
    watchdog_hw->scratch[0] = 0;

    serial_init(SERIAL_BAUD);
    link_init(&s_link, &LINK_OPS, NULL, FW_HASH, "ns-controller " FW_VERSION " (" PICO_BOARD ")");
    log_init(log_sink);
    link_send_boot(&s_link, reset_reason);
    log_printf("ns-controller firmware %s (%s)%s", FW_VERSION, PICO_BOARD,
               reset_reason == 1 ? " -- rebooted by WATCHDOG" : "");

    led_init();
    procon_init(&s_pc);
    tud_init(0);
    watchdog_enable(WATCHDOG_MS, true);

    while (true) {
        uint64_t now_us = time_us_64();
        s_now_us = now_us;
        tud_task();
        usb_tx_task(now_us);
        link_task(now_us);
        button_task(now_us);
        player_task(now_us);
        usb_tx_task(now_us);  // push a state change immediately rather than next iteration
        status_task();
        led_task(now_us);
        stats_task(now_us);
        serial_drain();
        watchdog_update();
    }
}
