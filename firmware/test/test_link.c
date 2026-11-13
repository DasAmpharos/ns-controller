// Host tests for the serial protocol engine (link.c).
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "link.h"

static int checks, failures;

void procon_log(const char *fmt, ...) {
    (void)fmt;
}

#define EXPECT(cond, ...)                                                                                              \
    do {                                                                                                               \
        checks++;                                                                                                      \
        if (!(cond)) {                                                                                                 \
            failures++;                                                                                                \
            fprintf(stderr, "FAIL %s:%d: ", __FILE__, __LINE__);                                                       \
            fprintf(stderr, __VA_ARGS__);                                                                              \
            fprintf(stderr, "\n");                                                                                     \
        }                                                                                                              \
    } while (0)

// ── fake device ──────────────────────────────────────────────────────────────

static struct {
    uint8_t out[8192];
    size_t out_len;
    int set_state_calls, run_calls, abort_calls, reboots;
    bool bootsel, running;
    procon_input_t state;
    const sequence_t *seq;
    uint16_t macro_id;
} dev;

static void w(void *ctx, const uint8_t *d, size_t n) {
    (void)ctx;
    memcpy(dev.out + dev.out_len, d, n);
    dev.out_len += n;
}
static bool set_state(void *ctx, const procon_input_t *s) {
    (void)ctx;
    dev.set_state_calls++;
    if (dev.running) {
        return false;
    }
    dev.state = *s;
    return true;
}
static bool run_macro(void *ctx, const sequence_t *s, uint16_t id) {
    (void)ctx;
    dev.run_calls++;
    if (dev.running) {
        return false;
    }
    dev.seq = s;
    dev.macro_id = id;
    dev.running = true;
    return true;
}
static void abort_macro(void *ctx) {
    (void)ctx;
    dev.abort_calls++;
    dev.running = false;
}
static void get_status(void *ctx, link_status_t *st) {
    (void)ctx;
    st->flags = (uint8_t)(STATUS_USB_MOUNTED | (dev.running ? STATUS_MACRO_RUNNING : 0));
    st->uptime_ms = 1234;
    st->macro_id = dev.macro_id;
    st->macro_index = 0;
}
static void reboot(void *ctx, bool bootsel) {
    (void)ctx;
    dev.reboots++;
    dev.bootsel = bootsel;
}
static const link_ops_t OPS = {w, set_state, run_macro, abort_macro, get_status, reboot};

static link_t *fresh(void) {
    static link_t link;
    memset(&dev, 0, sizeof(dev));
    link_init(&link, &OPS, NULL, 0xabc1234, "test-fw");
    return &link;
}

// Send a frame; return the single reply decoded into type/seq/payload.
typedef struct {
    int ok;
    uint8_t type, seq;
    uint8_t payload[LINK_MAX_PAYLOAD];
    size_t len;
} msg_t;

static msg_t decode_out(size_t from) {
    msg_t m = {0};
    uint8_t frame[LINK_MAX_FRAME];
    size_t end = from;
    while (end < dev.out_len && dev.out[end] != 0) {
        end++;
    }
    size_t n = link_cobs_decode(dev.out + from, end - from, frame, sizeof(frame));
    if (n < 4 || link_crc16(frame, n - 2) != (uint16_t)(frame[n - 2] | frame[n - 1] << 8)) {
        return m;
    }
    m.ok = 1;
    m.type = frame[0];
    m.seq = frame[1];
    m.len = n - 4;
    memcpy(m.payload, frame + 2, m.len);
    return m;
}

static msg_t send(link_t *link, uint8_t type, uint8_t seq, const uint8_t *payload, size_t len) {
    uint8_t wire[LINK_MAX_WIRE];
    size_t n = link_encode(type, seq, payload, len, wire);
    size_t before = dev.out_len;
    link_rx(link, wire, n, 1000);
    return decode_out(before);
}

// ── tests ────────────────────────────────────────────────────────────────────

static void test_crc_and_cobs(void) {
    EXPECT(link_crc16((const uint8_t *)"123456789", 9) == 0x29B1, "CRC-16/CCITT-FALSE check value");
    srand(7);
    for (int round = 0; round < 500; round++) {
        uint8_t in[300], enc[320], dec[300];
        size_t len = (size_t)(rand() % 300);
        for (size_t i = 0; i < len; i++) {
            in[i] = (rand() % 4 == 0) ? 0 : (uint8_t)rand();
        }
        if (round == 1) {
            len = 260;
            memset(in, 0x11, len);  // long zero-free run crosses the 254-byte block limit
        }
        size_t e = link_cobs_encode(in, len, enc);
        int has_zero = 0;
        for (size_t i = 0; i < e; i++) {
            has_zero |= enc[i] == 0;
        }
        size_t d = link_cobs_decode(enc, e, dec, sizeof(dec));
        EXPECT(!has_zero && d == len && memcmp(in, dec, len) == 0, "cobs round trip, len %zu", len);
    }
}

