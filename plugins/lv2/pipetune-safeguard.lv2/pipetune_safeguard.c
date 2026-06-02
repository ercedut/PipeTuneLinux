// PipeTune Safeguard LV2 plugin.
// Conservative safety DSP only: preamp, first-order high-pass, hard limiter.

#include <math.h>
#include <stdint.h>
#include <stdlib.h>

#include "lv2/core/lv2.h"

#define PIPE_TUNE_URI "https://pipetune.local/plugins/pipetune-safeguard"

typedef enum {
    PORT_IN_L = 0,
    PORT_IN_R = 1,
    PORT_OUT_L = 2,
    PORT_OUT_R = 3,
    PORT_PREAMP_DB = 4,
    PORT_HIGHPASS_HZ = 5,
    PORT_LIMITER_CEILING_DB = 6,
    PORT_BYPASS = 7
} PortIndex;

typedef struct {
    const float* in_l;
    const float* in_r;
    float* out_l;
    float* out_r;
    const float* preamp_db;
    const float* highpass_hz;
    const float* limiter_ceiling_db;
    const float* bypass;
    double sample_rate;
    float prev_in_l;
    float prev_in_r;
    float prev_out_l;
    float prev_out_r;
} PipeTuneSafeguard;

static float clampf(float value, float minimum, float maximum, float fallback) {
    if (!isfinite(value)) {
        return fallback;
    }
    if (value < minimum) {
        return minimum;
    }
    if (value > maximum) {
        return maximum;
    }
    return value;
}

static float read_control(const float* value, float fallback) {
    if (value == NULL) {
        return fallback;
    }
    return *value;
}

static LV2_Handle instantiate(
    const LV2_Descriptor* descriptor,
    double rate,
    const char* bundle_path,
    const LV2_Feature* const* features
) {
    (void)descriptor;
    (void)bundle_path;
    (void)features;

    PipeTuneSafeguard* self = (PipeTuneSafeguard*)calloc(1, sizeof(PipeTuneSafeguard));
    if (self != NULL) {
        self->sample_rate = rate > 0.0 ? rate : 48000.0;
    }
    return (LV2_Handle)self;
}

static void connect_port(LV2_Handle instance, uint32_t port, void* data) {
    PipeTuneSafeguard* self = (PipeTuneSafeguard*)instance;
    if (self == NULL) {
        return;
    }

    switch ((PortIndex)port) {
        case PORT_IN_L:
            self->in_l = (const float*)data;
            break;
        case PORT_IN_R:
            self->in_r = (const float*)data;
            break;
        case PORT_OUT_L:
            self->out_l = (float*)data;
            break;
        case PORT_OUT_R:
            self->out_r = (float*)data;
            break;
        case PORT_PREAMP_DB:
            self->preamp_db = (const float*)data;
            break;
        case PORT_HIGHPASS_HZ:
            self->highpass_hz = (const float*)data;
            break;
        case PORT_LIMITER_CEILING_DB:
            self->limiter_ceiling_db = (const float*)data;
            break;
        case PORT_BYPASS:
            self->bypass = (const float*)data;
            break;
    }
}

static void activate(LV2_Handle instance) {
    PipeTuneSafeguard* self = (PipeTuneSafeguard*)instance;
    if (self == NULL) {
        return;
    }
    self->prev_in_l = 0.0f;
    self->prev_in_r = 0.0f;
    self->prev_out_l = 0.0f;
    self->prev_out_r = 0.0f;
}

static float limit_sample(float value, float ceiling) {
    if (value > ceiling) {
        return ceiling;
    }
    if (value < -ceiling) {
        return -ceiling;
    }
    return value;
}

static void run(LV2_Handle instance, uint32_t sample_count) {
    PipeTuneSafeguard* self = (PipeTuneSafeguard*)instance;
    if (
        self == NULL ||
        self->in_l == NULL ||
        self->in_r == NULL ||
        self->out_l == NULL ||
        self->out_r == NULL
    ) {
        return;
    }

    const float bypass = clampf(read_control(self->bypass, 0.0f), 0.0f, 1.0f, 0.0f);
    if (bypass >= 0.5f) {
        for (uint32_t i = 0; i < sample_count; ++i) {
            self->out_l[i] = self->in_l[i];
            self->out_r[i] = self->in_r[i];
        }
        return;
    }

    const float preamp_db = clampf(read_control(self->preamp_db, -6.0f), -24.0f, 0.0f, -6.0f);
    const float highpass_hz = clampf(read_control(self->highpass_hz, 120.0f), 60.0f, 250.0f, 120.0f);
    const float limiter_db = clampf(read_control(self->limiter_ceiling_db, -1.0f), -12.0f, -0.1f, -1.0f);

    const float preamp_gain = powf(10.0f, preamp_db / 20.0f);
    const float ceiling = powf(10.0f, limiter_db / 20.0f);
    const float rc = 1.0f / (2.0f * (float)M_PI * highpass_hz);
    const float dt = 1.0f / (float)self->sample_rate;
    const float alpha = rc / (rc + dt);

    float prev_in_l = self->prev_in_l;
    float prev_in_r = self->prev_in_r;
    float prev_out_l = self->prev_out_l;
    float prev_out_r = self->prev_out_r;

    for (uint32_t i = 0; i < sample_count; ++i) {
        const float in_l = self->in_l[i] * preamp_gain;
        const float in_r = self->in_r[i] * preamp_gain;
        const float high_l = alpha * (prev_out_l + in_l - prev_in_l);
        const float high_r = alpha * (prev_out_r + in_r - prev_in_r);

        self->out_l[i] = limit_sample(high_l, ceiling);
        self->out_r[i] = limit_sample(high_r, ceiling);

        prev_in_l = in_l;
        prev_in_r = in_r;
        prev_out_l = high_l;
        prev_out_r = high_r;
    }

    self->prev_in_l = prev_in_l;
    self->prev_in_r = prev_in_r;
    self->prev_out_l = prev_out_l;
    self->prev_out_r = prev_out_r;
}

static void deactivate(LV2_Handle instance) {
    (void)instance;
}

static void cleanup(LV2_Handle instance) {
    free(instance);
}

static const void* extension_data(const char* uri) {
    (void)uri;
    return NULL;
}

static const LV2_Descriptor descriptor = {
    PIPE_TUNE_URI,
    instantiate,
    connect_port,
    activate,
    run,
    deactivate,
    cleanup,
    extension_data
};

LV2_SYMBOL_EXPORT const LV2_Descriptor* lv2_descriptor(uint32_t index) {
    return index == 0 ? &descriptor : NULL;
}

