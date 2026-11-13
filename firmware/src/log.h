// Log lines go to a sink set by main (LOG frames on the brain link). Formatting never blocks.
#pragma once

#include <stddef.h>
#include <stdint.h>

typedef void (*log_sink_t)(const char *line, size_t len);

void log_init(log_sink_t sink);
void log_printf(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
void log_hex(const char *label, const uint8_t *buf, uint16_t len);
