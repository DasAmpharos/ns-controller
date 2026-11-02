// Pro Controller USB protocol. Ported from ns_controller/controller.py and go-server controller.go
// (both drove the same Switch consoles successfully through a Linux USB gadget).
//
// Deliberate differences from the ports:
//   - Unknown UART subcommands get a plain ACK instead of silence (a real controller ACKs everything).
//   - SPI reads outside the two captured pages return 0xFF (erased flash) instead of a NACK/short reply.
//   - 0x80 0x04 / 0x05 just toggle a flag; there are no report threads to leak (audit S4/S5).
#include "procon.h"

#include <string.h>

#include "procon_data.h"

// Reply to 0x80 0x01: [0x00, controller type 0x03 (Pro Controller), MAC address x6].
static const uint8_t k_mac_reply[] = {0x00, 0x03, 0x00, 0x00, 0x5e, 0x00, 0x53, 0x5e};

// Reply to subcommand 0x02 (device info): firmware 3.72, type Pro Controller, 0x02, MAC, 0x03?, use SPI colours.
static const uint8_t k_device_info[] = {0x03, 0x48, 0x03, 0x02, 0x5e, 0x53, 0x00, 0x5e, 0x00, 0x00, 0x03, 0x01};

// Reply to subcommand 0x21 (set NFC/IR MCU config).
static const uint8_t k_mcu_config[] = {0x01, 0x00, 0xff, 0x00, 0x03, 0x00, 0x05, 0x01};

// Offset of the subcommand payload inside a 0x21 reply: id, timer, 11-byte input block, ack, subcommand id.
#define UART_REPLY_DATA_OFFSET 15
#define UART_REPLY_MAX_DATA (PROCON_REPORT_SIZE - UART_REPLY_DATA_OFFSET)

void procon_init(procon_t *pc) {
    memset(pc, 0, sizeof(*pc));
    pc->input.lx = pc->input.ly = pc->input.rx = pc->input.ry = PROCON_STICK_CENTER;
}

static uint8_t *tx_push(procon_t *pc) {
    if (pc->txq_count == PROCON_TXQ_LEN) {
        pc->txq_dropped++;
        procon_log("txq full, dropping reply");
        return NULL;
    }
    uint8_t idx = (uint8_t)((pc->txq_head + pc->txq_count) % PROCON_TXQ_LEN);
    pc->txq_count++;
    memset(pc->txq[idx], 0, PROCON_REPORT_SIZE);
    return pc->txq[idx];
}

const uint8_t *procon_tx_peek(const procon_t *pc) {
    return pc->txq_count ? pc->txq[pc->txq_head] : NULL;
}

void procon_tx_pop(procon_t *pc) {
    if (pc->txq_count) {
        pc->txq_head = (uint8_t)((pc->txq_head + 1) % PROCON_TXQ_LEN);
        pc->txq_count--;
    }
}

static void reply_usb(procon_t *pc, uint8_t cmd, const uint8_t *data, uint8_t len) {
    uint8_t *out = tx_push(pc);
    if (!out) {
        return;
    }
    out[0] = 0x81;
    out[1] = cmd;
    if (len) {
        memcpy(out + 2, data, len);
    }
}

static void reply_uart(procon_t *pc, uint8_t timer, bool ack, uint8_t subcmd, const uint8_t *data, uint8_t len) {
    uint8_t *out = tx_push(pc);
    if (!out) {
        return;
    }
    if (len > UART_REPLY_MAX_DATA) {
        len = UART_REPLY_MAX_DATA;
    }
    out[0] = 0x21;
    out[1] = timer;
    procon_pack_input(&pc->input, out + 2);
    uint8_t ack_byte = 0x00;
    if (ack) {
        ack_byte = 0x80;
        if (len) {
            ack_byte |= subcmd;
        }
    }
    out[13] = ack_byte;
    out[14] = subcmd;
    if (len) {
        memcpy(out + UART_REPLY_DATA_OFFSET, data, len);
    }
}

void procon_on_mount(procon_t *pc) {
    procon_input_t input = pc->input;
    uint32_t dropped = pc->txq_dropped;
    procon_init(pc);
    pc->input = input;
    pc->txq_dropped = dropped;
    reply_usb(pc, 0x03, NULL, 0);
    reply_usb(pc, 0x01, (const uint8_t[]){0x00, 0x03}, 2);
}

void procon_spi_read(uint32_t addr, uint8_t *out, uint8_t len) {
    for (uint8_t i = 0; i < len; i++) {
        uint32_t a = addr + i;
        if (a >= 0x6000 && a < 0x6000 + PROCON_SPI_6000_LEN) {
            out[i] = procon_spi_6000[a - 0x6000];
        } else if (a >= 0x8000 && a < 0x8000 + PROCON_SPI_8000_LEN) {
            out[i] = procon_spi_8000[a - 0x8000];
        } else {
            out[i] = 0xff;
        }
    }
}

