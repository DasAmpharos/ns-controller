// Non-blocking log over UART. Messages go into a RAM ring buffer; log_drain() pushes bytes
// to the UART FIFO only while it has space, so logging never stalls USB handling.
#pragma once

#include <stdint.h>

void log_init(void);
void log_printf(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
void log_hex(const char *label, const uint8_t *buf, uint16_t len);
void log_drain(void);