static void test_hello(void) {
    link_t *link = fresh();
    uint8_t v[2] = {LINK_PROTO_VERSION, 0};
    msg_t m = send(link, MSG_HELLO, 1, v, 2);
    EXPECT(m.ok && m.type == MSG_HELLO_REPLY && m.seq == 1, "hello reply");
    EXPECT(m.payload[0] == LINK_PROTO_VERSION && m.payload[6] == (LINK_MAX_KEYFRAMES & 0xFF), "hello fields");
    EXPECT(m.len == 8 + 7 && memcmp(m.payload + 8, "test-fw", 7) == 0, "hello carries fw text");
}

static void test_set_state_and_resend(void) {
    link_t *link = fresh();
    procon_input_t st = {PROCON_BTN_A | PROCON_BTN_ZL, 0, 4095, 2048, 100};
    uint8_t buf[12];
    link_pack_state(&st, buf);
    msg_t m = send(link, MSG_SET_STATE, 5, buf, 12);
    EXPECT(m.ok && m.type == MSG_ACK && m.seq == 5 && m.payload[0] == ACK_OK, "set_state acked");
    EXPECT(dev.state.buttons == st.buttons && dev.state.ly == 4095 && dev.state.ry == 100, "state applied");
    m = send(link, MSG_SET_STATE, 5, buf, 12);  // resend with the same seq
    EXPECT(m.ok && m.payload[0] == ACK_OK && dev.set_state_calls == 1, "resend replays ACK without re-running");
    m = send(link, MSG_SET_STATE, 6, buf, 11);
    EXPECT(m.payload[0] == ACK_BAD_ARG, "short state rejected");
}

static void load(link_t *link, uint8_t seq, uint16_t id, uint16_t total, uint16_t offset, uint8_t count,
                 msg_t *out) {
    uint8_t p[7 + 16 * LINK_KEYFRAMES_PER_LOAD];
    p[0] = (uint8_t)id;
    p[1] = (uint8_t)(id >> 8);
    p[2] = (uint8_t)total;
    p[3] = (uint8_t)(total >> 8);
    p[4] = (uint8_t)offset;
    p[5] = (uint8_t)(offset >> 8);
    p[6] = count;
    for (uint8_t i = 0; i < count; i++) {
        uint8_t *k = p + 7 + 16 * i;
        uint32_t t = (uint32_t)(offset + i) * 50000;
        k[0] = (uint8_t)t;
        k[1] = (uint8_t)(t >> 8);
        k[2] = (uint8_t)(t >> 16);
        k[3] = (uint8_t)(t >> 24);
        procon_input_t st = {(offset + i) % 2 ? PROCON_BTN_B : 0, 2048, 2048, 2048, 2048};
        link_pack_state(&st, k + 4);
    }
    *out = send(link, MSG_MACRO_LOAD, seq, p, 7 + 16 * (size_t)count);
}

static void test_macro_load_and_run(void) {
    link_t *link = fresh();
    msg_t m;
    uint8_t id[2] = {7, 0};
    m = send(link, MSG_MACRO_RUN, 1, id, 2);
    EXPECT(m.payload[0] == ACK_MACRO_INCOMPLETE, "run with nothing loaded");
    load(link, 2, 7, 20, 0, 15, &m);
    EXPECT(m.payload[0] == ACK_OK, "first chunk");
    m = send(link, MSG_MACRO_RUN, 3, id, 2);
    EXPECT(m.payload[0] == ACK_MACRO_INCOMPLETE, "run with 15/20 loaded");
    load(link, 4, 7, 20, 15, 5, &m);
    EXPECT(m.payload[0] == ACK_OK, "second chunk");
    m = send(link, MSG_MACRO_RUN, 5, id, 2);
    EXPECT(m.payload[0] == ACK_OK && dev.running && dev.seq->count == 20 && dev.macro_id == 7, "run accepted");
    EXPECT(dev.seq->frames[19].t_us == 19 * 50000 && dev.seq->frames[19].buttons == PROCON_BTN_B, "frames copied");
    load(link, 6, 8, 3, 0, 3, &m);
    EXPECT(m.payload[0] == ACK_BUSY, "load while running is busy");
    uint8_t st[12] = {0};
    m = send(link, MSG_SET_STATE, 7, st, 12);
    EXPECT(m.payload[0] == ACK_BUSY, "set_state while running is busy");
    m = send(link, MSG_ABORT, 8, NULL, 0);
    EXPECT(m.payload[0] == ACK_OK && dev.abort_calls == 1 && !dev.running, "abort");
}

