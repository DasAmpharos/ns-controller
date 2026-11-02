# Host unit tests for the hardware-free firmware modules.
#   cmake -S test -B build-test && cmake --build build-test && ctest --test-dir build-test --output-on-failure
cmake_minimum_required(VERSION 3.13)
project(ns_controller_firmware_tests C)

set(CMAKE_C_STANDARD 11)
set(SRC ${CMAKE_CURRENT_LIST_DIR}/../src)

add_executable(test_procon test_procon.c ${SRC}/procon.c ${SRC}/procon_data.c)
target_include_directories(test_procon PRIVATE ${SRC} ${CMAKE_CURRENT_LIST_DIR})
target_compile_options(test_procon PRIVATE -Wall -Wextra -Werror -fsanitize=address,undefined)
target_link_options(test_procon PRIVATE -fsanitize=address,undefined)

enable_testing()
add_test(NAME procon COMMAND test_procon)
