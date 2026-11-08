// Host tests for the keyframe player, including the compiled test sequences.
#include <stdio.h>
#include <string.h>

#include "player.h"
#include "sequences.h"

static int checks, failures;

void procon_log(const char *fmt, ...) {
    (void)fmt;
}

#define EXPECT(cond, ...)                                                                                              \
    do {                                                                                                               \
        checks++;                                                                                                      \
        if (!(cond)) {                                                                                                 \
            failures++;                                                                                                \
            fprintf(stderr, "FAIL %s:%d: ", __FILE__, __LINE__);                                                       \
            fprintf(stderr, __VA_ARGS__);                                                                              \
            fprintf(stderr, "\n");                                                                                     \
        }                                                                                                              \
    } while (0)

static const keyframe_t k_frames[] = {
    {0, PROCON_BTN_A, 2048, 2048, 2048, 2048},
    {100, 0, 2048, 2048, 2048, 2048},
    {200, PROCON_BTN_B, 4095, 2048, 2048, 2048},
    {300, 0, 2048, 2048, 2048, 2048},
};
static const sequence_t k_seq = {"t", k_frames, 4};

static void test_basic_timeline(void) {
    player_t p;
    procon_input_t in = {0, 2048, 2048, 2048, 2048};
    uint64_t t0 = 5000000;
    player_start(&p, &k_seq, t0);
    EXPECT(player_due_in(&p, t0) == 0, "first keyframe due immediately");
    EXPECT(player_update(&p, t0, &in) && in.buttons == PROCON_BTN_A, "A pressed at 0");
    EXPECT(!player_update(&p, t0 + 99999, &in) && in.buttons == PROCON_BTN_A, "still A at 99.999 ms");
    EXPECT(player_due_in(&p, t0 + 50000) == 50000, "next due in 50 ms");
    EXPECT(player_update(&p, t0 + 100000, &in) && in.buttons == 0, "released at 100 ms");
    EXPECT(player_update(&p, t0 + 250000, &in) && in.buttons == PROCON_BTN_B && in.lx == 4095, "B + stick at 200");
    EXPECT(p.running, "still running before last keyframe");
    EXPECT(player_update(&p, t0 + 300000, &in) && in.buttons == 0 && in.lx == 2048, "neutral at end");
    EXPECT(!p.running, "stopped after last keyframe");
    EXPECT(!player_update(&p, t0 + 400000, &in), "no changes after the end");
}

static void test_overdue_frames_collapse(void) {
    player_t p;
    procon_input_t in = {0, 2048, 2048, 2048, 2048};
    player_start(&p, &k_seq, 0);
    player_update(&p, 250000, &in);  // a late tick applies 0, 100 and 200 ms at once
    EXPECT(in.buttons == PROCON_BTN_B && p.next == 3, "latest due keyframe wins");
}

static void test_clock_slightly_behind_start(void) {
    // Regression: the main loop reads the clock, then starts a sequence with a later timestamp. An update with
    // the earlier time used to wrap around and apply every keyframe at once (the sequence "finished" instantly).
    player_t p;
    procon_input_t in = {0, 2048, 2048, 2048, 2048};
    player_start(&p, &k_seq, 1000050);
    player_update(&p, 1000000, &in);
    EXPECT(p.running && p.next == 1 && in.buttons == PROCON_BTN_A, "only the t=0 keyframe applied");
}

static void test_stop_is_neutral(void) {
    player_t p;
    procon_input_t in = {0, 2048, 2048, 2048, 2048};
    player_start(&p, &k_seq, 0);
    player_update(&p, 200000, &in);
    player_stop(&p, &in);
    EXPECT(!p.running && in.buttons == 0 && in.lx == 2048, "stop releases everything");
    EXPECT(player_due_in(&p, 0) == UINT64_MAX, "nothing due when stopped");
}

// Play a whole sequence on a 1 ms tick; count presses per button and stick deflections.
static void play(const sequence_t *seq, int presses[24], int *stick_moves, procon_input_t *end) {
    player_t p;
    procon_input_t in = {0, 2048, 2048, 2048, 2048};
    uint32_t prev = 0;
    memset(presses, 0, 24 * sizeof(int));
    *stick_moves = 0;
    player_start(&p, seq, 0);
    for (uint64_t t = 0; p.running && t < 120000000; t += 1000) {
        uint16_t lx = in.lx, rx = in.rx, ly = in.ly, ry = in.ry;
        player_update(&p, t, &in);
        for (int b = 0; b < 24; b++) {
            presses[b] += (in.buttons >> b & 1) && !(prev >> b & 1);
        }
        *stick_moves += (in.lx != lx || in.ly != ly || in.rx != rx || in.ry != ry);
        prev = in.buttons;
    }
    *end = in;
}

static void test_input_test_sequence(void) {
    int presses[24], moves;
    procon_input_t end;
    play(&SEQUENCES[0], presses, &moves, &end);
    EXPECT(strcmp(SEQUENCES[0].name, "input-test") == 0, "sequence 1 is the input test");
    const uint32_t every = PROCON_BTN_A | PROCON_BTN_B | PROCON_BTN_X | PROCON_BTN_Y | PROCON_BTN_L | PROCON_BTN_R |
                           PROCON_BTN_ZL | PROCON_BTN_ZR | PROCON_BTN_UP | PROCON_BTN_DOWN | PROCON_BTN_LEFT |
                           PROCON_BTN_RIGHT | PROCON_BTN_LSTICK | PROCON_BTN_RSTICK | PROCON_BTN_PLUS |
                           PROCON_BTN_MINUS;
    for (int b = 0; b < 24; b++) {
        int want = (every >> b & 1) ? 1 : 0;
        if ((1u << b) & (PROCON_BTN_L | PROCON_BTN_R)) {
            want = 2;  // alone and as the L+R combo
        }
        EXPECT(presses[b] == want, "button bit %d pressed %d times, want %d", b, presses[b], want);
    }
    EXPECT(presses[12] == 0 && presses[13] == 0, "never HOME or CAPTURE");
    EXPECT(moves >= 16, "both sticks swept (%d moves)", moves);
    EXPECT(end.buttons == 0 && end.lx == 2048 && end.ry == 2048, "ends neutral");
}

static void test_nxbt_demo_sequence(void) {
    int presses[24], moves;
    procon_input_t end;
    play(&SEQUENCES[1], presses, &moves, &end);
    EXPECT(strcmp(SEQUENCES[1].name, "nxbt-demo") == 0, "sequence 2 is the nxbt demo");
    EXPECT(presses[16] == 12 + 1, "DPAD_DOWN: LOOP 12 plus one long hold (%d)", presses[16]);
    EXPECT(presses[2] == 9, "B pressed 9 times (%d)", presses[2]);
    EXPECT(SEQUENCES[1].frames[SEQUENCES[1].count - 1].t_ms == 25130, "25.13 s long");
    EXPECT(end.buttons == 0 && end.lx == 2048, "ends neutral");
}

int main(void) {
    test_basic_timeline();
    test_overdue_frames_collapse();
    test_clock_slightly_behind_start();
    test_stop_is_neutral();
    test_input_test_sequence();
    test_nxbt_demo_sequence();
    printf("%d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
