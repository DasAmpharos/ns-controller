#pragma once

#include <stdbool.h>

// True while the BOOTSEL button is held. Takes a few microseconds with interrupts disabled; poll sparingly.
bool bootsel_pressed(void);
