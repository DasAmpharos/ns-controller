#pragma once

// RP2040 native USB in device mode. CFG_TUSB_MCU / CFG_TUSB_OS are set by the Pico SDK.
#define CFG_TUSB_RHPORT0_MODE OPT_MODE_DEVICE
#define CFG_TUD_ENABLED 1
#define CFG_TUD_ENDPOINT0_SIZE 64

// One HID interface (the Pro Controller), nothing else: the Switch must see a plain single-interface device.
#define CFG_TUD_HID 1
#define CFG_TUD_HID_EP_BUFSIZE 64
#define CFG_TUD_CDC 0
#define CFG_TUD_MSC 0
#define CFG_TUD_MIDI 0
#define CFG_TUD_VENDOR 0
