#pragma once

#include <stdint.h>

#define PROCON_HID_REPORT_DESCRIPTOR_LEN 203
#define PROCON_SPI_6000_LEN 176
#define PROCON_SPI_8000_LEN 64

extern const uint8_t procon_hid_report_descriptor[PROCON_HID_REPORT_DESCRIPTOR_LEN];
extern const uint8_t procon_spi_6000[PROCON_SPI_6000_LEN];
extern const uint8_t procon_spi_8000[PROCON_SPI_8000_LEN];
