// UART0 link to the brain (GP0 TX, GP1 RX): interrupt-driven receive into a ring buffer, transmit from a ring
// buffer drained without blocking from the main loop.
#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define SERIAL_BAUD 1000000

void serial_init(uint32_t baud);
size_t serial_read(uint8_t *buf, size_t max);  // bytes received so far (non-blocking)
// Queue `len` bytes if at least `reserve` bytes stay free afterwards (all or nothing). Logs pass a reserve so
// they can never crowd out protocol replies.
bool serial_write(const uint8_t *data, size_t len, size_t reserve);
void serial_drain(void);  // move queued bytes into the UART FIFO while it has room
void serial_flush(uint32_t timeout_us);  // drain completely (before a reboot)
uint32_t serial_rx_overflows(void);
