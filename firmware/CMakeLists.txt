# Pro Controller emulator firmware for the Raspberry Pi Pico / Pico W.
#   cmake -S . -B build && cmake --build build   ->  build/ns_controller_fw.uf2
cmake_minimum_required(VERSION 3.13)

set(PICO_SDK_VERSION 2.2.0)
if (NOT PICO_SDK_PATH AND NOT DEFINED ENV{PICO_SDK_PATH} AND EXISTS $ENV{HOME}/.pico-sdk/sdk/${PICO_SDK_VERSION})
    set(PICO_SDK_PATH $ENV{HOME}/.pico-sdk/sdk/${PICO_SDK_VERSION})
endif ()
if (NOT PICO_BOARD)
    set(PICO_BOARD pico_w)
endif ()

include(pico_sdk_import.cmake)
project(ns_controller_fw C CXX ASM)
set(CMAKE_C_STANDARD 11)
pico_sdk_init()

execute_process(
    COMMAND git describe --always --dirty --exclude */*
    WORKING_DIRECTORY ${CMAKE_CURRENT_LIST_DIR}
    OUTPUT_VARIABLE GIT_DESCRIBE OUTPUT_STRIP_TRAILING_WHITESPACE ERROR_QUIET)
set(FW_VERSION "0.1.0-spike+${GIT_DESCRIBE}")

add_executable(ns_controller_fw
    src/main.c
    src/log.c
    src/procon.c
    src/procon_data.c
    src/usb_descriptors.c)
target_include_directories(ns_controller_fw PRIVATE src)
target_compile_definitions(ns_controller_fw PRIVATE FW_VERSION="${FW_VERSION}" PICO_BOARD="${PICO_BOARD}")
target_compile_options(ns_controller_fw PRIVATE -Wall -Wextra)
target_link_libraries(ns_controller_fw PRIVATE pico_stdlib hardware_uart hardware_watchdog tinyusb_device)
if (PICO_CYW43_SUPPORTED)
    target_link_libraries(ns_controller_fw PRIVATE pico_cyw43_arch_none)
endif ()

# USB belongs to the Switch and UART0 to our own log, so no SDK stdio at all.
pico_enable_stdio_usb(ns_controller_fw 0)
pico_enable_stdio_uart(ns_controller_fw 0)
pico_add_extra_outputs(ns_controller_fw)
