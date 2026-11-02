// USB descriptors for a wired Nintendo Switch Pro Controller.
// Device/config values match the Linux gadget in bin/install.sh, which worked on the target consoles.
// Endpoint layout matches a genuine controller: IN 0x81 then OUT 0x01, 64 bytes, 8 ms interval.
#include <string.h>

#include "procon_data.h"
#include "tusb.h"

#define USB_VID 0x057e  // Nintendo
#define USB_PID 0x2009  // Pro Controller
#define USB_BCD_DEVICE 0x0100

#define EP_IN 0x81
#define EP_OUT 0x01
#define EP_SIZE 64
#define EP_INTERVAL_MS 8

enum { STR_LANGID = 0, STR_MANUFACTURER, STR_PRODUCT, STR_SERIAL, STR_CONFIG };

static const tusb_desc_device_t k_device = {
    .bLength = sizeof(tusb_desc_device_t),
    .bDescriptorType = TUSB_DESC_DEVICE,
    .bcdUSB = 0x0200,
    .bDeviceClass = 0x00,
    .bDeviceSubClass = 0x00,
    .bDeviceProtocol = 0x00,
    .bMaxPacketSize0 = CFG_TUD_ENDPOINT0_SIZE,
    .idVendor = USB_VID,
    .idProduct = USB_PID,
    .bcdDevice = USB_BCD_DEVICE,
    .iManufacturer = STR_MANUFACTURER,
    .iProduct = STR_PRODUCT,
    .iSerialNumber = STR_SERIAL,
    .bNumConfigurations = 1,
};

#define CONFIG_TOTAL_LEN (TUD_CONFIG_DESC_LEN + 9 + 9 + 7 + 7)

static const uint8_t k_config[CONFIG_TOTAL_LEN] = {
    // Config: 1 interface, bus powered + remote wakeup (0xA0), 500 mA.
    TUD_CONFIG_DESCRIPTOR(1, 1, STR_CONFIG, CONFIG_TOTAL_LEN, TUSB_DESC_CONFIG_ATT_REMOTE_WAKEUP, 500),
    // Interface 0: HID, no boot protocol, 2 endpoints.
    9, TUSB_DESC_INTERFACE, 0, 0, 2, TUSB_CLASS_HID, 0, 0, 0,
    // HID 1.11 descriptor with one report descriptor.
    9, HID_DESC_TYPE_HID, U16_TO_U8S_LE(0x0111), 0, 1, HID_DESC_TYPE_REPORT,
    U16_TO_U8S_LE(PROCON_HID_REPORT_DESCRIPTOR_LEN),
    // Endpoint IN, then OUT.
    7, TUSB_DESC_ENDPOINT, EP_IN, TUSB_XFER_INTERRUPT, U16_TO_U8S_LE(EP_SIZE), EP_INTERVAL_MS,
    7, TUSB_DESC_ENDPOINT, EP_OUT, TUSB_XFER_INTERRUPT, U16_TO_U8S_LE(EP_SIZE), EP_INTERVAL_MS,
};

static const char *const k_strings[] = {
    [STR_MANUFACTURER] = "Nintendo Co., Ltd.",
    [STR_PRODUCT] = "Pro Controller",
    [STR_SERIAL] = "000000000001",
    [STR_CONFIG] = "Nintendo Switch Pro Controller",
};

const uint8_t *tud_descriptor_device_cb(void) {
    return (const uint8_t *)&k_device;
}

const uint8_t *tud_descriptor_configuration_cb(uint8_t index) {
    (void)index;
    return k_config;
}

const uint8_t *tud_hid_descriptor_report_cb(uint8_t instance) {
    (void)instance;
    return procon_hid_report_descriptor;
}

const uint16_t *tud_descriptor_string_cb(uint8_t index, uint16_t langid) {
    (void)langid;
    static uint16_t desc[32];
    uint8_t chars;
    if (index == STR_LANGID) {
        desc[1] = 0x0409;  // English (US)
        chars = 1;
    } else {
        if (index >= sizeof(k_strings) / sizeof(k_strings[0]) || !k_strings[index]) {
            return NULL;
        }
        const char *s = k_strings[index];
        chars = (uint8_t)strlen(s);
        if (chars > 31) {
            chars = 31;
        }
        for (uint8_t i = 0; i < chars; i++) {
            desc[1 + i] = (uint8_t)s[i];
        }
    }
    desc[0] = (uint16_t)((TUSB_DESC_STRING << 8) | (2 * chars + 2));
    return desc;
}
