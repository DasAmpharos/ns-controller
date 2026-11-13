#include "log.h"

#include <stdarg.h>
#include <stdio.h>

#include "pico/time.h"
#include "procon.h"

static log_sink_t s_sink;

void log_init(log_sink_t sink) {
    s_sink = sink;
}

static void vlog(const char *fmt, va_list ap) {
    if (!s_sink) {
        return;
    }
    char line[200];
    uint32_t ms = to_ms_since_boot(get_absolute_time());
    int n = snprintf(line, sizeof(line), "%6lu.%03lu ", (unsigned long)(ms / 1000), (unsigned long)(ms % 1000));
    int m = vsnprintf(line + n, sizeof(line) - (size_t)n, fmt, ap);
    if (m < 0) {
        return;
    }
    n += m;
    if (n > (int)sizeof(line) - 1) {
        n = (int)sizeof(line) - 1;
    }
    s_sink(line, (size_t)n);
}

void log_printf(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    vlog(fmt, ap);
    va_end(ap);
}

void procon_log(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    vlog(fmt, ap);
    va_end(ap);
}

void log_hex(const char *label, const uint8_t *buf, uint16_t len) {
    char hex[3 * 24 + 1];
    uint16_t n = len > 24 ? 24 : len;
    for (uint16_t i = 0; i < n; i++) {
        snprintf(hex + 3 * i, 4, "%02x ", buf[i]);
    }
    hex[3 * n] = '\0';
    log_printf("%s [%u] %s%s", label, len, hex, len > n ? "..." : "");
}
