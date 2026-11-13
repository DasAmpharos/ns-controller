#include "serial.h"

#include "hardware/gpio.h"
#include "hardware/irq.h"
#include "hardware/uart.h"
#include "pico/time.h"

#define UART uart0
#define TX_PIN 0
#define RX_PIN 1
#define RX_SIZE 4096  // powers of two
#define TX_SIZE 16384

static volatile uint8_t s_rx[RX_SIZE];
static volatile uint32_t s_rx_head, s_rx_tail, s_rx_overflows;
static uint8_t s_tx[TX_SIZE];
static uint32_t s_tx_head, s_tx_tail;

static void on_uart_rx(void) {
    while (uart_is_readable(UART)) {
        uint8_t b = (uint8_t)uart_get_hw(UART)->dr;
        if (s_rx_head - s_rx_tail < RX_SIZE) {
            s_rx[s_rx_head & (RX_SIZE - 1)] = b;
            s_rx_head++;
        } else {
            s_rx_overflows++;
        }
    }
}

void serial_init(uint32_t baud) {
    uart_init(UART, baud);
    gpio_set_function(TX_PIN, GPIO_FUNC_UART);
    gpio_set_function(RX_PIN, GPIO_FUNC_UART);
    uart_set_fifo_enabled(UART, true);
    irq_set_exclusive_handler(UART0_IRQ, on_uart_rx);
    irq_set_enabled(UART0_IRQ, true);
    uart_set_irq_enables(UART, true, false);
}

size_t serial_read(uint8_t *buf, size_t max) {
    size_t n = 0;
    while (n < max && s_rx_tail != s_rx_head) {
        buf[n++] = s_rx[s_rx_tail & (RX_SIZE - 1)];
        s_rx_tail++;
    }
    return n;
}

bool serial_write(const uint8_t *data, size_t len, size_t reserve) {
    uint32_t free = TX_SIZE - (s_tx_head - s_tx_tail);
    if (len + reserve > free) {
        return false;
    }
    for (size_t i = 0; i < len; i++) {
        s_tx[(s_tx_head + i) & (TX_SIZE - 1)] = data[i];
    }
    s_tx_head += len;
    return true;
}

void serial_drain(void) {
    while (s_tx_tail != s_tx_head && uart_is_writable(UART)) {
        uart_get_hw(UART)->dr = s_tx[s_tx_tail & (TX_SIZE - 1)];
        s_tx_tail++;
    }
}

void serial_flush(uint32_t timeout_us) {
    absolute_time_t until = make_timeout_time_us(timeout_us);
    while (s_tx_tail != s_tx_head && !time_reached(until)) {
        serial_drain();
    }
    uart_tx_wait_blocking(UART);
}

uint32_t serial_rx_overflows(void) {
    return s_rx_overflows;
}
