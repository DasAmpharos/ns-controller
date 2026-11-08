#include "player.h"

#include <string.h>

void player_start(player_t *p, const sequence_t *seq, uint64_t now_us) {
    p->seq = seq;
    p->start_us = now_us;
    p->next = 0;
    p->running = seq != NULL && seq->count > 0;
}

void player_stop(player_t *p, procon_input_t *input) {
    p->running = false;
    input->buttons = 0;
    input->lx = input->ly = input->rx = input->ry = PROCON_STICK_CENTER;
}

bool player_update(player_t *p, uint64_t now_us, procon_input_t *input) {
    if (!p->running) {
        return false;
    }
    procon_input_t before = *input;
    uint64_t elapsed_ms = (now_us - p->start_us) / 1000;
    while (p->next < p->seq->count && p->seq->frames[p->next].t_ms <= elapsed_ms) {
        const keyframe_t *kf = &p->seq->frames[p->next++];
        input->buttons = kf->buttons;
        input->lx = kf->lx;
        input->ly = kf->ly;
        input->rx = kf->rx;
        input->ry = kf->ry;
    }
    if (p->next >= p->seq->count) {
        p->running = false;
    }
    return memcmp(&before, input, sizeof(before)) != 0;
}

uint64_t player_due_in(const player_t *p, uint64_t now_us) {
    if (!p->running) {
        return UINT64_MAX;
    }
    uint64_t due = p->start_us + (uint64_t)p->seq->frames[p->next].t_ms * 1000;
    return due > now_us ? due - now_us : 0;
}
