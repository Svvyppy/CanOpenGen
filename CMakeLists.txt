cmake_minimum_required(VERSION 3.20)

project(CanOpenGen LANGUAGES NONE)

include("${CMAKE_CURRENT_SOURCE_DIR}/cmake/CanOpenGen.cmake")
option(CANOPENGEN_BUILD_EXAMPLE "Generate the bundled PressureSensor artifacts" OFF)
if(CANOPENGEN_BUILD_EXAMPLE)
    canopen_firmware(
        TARGET PressureSensor
        LOCAL PressureSensor
        DEFINITIONS_DIR "${CMAKE_CURRENT_SOURCE_DIR}/examples/definitions"
    )
endif()

find_package(Doxygen QUIET)
if(Doxygen_FOUND)
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
else()
    message(STATUS "Doxygen not found; the optional docs target is unavailable")
endif()
