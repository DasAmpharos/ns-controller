// Brain <-> Pico serial protocol (docs/protocol.md in ns-automation; nsctl implements the brain side).
//
//   wire: COBS( type:u8 | seq:u8 | payload | crc16:u16le ) | 0x00
//
// Hardware-free: the firmware feeds received bytes in with link_rx() and supplies callbacks for the effects
// (write bytes, set state, run/abort a macro, status, reboot). Host-tested in test/test_link.c.
#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "player.h"
#include "procon.h"

#define LINK_PROTO_VERSION 1
#define LINK_MAX_FRAME 256  // decoded: type + seq + payload + crc
#define LINK_MAX_PAYLOAD (LINK_MAX_FRAME - 4)
#define LINK_MAX_WIRE (LINK_MAX_FRAME + LINK_MAX_FRAME / 254 + 2)  // COBS overhead + delimiter
#define LINK_MAX_KEYFRAMES 2048
#define LINK_KEYFRAMES_PER_LOAD 15
#define LINK_SAFETY_TIMEOUT_US 2000000

enum {
    // brain -> Pico
    MSG_HELLO = 0x01,
    MSG_PING = 0x02,
    MSG_GET_STATUS = 0x03,
    MSG_SET_STATE = 0x10,
    MSG_MACRO_LOAD = 0x20,
    MSG_MACRO_RUN = 0x21,
    MSG_ABORT = 0x22,
    MSG_REBOOT = 0x30,
    // Pico -> brain
    MSG_ACK = 0x80,
    MSG_HELLO_REPLY = 0x81,
    MSG_STATUS = 0x82,
    MSG_MACRO_DONE = 0x83,  // seq 0
    MSG_BOOT = 0x84,  // seq 0
    MSG_STATUS_CHANGED = 0x85,  // seq 0
    MSG_LOG = 0x8F,  // seq 0
};

enum {
    ACK_OK = 0,
    ACK_BUSY = 1,
    ACK_BAD_ARG = 2,
    ACK_UNKNOWN_TYPE = 3,
    ACK_VERSION_MISMATCH = 4,
    ACK_MACRO_INCOMPLETE = 5,
    ACK_NOT_READY = 6,
};

enum {
    STATUS_USB_MOUNTED = 1 << 0,
    STATUS_SUSPENDED = 1 << 1,
    STATUS_HANDSHAKE_DONE = 1 << 2,
    STATUS_REPORTS_FLOWING = 1 << 3,
    STATUS_MACRO_RUNNING = 1 << 4,
    STATUS_SAFETY_RELEASE = 1 << 5,
};

enum { MACRO_COMPLETED = 0, MACRO_ABORTED = 1, MACRO_SAFETY = 2 };

typedef struct {
    uint8_t flags;
    uint32_t uptime_ms;
    uint16_t macro_id;
    uint16_t macro_index;
} link_status_t;

typedef struct {
    void (*write)(void *ctx, const uint8_t *data, size_t len);  // encoded wire bytes
    bool (*set_state)(void *ctx, const procon_input_t *state);  // false: busy (macro running)
    bool (*run_macro)(void *ctx, const sequence_t *seq, uint16_t macro_id);  // false: busy / not ready
    void (*abort_macro)(void *ctx);
    void (*get_status)(void *ctx, link_status_t *out);
    void (*reboot)(void *ctx, bool bootsel);  // called after the ACK has been written
} link_ops_t;

typedef struct {
    const link_ops_t *ops;
    void *ctx;
    uint32_t fw_version;
    const char *fw_text;

    uint8_t rx[LINK_MAX_WIRE];
    size_t rx_len;
    bool rx_overflow;
    uint64_t last_rx_us;  // last valid frame
    bool heard;  // a valid frame has arrived since boot

    uint8_t last_seq;  // de-duplication of resends
    uint8_t last_reply[LINK_MAX_WIRE];
    size_t last_reply_len;

    keyframe_t frames[LINK_MAX_KEYFRAMES];
    sequence_t seq;
    uint16_t macro_id;
    uint16_t total;
    uint16_t loaded;  // keyframes received contiguously from 0

    uint32_t bad_frames;
} link_t;

void link_init(link_t *link, const link_ops_t *ops, void *ctx, uint32_t fw_version, const char *fw_text);

// Feed received bytes; complete frames are decoded and handled immediately.
void link_rx(link_t *link, const uint8_t *data, size_t len, uint64_t now_us);

// Unsolicited messages (seq 0).
void link_send(link_t *link, uint8_t type, const uint8_t *payload, size_t len);
void link_send_macro_done(link_t *link, uint16_t macro_id, uint8_t result, uint64_t start_us, uint32_t duration_us);
void link_send_status_changed(link_t *link);
void link_send_boot(link_t *link, uint8_t reset_reason);
void link_send_log(link_t *link, uint8_t level, const char *text, size_t len);

// True when the brain has gone quiet for LINK_SAFETY_TIMEOUT_US (it had been heard from at least once).
bool link_silent(const link_t *link, uint64_t now_us);

// Building blocks (exposed for tests and the host tools).
uint16_t link_crc16(const uint8_t *data, size_t len);
size_t link_cobs_encode(const uint8_t *in, size_t len, uint8_t *out);  // no delimiter
size_t link_cobs_decode(const uint8_t *in, size_t len, uint8_t *out, size_t out_max);  // 0 on error
size_t link_encode(uint8_t type, uint8_t seq, const uint8_t *payload, size_t len, uint8_t *out);  // with 0x00
void link_pack_state(const procon_input_t *in, uint8_t out[12]);
void link_unpack_state(const uint8_t in[12], procon_input_t *out);
