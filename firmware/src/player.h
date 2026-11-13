// Keyframe player: applies a timeline of absolute controller states at the right moments.
//
// Hardware-free (host-tested). Phase 1 plays sequences compiled into the firmware (tools/macro2c.py);
// Phase 2 will play timelines uploaded from the brain over UART.
#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "procon.h"

typedef struct {
    uint32_t t_us;  // offset from the start of the sequence (up to ~71 minutes)
    uint32_t buttons;  // PROCON_BTN_* bits
    uint16_t lx, ly, rx, ry;  // 12-bit stick axes
} keyframe_t;

typedef struct {
    const char *name;
    const keyframe_t *frames;
    uint16_t count;
} sequence_t;

typedef struct {
    const sequence_t *seq;
    uint64_t start_us;
    uint16_t next;  // index of the next keyframe to apply
    bool running;
} player_t;

void player_start(player_t *p, const sequence_t *seq, uint64_t now_us);

// Stop and leave the input neutral.
void player_stop(player_t *p, procon_input_t *input);

// Apply every keyframe due by now_us to *input; the last one applied wins. Returns true if *input changed.
// Sets running = false once the final keyframe has been applied.
bool player_update(player_t *p, uint64_t now_us, procon_input_t *input);

// Microseconds until the next keyframe is due (0 if overdue), or UINT64_MAX when not running.
uint64_t player_due_in(const player_t *p, uint64_t now_us);
