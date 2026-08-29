cmake_minimum_required(VERSION 3.20)

project(CanOpenGen LANGUAGES NONE)

find_package(Doxygen REQUIRED)

set(CANOPENGEN_DOXYGEN_OUTPUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/docs")
configure_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/Doxyfile"
    "${CMAKE_CURRENT_BINARY_DIR}/Doxyfile"
    @ONLY
)

add_custom_target(
    docs
    COMMAND Doxygen::doxygen "${CMAKE_CURRENT_BINARY_DIR}/Doxyfile"
    WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
    COMMENT "Generating CanOpenGen API documentation"
    VERBATIM
)

