// Pro Controller USB protocol: handshake replies, subcommand replies, input reports.
//
// Hardware-free: no Pico SDK or TinyUSB includes, so it builds and runs in host unit tests.
// The caller feeds OUT reports in (procon_handle_output), drains queued replies
// (procon_tx_peek / procon_tx_pop), and builds periodic 0x30 input reports.
#pragma once

#include <stdbool.h>
#include <stdint.h>

#define PROCON_REPORT_SIZE 64
#define PROCON_TXQ_LEN 8

// Button bits. Layout matches report bytes 3..5: bits 0-7 = byte 3 (right side),
// 8-15 = byte 4 (shared), 16-23 = byte 5 (left side).
#define PROCON_BTN_Y (1u << 0)
#define PROCON_BTN_X (1u << 1)
#define PROCON_BTN_B (1u << 2)
#define PROCON_BTN_A (1u << 3)
#define PROCON_BTN_R (1u << 6)
#define PROCON_BTN_ZR (1u << 7)
#define PROCON_BTN_MINUS (1u << 8)
#define PROCON_BTN_PLUS (1u << 9)
#define PROCON_BTN_RSTICK (1u << 10)
#define PROCON_BTN_LSTICK (1u << 11)
#define PROCON_BTN_HOME (1u << 12)
#define PROCON_BTN_CAPTURE (1u << 13)
#define PROCON_BTN_DOWN (1u << 16)
#define PROCON_BTN_UP (1u << 17)
#define PROCON_BTN_RIGHT (1u << 18)
#define PROCON_BTN_LEFT (1u << 19)
#define PROCON_BTN_L (1u << 22)
#define PROCON_BTN_ZL (1u << 23)

#define PROCON_STICK_CENTER 0x800  // 12-bit stick axes, 0x000..0xFFF

typedef struct {
    uint32_t buttons;  // PROCON_BTN_* bits
    uint16_t lx, ly, rx, ry;
} procon_input_t;

typedef struct {
    bool reports_enabled;  // 0x80 0x04 seen and not stopped by 0x80 0x05
    uint8_t player_lights;  // last subcommand 0x30 argument
    procon_input_t input;

    uint8_t txq[PROCON_TXQ_LEN][PROCON_REPORT_SIZE];
    uint8_t txq_head;
    uint8_t txq_count;
    uint32_t txq_dropped;
} procon_t;

void procon_init(procon_t *pc);

// Device was (re)configured by the host: reset session state and queue the
// unsolicited 0x81 packets the Linux gadget implementation sent on open.
void procon_on_mount(procon_t *pc);

// Process one OUT report from the host. buf[0] is the report ID (0x80, 0x01, 0x10, ...).
// `timer` is the free-running timer byte placed in 0x21 replies.
void procon_handle_output(procon_t *pc, const uint8_t *buf, uint16_t len, uint8_t timer);

// Queued replies, oldest first. peek returns NULL when empty.
const uint8_t *procon_tx_peek(const procon_t *pc);
void procon_tx_pop(procon_t *pc);

// Full 0x30 standard input report for the current input state.
void procon_build_input_report(const procon_t *pc, uint8_t timer, uint8_t out[PROCON_REPORT_SIZE]);

// The 11-byte input block shared by 0x21 and 0x30 reports (connection/battery, buttons, sticks, vibrator).
void procon_pack_input(const procon_input_t *in, uint8_t out[11]);

// Read emulated SPI flash. Unmapped addresses read as 0xFF (erased flash).
void procon_spi_read(uint32_t addr, uint8_t *out, uint8_t len);

// Logging hook. The firmware provides a non-blocking implementation; tests provide a stub.
void procon_log(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