static void handle_usb_cmd(procon_t *pc, uint8_t cmd) {
    switch (cmd) {
    case 0x01:  // status / MAC request
        procon_log("usb 80 01: status");
        reply_usb(pc, cmd, k_mac_reply, sizeof(k_mac_reply));
        break;
    case 0x02:  // handshake
    case 0x03:  // set baud rate
        procon_log("usb 80 %02x: %s", cmd, cmd == 0x02 ? "handshake" : "baud rate");
        reply_usb(pc, cmd, NULL, 0);
        break;
    case 0x04:  // USB HID only, no timeout: start streaming input reports
        procon_log("usb 80 04: input reports on");
        pc->reports_enabled = true;
        break;
    case 0x05:  // back to Bluetooth-style operation: stop input reports
        procon_log("usb 80 05: input reports off");
        pc->reports_enabled = false;
        break;
    default:
        procon_log("usb 80 %02x: unknown, ignored", cmd);
        break;
    }
}

static void handle_subcommand(procon_t *pc, const uint8_t *buf, uint16_t len, uint8_t timer) {
    uint8_t sub = buf[10];
    switch (sub) {
    case 0x01:  // Bluetooth manual pairing
        procon_log("sub 01: pairing");
        reply_uart(pc, timer, true, sub, (const uint8_t[]){0x03, 0x01}, 2);
        break;
    case 0x02:  // device info
        procon_log("sub 02: device info");
        reply_uart(pc, timer, true, sub, k_device_info, sizeof(k_device_info));
        break;
    case 0x10: {  // SPI flash read: addr u32 LE at [11..14], length at [15]
        if (len < 16) {
            procon_log("sub 10: short packet (%u bytes)", len);
            return;
        }
        uint32_t addr = (uint32_t)buf[11] | (uint32_t)buf[12] << 8 | (uint32_t)buf[13] << 16 | (uint32_t)buf[14] << 24;
        uint8_t n = buf[15];
        if (n > UART_REPLY_MAX_DATA - 5) {
            n = UART_REPLY_MAX_DATA - 5;
        }
        uint8_t data[UART_REPLY_MAX_DATA];
        memcpy(data, buf + 11, 4);
        data[4] = buf[15];
        procon_spi_read(addr, data + 5, n);
        procon_log("sub 10: spi read 0x%04lx len %u", (unsigned long)addr, buf[15]);
        reply_uart(pc, timer, true, sub, data, (uint8_t)(5 + n));
        break;
    }
    case 0x21:  // set NFC/IR MCU configuration
        procon_log("sub 21: mcu config");
        reply_uart(pc, timer, true, sub, k_mcu_config, sizeof(k_mcu_config));
        break;
    case 0x30:  // player lights
        pc->player_lights = len > 11 ? buf[11] : 0;
        procon_log("sub 30: player lights 0x%02x", pc->player_lights);
        reply_uart(pc, timer, true, sub, NULL, 0);
        break;
    case 0x03:  // set input report mode
    case 0x04:  // trigger buttons elapsed time
    case 0x08:  // shipment low power state
    case 0x38:  // HOME light
    case 0x40:  // enable IMU
    case 0x41:  // IMU sensitivity
    case 0x48:  // enable vibration
        procon_log("sub %02x: ack", sub);
        reply_uart(pc, timer, true, sub, NULL, 0);
        break;
    default:
        procon_log("sub %02x: unhandled, acked", sub);
        reply_uart(pc, timer, true, sub, NULL, 0);
        break;
    }
}

void procon_handle_output(procon_t *pc, const uint8_t *buf, uint16_t len, uint8_t timer) {
    if (len < 1) {
        return;
    }
    switch (buf[0]) {
    case 0x80:
        if (len >= 2) {
            handle_usb_cmd(pc, buf[1]);
        }
        break;
    case 0x01:  // rumble + subcommand
        if (len >= 11) {
            handle_subcommand(pc, buf, len, timer);
        }
        break;
    case 0x00:
    case 0x10:  // rumble only
        break;
    default:
        procon_log("out report %02x: unknown, ignored", buf[0]);
        break;
    }
}

static void pack_stick(uint16_t x, uint16_t y, uint8_t out[3]) {
    x &= 0xfff;
    y &= 0xfff;
    out[0] = (uint8_t)(x & 0xff);
    out[1] = (uint8_t)(((y << 4) & 0xf0) | ((x >> 8) & 0x0f));
    out[2] = (uint8_t)((y >> 4) & 0xff);
}

void procon_pack_input(const procon_input_t *in, uint8_t out[11]) {
    out[0] = 0x81;  // battery full, wired/USB powered
    out[1] = (uint8_t)(in->buttons & 0xff);
    out[2] = (uint8_t)((in->buttons >> 8) & 0xff);
    out[3] = (uint8_t)((in->buttons >> 16) & 0xff);
    pack_stick(in->lx, in->ly, out + 4);
    pack_stick(in->rx, in->ry, out + 7);
    out[10] = 0x00;  // vibrator input report
}

void procon_build_input_report(const procon_t *pc, uint8_t timer, uint8_t out[PROCON_REPORT_SIZE]) {
    memset(out, 0, PROCON_REPORT_SIZE);  // IMU data left zeroed, as in the Python/Go ports
    out[0] = 0x30;
    out[1] = timer;
    procon_pack_input(&pc->input, out + 2);
}
