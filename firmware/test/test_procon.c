// Host unit tests for procon.c. Golden vectors in vectors.h come from the Python Controller (gen_vectors.py).
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#include "procon.h"
#include "procon_data.h"
#include "vectors.h"

#define ARRAY_LEN(a) (sizeof(a) / sizeof((a)[0]))

static int failures;
static int checks;

void procon_log(const char *fmt, ...) {
    (void)fmt;
}

static void dump(const char *label, const uint8_t *b, size_t n) {
    fprintf(stderr, "    %s:", label);
    for (size_t i = 0; i < n; i++) {
        fprintf(stderr, " %02x", b[i]);
    }
    fprintf(stderr, "\n");
}

// Compare a reply with the golden one. For 0x21 replies byte 1 is the free-running timer, so it is skipped.
static void expect_report(const char *name, const uint8_t *got, const uint8_t *want) {
    checks++;
    for (int i = 0; i < PROCON_REPORT_SIZE; i++) {
        if (i == 1 && want[0] == 0x21) {
            continue;
        }
        if (got[i] != want[i]) {
            failures++;
            fprintf(stderr, "FAIL %s: byte %d got %02x want %02x\n", name, i, got[i], want[i]);
            dump("got ", got, PROCON_REPORT_SIZE);
            dump("want", want, PROCON_REPORT_SIZE);
            return;
        }
    }
}

static void expect(int cond, const char *what) {
    checks++;
    if (!cond) {
        failures++;
        fprintf(stderr, "FAIL %s\n", what);
    }
}

static void test_on_mount(void) {
    procon_t pc;
    procon_init(&pc);
    procon_on_mount(&pc);
    expect(pc.txq_count == ARRAY_LEN(vec_on_open), "on_mount queues the open packets");
    for (size_t i = 0; i < ARRAY_LEN(vec_on_open); i++) {
        const uint8_t *got = procon_tx_peek(&pc);
        if (!got) {
            break;
        }
        expect_report("on_mount", got, vec_on_open[i]);
        procon_tx_pop(&pc);
    }
}

static void test_out_vectors(void) {
    for (size_t v = 0; v < ARRAY_LEN(out_vectors); v++) {
        const out_vector_t *vec = &out_vectors[v];
        procon_t pc;
        procon_init(&pc);
        procon_handle_output(&pc, vec->req, vec->req_len, 0x42);
        char what[96];
        snprintf(what, sizeof(what), "%s: reply count %u (want %u)", vec->name, pc.txq_count, vec->n_replies);
        expect(pc.txq_count == vec->n_replies, what);
        for (uint8_t r = 0; r < vec->n_replies; r++) {
            const uint8_t *got = procon_tx_peek(&pc);
            if (!got) {
                break;
            }
            expect_report(vec->name, got, vec->replies[r]);
            procon_tx_pop(&pc);
        }
    }
}

static void test_in_vectors(void) {
    for (size_t v = 0; v < ARRAY_LEN(in_vectors); v++) {
        const in_vector_t *vec = &in_vectors[v];
        procon_input_t in = {vec->buttons, vec->lx, vec->ly, vec->rx, vec->ry};
        uint8_t block[11];
        procon_pack_input(&in, block);
        checks++;
        if (memcmp(block, vec->block, sizeof(block)) != 0) {
            failures++;
            fprintf(stderr, "FAIL input %s\n", vec->name);
            dump("got ", block, sizeof(block));
            dump("want", vec->block, sizeof(block));
        }
    }
}

static void test_report_toggle(void) {
    procon_t pc;
    procon_init(&pc);
    procon_handle_output(&pc, (const uint8_t[]){0x80, 0x04}, 2, 0);
    expect(pc.reports_enabled, "0x80 0x04 enables reports");
    procon_handle_output(&pc, (const uint8_t[]){0x80, 0x04}, 2, 0);
    expect(pc.reports_enabled && pc.txq_count == 0, "repeated 0x80 0x04 is idempotent");
    procon_handle_output(&pc, (const uint8_t[]){0x80, 0x05}, 2, 0);
    expect(!pc.reports_enabled, "0x80 0x05 disables reports");
}

static void test_input_report(void) {
    procon_t pc;
    procon_init(&pc);
    pc.input.buttons = PROCON_BTN_A;
    uint8_t out[PROCON_REPORT_SIZE];
    procon_build_input_report(&pc, 0x7b, out);
    const uint8_t want[13] = {0x30, 0x7b, 0x81, 0x08, 0x00, 0x00, 0x00, 0x08, 0x80, 0x00, 0x08, 0x80, 0x00};
    expect(memcmp(out, want, sizeof(want)) == 0, "0x30 report header + input block");
    int rest_zero = 1;
    for (int i = 13; i < PROCON_REPORT_SIZE; i++) {
        rest_zero &= out[i] == 0;
    }
    expect(rest_zero, "0x30 report IMU bytes zero");
}

static void test_unknown_subcommand_acked(void) {
    procon_t pc;
    procon_init(&pc);
    uint8_t req[12] = {0x01, 0x00, 0, 0, 0, 0, 0, 0, 0, 0, 0x22, 0x01};
    procon_handle_output(&pc, req, sizeof(req), 0);
    const uint8_t *out = procon_tx_peek(&pc);
    expect(out && out[0] == 0x21 && out[13] == 0x80 && out[14] == 0x22, "unknown subcommand gets plain ACK");
}

static void test_spi_unmapped(void) {
    uint8_t out[4];
    procon_spi_read(0x5ffe, out, 4);
    expect(out[0] == 0xff && out[1] == 0xff, "spi below page reads 0xff");
    expect(out[2] == 0xff && out[3] == 0xff, "spi 0x6000 first bytes (erased in capture)");
    procon_spi_read(0x8000 + PROCON_SPI_8000_LEN - 1, out, 2);
    expect(out[1] == 0xff, "spi past page end reads 0xff");
}

static void test_bounds(void) {
    procon_t pc;
    procon_init(&pc);
    procon_handle_output(&pc, (const uint8_t[]){0x80}, 1, 0);
    procon_handle_output(&pc, (const uint8_t[]){0x01, 0x00, 0x00}, 3, 0);
    uint8_t short_spi[12] = {0x01, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0x10, 0x00};
    procon_handle_output(&pc, short_spi, sizeof(short_spi), 0);
    expect(pc.txq_count == 0, "short packets produce no reply");

    uint8_t big_spi[16] = {0x01, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0x10, 0x00, 0x60, 0x00, 0x00, 0xff};
    procon_handle_output(&pc, big_spi, sizeof(big_spi), 0);
    expect(pc.txq_count == 1, "oversized spi read still replies (clamped)");
}

static void test_queue_overflow(void) {
    procon_t pc;
    procon_init(&pc);
    for (int i = 0; i < PROCON_TXQ_LEN + 3; i++) {
        procon_handle_output(&pc, (const uint8_t[]){0x80, 0x02}, 2, 0);
    }
    expect(pc.txq_count == PROCON_TXQ_LEN && pc.txq_dropped == 3, "queue caps and counts drops");
    for (int i = 0; i < PROCON_TXQ_LEN; i++) {
        procon_tx_pop(&pc);
    }
    expect(procon_tx_peek(&pc) == NULL, "queue drains to empty");
}

int main(void) {
    test_on_mount();
    test_out_vectors();
    test_in_vectors();
    test_report_toggle();
    test_input_report();
    test_unknown_subcommand_acked();
    test_spi_unmapped();
    test_bounds();
    test_queue_overflow();
    printf("%d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
