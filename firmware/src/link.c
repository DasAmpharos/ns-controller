#include "link.h"

#include <string.h>

// ── little-endian helpers ──────────────────────────────────────────────────────────────────────────────────

static uint16_t rd16(const uint8_t *p) {
    return (uint16_t)(p[0] | p[1] << 8);
}

static uint32_t rd32(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static uint8_t *wr16(uint8_t *p, uint16_t v) {
    p[0] = (uint8_t)v;
    p[1] = (uint8_t)(v >> 8);
    return p + 2;
}

static uint8_t *wr32(uint8_t *p, uint32_t v) {
    for (int i = 0; i < 4; i++) {
        p[i] = (uint8_t)(v >> (8 * i));
    }
    return p + 4;
}

static size_t text_len(const char *s, size_t max) {
    size_t n = 0;
    while (n < max && s && s[n]) {
        n++;
    }
    return n;
}

// ── CRC-16/CCITT-FALSE and COBS ────────────────────────────────────────────────────────────────────────────

uint16_t link_crc16(const uint8_t *data, size_t len) {
    uint16_t crc = 0xFFFF;
    for (size_t i = 0; i < len; i++) {
        crc ^= (uint16_t)data[i] << 8;
        for (int b = 0; b < 8; b++) {
            crc = (crc & 0x8000) ? (uint16_t)((crc << 1) ^ 0x1021) : (uint16_t)(crc << 1);
        }
    }
    return crc;
}

size_t link_cobs_encode(const uint8_t *in, size_t len, uint8_t *out) {
    size_t code_at = 0, o = 1;
    uint8_t code = 1;
    for (size_t i = 0; i < len; i++) {
        if (in[i] == 0) {
            out[code_at] = code;
            code_at = o++;
            code = 1;
        } else {
            out[o++] = in[i];
            if (++code == 0xFF) {
                out[code_at] = code;
                code_at = o++;
                code = 1;
            }
        }
    }
    out[code_at] = code;
    return o;
}

size_t link_cobs_decode(const uint8_t *in, size_t len, uint8_t *out, size_t out_max) {
    size_t i = 0, o = 0;
    while (i < len) {
        uint8_t code = in[i++];
        if (code == 0 || i + code - 1 > len) {
            return 0;
        }
        for (uint8_t k = 1; k < code; k++) {
            if (o >= out_max) {
                return 0;
            }
            out[o++] = in[i++];
        }
        if (code != 0xFF && i < len) {
            if (o >= out_max) {
                return 0;
            }
            out[o++] = 0;
        }
    }
    return o;
}

size_t link_encode(uint8_t type, uint8_t seq, const uint8_t *payload, size_t len, uint8_t *out) {
    uint8_t raw[LINK_MAX_FRAME];
    if (len > LINK_MAX_PAYLOAD) {
        len = LINK_MAX_PAYLOAD;
    }
    raw[0] = type;
    raw[1] = seq;
    if (len) {
        memcpy(raw + 2, payload, len);
    }
    uint16_t crc = link_crc16(raw, len + 2);
    wr16(raw + 2 + len, crc);
    size_t n = link_cobs_encode(raw, len + 4, out);
    out[n++] = 0x00;
    return n;
}

// ── state / keyframe encoding ──────────────────────────────────────────────────────────────────────────────

void link_pack_state(const procon_input_t *in, uint8_t out[12]) {
    uint8_t *p = wr32(out, in->buttons);
    p = wr16(p, in->lx);
    p = wr16(p, in->ly);
    p = wr16(p, in->rx);
    wr16(p, in->ry);
}

void link_unpack_state(const uint8_t in[12], procon_input_t *out) {
    out->buttons = rd32(in) & 0x00FFFFFF;
    out->lx = rd16(in + 4) & 0xFFF;
    out->ly = rd16(in + 6) & 0xFFF;
    out->rx = rd16(in + 8) & 0xFFF;
    out->ry = rd16(in + 10) & 0xFFF;
}

// ── sending ────────────────────────────────────────────────────────────────────────────────────────────────

static void reply(link_t *link, uint8_t type, uint8_t seq, const uint8_t *payload, size_t len) {
    link->last_reply_len = link_encode(type, seq, payload, len, link->last_reply);
    link->last_seq = seq;
    link->ops->write(link->ctx, link->last_reply, link->last_reply_len);
}

static void ack(link_t *link, uint8_t seq, uint8_t status) {
    reply(link, MSG_ACK, seq, &status, 1);
}

void link_send(link_t *link, uint8_t type, const uint8_t *payload, size_t len) {
    uint8_t wire[LINK_MAX_WIRE];
    size_t n = link_encode(type, 0, payload, len, wire);
    link->ops->write(link->ctx, wire, n);
}

static size_t pack_status(link_t *link, uint8_t *out) {
    link_status_t st;
    link->ops->get_status(link->ctx, &st);
    out[0] = st.flags;
    uint8_t *p = wr32(out + 1, st.uptime_ms);
    p = wr16(p, st.macro_id);
    p = wr16(p, st.macro_index);
    return (size_t)(p - out);
}

void link_send_status_changed(link_t *link) {
    uint8_t buf[16];
    link_send(link, MSG_STATUS_CHANGED, buf, pack_status(link, buf));
}

void link_send_macro_done(link_t *link, uint16_t macro_id, uint8_t result, uint64_t start_us, uint32_t duration_us) {
    uint8_t buf[2 + 1 + 8 + 4];
    uint8_t *p = wr16(buf, macro_id);
    *p++ = result;
    p = wr32(p, (uint32_t)start_us);
    p = wr32(p, (uint32_t)(start_us >> 32));
    wr32(p, duration_us);
    link_send(link, MSG_MACRO_DONE, buf, sizeof(buf));
}

void link_send_boot(link_t *link, uint8_t reset_reason) {
    uint8_t buf[LINK_MAX_PAYLOAD];
    uint8_t *p = wr32(buf, link->fw_version);
    *p++ = reset_reason;
    size_t text = text_len(link->fw_text, sizeof(buf) - 5);
    memcpy(p, link->fw_text, text);
    link_send(link, MSG_BOOT, buf, 5 + text);
}

void link_send_log(link_t *link, uint8_t level, const char *text, size_t len) {
    uint8_t buf[LINK_MAX_PAYLOAD];
    if (len > sizeof(buf) - 1) {
        len = sizeof(buf) - 1;
    }
    buf[0] = level;
    memcpy(buf + 1, text, len);
    link_send(link, MSG_LOG, buf, len + 1);
}

// ── handling ───────────────────────────────────────────────────────────────────────────────────────────────

static bool macro_running(link_t *link) {
    link_status_t st;
    link->ops->get_status(link->ctx, &st);
    return st.flags & STATUS_MACRO_RUNNING;
}

static void handle_macro_load(link_t *link, uint8_t seq, const uint8_t *p, size_t len) {
    if (len < 7) {
        ack(link, seq, ACK_BAD_ARG);
        return;
    }
    uint16_t id = rd16(p), total = rd16(p + 2), offset = rd16(p + 4);
    uint8_t count = p[6];
    if (len != 7 + (size_t)count * 16 || count > LINK_KEYFRAMES_PER_LOAD || total == 0 ||
        total > LINK_MAX_KEYFRAMES || offset + count > total) {
        ack(link, seq, ACK_BAD_ARG);
        return;
    }
    if (macro_running(link)) {
        ack(link, seq, ACK_BUSY);
        return;
    }
    if (id != link->macro_id || total != link->total || offset == 0) {
        link->macro_id = id;  // a new macro replaces any partly loaded one
        link->total = total;
        link->loaded = 0;
    }
    if (offset > link->loaded) {
        ack(link, seq, ACK_BAD_ARG);  // gap: chunks must arrive in order
        return;
    }
    for (uint8_t i = 0; i < count; i++) {
        const uint8_t *k = p + 7 + (size_t)i * 16;
        keyframe_t *kf = &link->frames[offset + i];
        kf->t_us = rd32(k);
        procon_input_t st;
        link_unpack_state(k + 4, &st);
        kf->buttons = st.buttons;
        kf->lx = st.lx;
        kf->ly = st.ly;
        kf->rx = st.rx;
        kf->ry = st.ry;
    }
    if (offset + count > link->loaded) {
        link->loaded = (uint16_t)(offset + count);
    }
    ack(link, seq, ACK_OK);
}

static void handle(link_t *link, const uint8_t *frame, size_t len) {
    uint8_t type = frame[0], seq = frame[1];
    const uint8_t *p = frame + 2;
    size_t plen = len - 4;

    if (type == MSG_HELLO) {
        link->last_seq = 0;  // a (re)connecting brain restarts its sequence numbers
    } else if (seq != 0 && seq == link->last_seq && link->last_reply_len) {
        link->ops->write(link->ctx, link->last_reply, link->last_reply_len);  // resend: reply again, don't redo
        return;
    }

    switch (type) {
    case MSG_HELLO: {
        uint8_t buf[LINK_MAX_PAYLOAD];
        uint8_t *q = wr16(buf, LINK_PROTO_VERSION);
        q = wr32(q, link->fw_version);
        q = wr16(q, LINK_MAX_KEYFRAMES);
        size_t text = text_len(link->fw_text, sizeof(buf) - 8);
        memcpy(q, link->fw_text, text);
        reply(link, MSG_HELLO_REPLY, seq, buf, 8 + text);
        break;
    }
    case MSG_PING:
        ack(link, seq, ACK_OK);
        break;
    case MSG_GET_STATUS: {
        uint8_t buf[16];
        reply(link, MSG_STATUS, seq, buf, pack_status(link, buf));
        break;
    }
    case MSG_SET_STATE: {
        if (plen != 12) {
            ack(link, seq, ACK_BAD_ARG);
            break;
        }
        procon_input_t st;
        link_unpack_state(p, &st);
        ack(link, seq, link->ops->set_state(link->ctx, &st) ? ACK_OK : ACK_BUSY);
        break;
    }
    case MSG_MACRO_LOAD:
        handle_macro_load(link, seq, p, plen);
        break;
    case MSG_MACRO_RUN: {
        if (plen != 2) {
            ack(link, seq, ACK_BAD_ARG);
            break;
        }
        uint16_t id = rd16(p);
        if (id != link->macro_id || link->total == 0 || link->loaded != link->total) {
            ack(link, seq, ACK_MACRO_INCOMPLETE);
            break;
        }
        link->seq.name = "brain";
        link->seq.frames = link->frames;
        link->seq.count = link->total;
        ack(link, seq, link->ops->run_macro(link->ctx, &link->seq, id) ? ACK_OK : ACK_BUSY);
        break;
    }
    case MSG_ABORT:
        link->ops->abort_macro(link->ctx);
        ack(link, seq, ACK_OK);
        break;
    case MSG_REBOOT:
        ack(link, seq, ACK_OK);
        link->ops->reboot(link->ctx, plen >= 1 && p[0] == 1);
        break;
    default:
        ack(link, seq, ACK_UNKNOWN_TYPE);
        break;
    }
}

static void frame_complete(link_t *link, uint64_t now_us) {
    uint8_t frame[LINK_MAX_FRAME];
    size_t n = link_cobs_decode(link->rx, link->rx_len, frame, sizeof(frame));
    if (n < 4 || link_crc16(frame, n - 2) != rd16(frame + n - 2)) {
        link->bad_frames++;  // dropped; the brain resends
        return;
    }
    link->last_rx_us = now_us;
    link->heard = true;
    handle(link, frame, n);
}

void link_rx(link_t *link, const uint8_t *data, size_t len, uint64_t now_us) {
    for (size_t i = 0; i < len; i++) {
        uint8_t b = data[i];
        if (b == 0x00) {
            if (!link->rx_overflow && link->rx_len) {
                frame_complete(link, now_us);
            } else if (link->rx_overflow) {
                link->bad_frames++;
            }
            link->rx_len = 0;
            link->rx_overflow = false;
        } else if (link->rx_len < sizeof(link->rx)) {
            link->rx[link->rx_len++] = b;
        } else {
            link->rx_overflow = true;
        }
    }
}

bool link_silent(const link_t *link, uint64_t now_us) {
    return link->heard && now_us - link->last_rx_us > LINK_SAFETY_TIMEOUT_US;
}

void link_init(link_t *link, const link_ops_t *ops, void *ctx, uint32_t fw_version, const char *fw_text) {
    memset(link, 0, sizeof(*link));
    link->ops = ops;
    link->ctx = ctx;
    link->fw_version = fw_version;
    link->fw_text = fw_text;
}
