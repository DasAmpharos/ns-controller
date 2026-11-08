// Phase 1 hardware spike: enumerate as a wired Pro Controller, complete the Switch handshake and stream
// input reports. Press BOOTSEL to play a built-in test sequence (1 press: input test, 2: nxbt demo; any press
// while one runs stops it). Logs everything over UART0 (GP0 TX, 115200 8N1).
#include <string.h>

#include "bootsel.h"
#include "hardware/watchdog.h"
#include "log.h"
#include "pico/stdlib.h"
#include "player.h"
#include "procon.h"
#include "sequences.h"
#include "tusb.h"

#if defined(CYW43_WL_GPIO_LED_PIN)
#include "pico/cyw43_arch.h"
#endif

#define REPORT_INTERVAL_US 8000      // 0x30 keepalive, same as the Python/Go ports
#define BUTTON_POLL_US 20000      // BOOTSEL poll period (each poll briefly pauses flash access)
#define BUTTON_GAP_US 700000      // presses closer together than this count as one multi-press
#define STATS_INTERVAL_US 10000000
#define WATCHDOG_MS 1000

static procon_t s_pc;
static bool s_input_dirty;
static uint64_t s_last_report_us;

static struct {
    uint32_t rx;
    uint32_t rx_rumble;
    uint32_t tx_replies;
    uint32_t tx_reports;
    uint32_t sequences;
    uint32_t mounts;
    uint32_t suspends;
} s_stats;

static inline uint8_t timer_byte(uint64_t now_us) {
    return (uint8_t)(now_us / 5000);  // ticks every 5 ms, like the Python counter thread
}

// ---- LED -----------------------------------------------------------------------------------------

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
//   solid, off during press  input reports flowing (blinks off whenever a test presses a button)
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

// ---- USB -----------------------------------------------------------------------------------------

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
    s_stats.suspends++;
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

// ---- Test sequences (BOOTSEL) ----------------------------------------------------------------------

static player_t s_player;

static void sequence_stop(const char *why) {
    if (s_player.running) {
        log_printf("test: '%s' stopped (%s)", s_player.seq->name, why);
    }
    player_stop(&s_player, &s_pc.input);
    s_input_dirty = true;
}

static void on_presses(int count) {
    if (count < 1 || count > SEQUENCE_COUNT) {
        log_printf("test: %d presses; use 1-%d:", count, SEQUENCE_COUNT);
        for (int i = 0; i < SEQUENCE_COUNT; i++) {
            log_printf("test:   %d = %s", i + 1, SEQUENCES[i].name);
        }
        return;
    }
    if (!(s_pc.reports_enabled && tud_ready())) {
        log_printf("test: not connected to a Switch yet (LED should be solid first)");
        return;
    }
    const sequence_t *seq = &SEQUENCES[count - 1];
    const keyframe_t *last = &seq->frames[seq->count - 1];
    s_stats.sequences++;
    log_printf("test: playing '%s' (%u keyframes, %lu.%03lu s)", seq->name, seq->count,
               (unsigned long)(last->t_ms / 1000), (unsigned long)(last->t_ms % 1000));
    player_start(&s_player, seq, time_us_64());
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
                sequence_stop("button pressed");
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

static void player_task(uint64_t now_us) {
    if (!s_player.running) {
        return;
    }
    if (!(s_pc.reports_enabled && tud_ready())) {
        sequence_stop("connection lost");
        return;
    }
    if (player_update(&s_player, now_us, &s_pc.input)) {
        s_input_dirty = true;  // send the new state immediately
    }
    if (!s_player.running) {
        log_printf("test: '%s' done", s_player.seq->name);
    }
}

static void stats_task(uint64_t now_us) {
    static uint64_t next_us = STATS_INTERVAL_US;
    if (now_us < next_us) {
        return;
    }
    next_us += STATS_INTERVAL_US;
    log_printf("stats: mounted=%d suspended=%d reports=%d lights=0x%02x rx=%lu rumble=%lu replies=%lu "
               "inputs=%lu tests=%lu dropped=%lu",
               tud_mounted(), tud_suspended(), s_pc.reports_enabled, s_pc.player_lights, (unsigned long)s_stats.rx,
               (unsigned long)s_stats.rx_rumble, (unsigned long)s_stats.tx_replies, (unsigned long)s_stats.tx_reports,
               (unsigned long)s_stats.sequences, (unsigned long)s_pc.txq_dropped);
}

int main(void) {
    bool watchdog_reboot = watchdog_caused_reboot();
    log_init();
    log_printf("ns-controller firmware %s (%s)%s", FW_VERSION, PICO_BOARD,
               watchdog_reboot ? " -- rebooted by WATCHDOG" : "");

    led_init();
    procon_init(&s_pc);
    tud_init(0);
    watchdog_enable(WATCHDOG_MS, true);
    log_printf("usb: started, waiting for host. BOOTSEL: 1 press = %s, 2 = %s", SEQUENCES[0].name,
               SEQUENCE_COUNT > 1 ? SEQUENCES[1].name : "-");

    while (true) {
        uint64_t now_us = time_us_64();
        tud_task();
        usb_tx_task(now_us);
        button_task(now_us);
        player_task(now_us);
        usb_tx_task(now_us);  // push a state change immediately rather than next iteration
        led_task(now_us);
        stats_task(now_us);
        log_drain();
        watchdog_update();
    }
}
