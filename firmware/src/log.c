#include "log.h"

#include <stdarg.h>
#include <stdio.h>

#include "hardware/gpio.h"
#include "hardware/uart.h"
#include "pico/time.h"
#include "procon.h"

// UART0 on GP0 (TX) / GP1 (RX): the same pins the brain link will use from Phase 2.
#define LOG_UART uart0
#define LOG_TX_PIN 0
#define LOG_RX_PIN 1
#define LOG_BAUD 115200

#define LOG_BUF_SIZE 16384  // power of two

static char s_buf[LOG_BUF_SIZE];
static uint32_t s_head;  // write index (monotonic)
static uint32_t s_tail;  // read index (monotonic)
static uint32_t s_dropped;

void log_init(void) {
    uart_init(LOG_UART, LOG_BAUD);
    gpio_set_function(LOG_TX_PIN, GPIO_FUNC_UART);
    gpio_set_function(LOG_RX_PIN, GPIO_FUNC_UART);
}

static void push(const char *s, uint32_t n) {
    if (LOG_BUF_SIZE - (s_head - s_tail) < n) {
        s_dropped++;
        return;
    }
    for (uint32_t i = 0; i < n; i++) {
        s_buf[(s_head + i) & (LOG_BUF_SIZE - 1)] = s[i];
    }
    s_head += n;
}

static void vlog(const char *fmt, va_list ap) {
    char line[160];
    uint32_t ms = to_ms_since_boot(get_absolute_time());
    int n = 0;
    if (s_dropped) {
        n = snprintf(line, sizeof(line), "[%lu log lines dropped]\r\n", (unsigned long)s_dropped);
        if (LOG_BUF_SIZE - (s_head - s_tail) >= (uint32_t)n) {
            push(line, (uint32_t)n);
            s_dropped = 0;
        }
    }
    n = snprintf(line, sizeof(line), "%6lu.%03lu ", (unsigned long)(ms / 1000), (unsigned long)(ms % 1000));
    int m = vsnprintf(line + n, sizeof(line) - (size_t)n - 2, fmt, ap);
    if (m < 0) {
        return;
    }
    n += m;
    if (n > (int)sizeof(line) - 3) {
        n = (int)sizeof(line) - 3;
    }
    line[n++] = '\r';
    line[n++] = '\n';
    push(line, (uint32_t)n);
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

void log_drain(void) {
    while (s_tail != s_head && uart_is_writable(LOG_UART)) {
        uart_putc_raw(LOG_UART, s_buf[s_tail & (LOG_BUF_SIZE - 1)]);
        s_tail++;
    }
}