static void test_macro_load_errors(void) {
    link_t *link = fresh();
    msg_t m;
    load(link, 1, 1, 30, 15, 15, &m);
    EXPECT(m.payload[0] == ACK_BAD_ARG, "gap (offset 15 before 0) rejected");
    load(link, 2, 1, 10, 5, 6, &m);
    EXPECT(m.payload[0] == ACK_BAD_ARG, "chunk past total rejected");
    load(link, 3, 1, 5, 0, 5, &m);
    EXPECT(m.payload[0] == ACK_OK, "small macro");
    load(link, 4, 2, 5, 0, 2, &m);  // new id replaces the old macro
    uint8_t old_id[2] = {1, 0};
    m = send(link, MSG_MACRO_RUN, 5, old_id, 2);
    EXPECT(m.payload[0] == ACK_MACRO_INCOMPLETE, "old macro discarded by a new id");
}

static void test_robustness(void) {
    link_t *link = fresh();
    uint8_t wire[LINK_MAX_WIRE];
    size_t n = link_encode(MSG_PING, 9, NULL, 0, wire);
    wire[1] ^= 0x40;  // corrupt
    link_rx(link, wire, n, 0);
    EXPECT(dev.out_len == 0 && link->bad_frames == 1, "bad CRC dropped silently");
    uint8_t junk[] = {0x13, 0x37, 0x00, 0x00};
    link_rx(link, junk, sizeof(junk), 0);
    n = link_encode(MSG_PING, 10, NULL, 0, wire);
    link_rx(link, wire, 3, 0);  // split across reads
    link_rx(link, wire + 3, n - 3, 0);
    msg_t m = decode_out(0);
    EXPECT(m.ok && m.type == MSG_ACK && m.seq == 10, "frame after junk, split across reads");
    m = send(link, 0x55, 11, NULL, 0);
    EXPECT(m.payload[0] == ACK_UNKNOWN_TYPE, "unknown type");
}

static void test_safety_and_reboot(void) {
    link_t *link = fresh();
    EXPECT(!link_silent(link, 10000000), "never heard: not silent (no brain yet)");
    send(link, MSG_PING, 1, NULL, 0);  // at t=1000 us
    EXPECT(!link_silent(link, 1000 + LINK_SAFETY_TIMEOUT_US), "within timeout");
    EXPECT(link_silent(link, 1001 + LINK_SAFETY_TIMEOUT_US), "silent after timeout");
    uint8_t b = 1;
    msg_t m = send(link, MSG_REBOOT, 2, &b, 1);
    EXPECT(m.payload[0] == ACK_OK && dev.reboots == 1 && dev.bootsel, "reboot to bootloader after ACK");
}

static void test_hello_resets_dedupe(void) {
    link_t *link = fresh();
    send(link, MSG_PING, 1, NULL, 0);
    uint8_t v[2] = {LINK_PROTO_VERSION, 0};
    send(link, MSG_HELLO, 1, v, 2);  // a restarted brain begins at seq 1 again
    procon_input_t st = {PROCON_BTN_A, 2048, 2048, 2048, 2048};
    uint8_t buf[12];
    link_pack_state(&st, buf);
    msg_t m = send(link, MSG_SET_STATE, 2, buf, 12);
    EXPECT(m.payload[0] == ACK_OK && dev.set_state_calls == 1, "commands after HELLO run");
}

static void test_unsolicited(void) {
    link_t *link = fresh();
    link_send_macro_done(link, 7, MACRO_COMPLETED, 0x0102030405060708ULL, 123456);
    msg_t m = decode_out(0);
    EXPECT(m.ok && m.type == MSG_MACRO_DONE && m.seq == 0 && m.len == 15 && m.payload[0] == 7, "macro done");
    EXPECT(m.payload[3] == 0x08 && m.payload[10] == 0x01, "start_us little-endian u64");
    size_t before = dev.out_len;
    link_send_log(link, 1, "hello", 5);
    m = decode_out(before);
    EXPECT(m.ok && m.type == MSG_LOG && m.payload[0] == 1 && memcmp(m.payload + 1, "hello", 5) == 0, "log frame");
}

int main(void) {
    test_crc_and_cobs();
    test_hello();
    test_set_state_and_resend();
    test_macro_load_and_run();
    test_macro_load_errors();
    test_robustness();
    test_safety_and_reboot();
    test_hello_resets_dedupe();
    test_unsolicited();
    printf("%d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
