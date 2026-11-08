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

file(GLOB SEQUENCE_FILES ${CMAKE_CURRENT_LIST_DIR}/../sequences/*.txt)
list(SORT SEQUENCE_FILES)
find_package(Python3 REQUIRED COMPONENTS Interpreter)
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/generated/sequences.h
    COMMAND ${CMAKE_COMMAND} -E make_directory ${CMAKE_CURRENT_BINARY_DIR}/generated
    COMMAND Python3::Interpreter ${CMAKE_CURRENT_LIST_DIR}/../tools/macro2c.py
            ${CMAKE_CURRENT_BINARY_DIR}/generated/sequences.h ${SEQUENCE_FILES}
    DEPENDS ${CMAKE_CURRENT_LIST_DIR}/../tools/macro2c.py ${SEQUENCE_FILES})

add_executable(test_player test_player.c ${SRC}/player.c ${CMAKE_CURRENT_BINARY_DIR}/generated/sequences.h)
target_include_directories(test_player PRIVATE ${SRC} ${CMAKE_CURRENT_BINARY_DIR}/generated)
target_compile_options(test_player PRIVATE -Wall -Wextra -Werror -fsanitize=address,undefined)
target_link_options(test_player PRIVATE -fsanitize=address,undefined)

enable_testing()
add_test(NAME procon COMMAND test_procon)
add_test(NAME player COMMAND test_player)
add_test(NAME macro2c COMMAND Python3::Interpreter ${CMAKE_CURRENT_LIST_DIR}/test_macro2c.py)
