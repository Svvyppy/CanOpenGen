include_guard(GLOBAL)
include(CMakeParseArguments)
get_filename_component(CANOPENGEN_SOURCE_DIR "${CMAKE_CURRENT_LIST_DIR}/.." ABSOLUTE)
find_package(Python3 3.11 REQUIRED COMPONENTS Interpreter)

function(canopen_device)
    cmake_parse_arguments(ARG "" "NAME;CONFIG;OUTPUT_DIR" "" ${ARGN})
    foreach(required NAME CONFIG OUTPUT_DIR)
        if(NOT ARG_${required})
            message(FATAL_ERROR "canopen_device requires ${required}")
        endif()
    endforeach()
    get_filename_component(config "${ARG_CONFIG}" ABSOLUTE BASE_DIR "${CMAKE_CURRENT_SOURCE_DIR}")
    get_filename_component(config_directory "${config}" DIRECTORY)
    get_filename_component(project_root "${config_directory}" DIRECTORY)
    get_filename_component(output_dir "${ARG_OUTPUT_DIR}" ABSOLUTE BASE_DIR "${CMAKE_CURRENT_BINARY_DIR}")
    file(GLOB_RECURSE generator_sources CONFIGURE_DEPENDS "${CANOPENGEN_SOURCE_DIR}/canopengen/*.py")
    file(GLOB_RECURSE module_sources CONFIGURE_DEPENDS "${project_root}/Modules/*.yml")
    set(outputs "${output_dir}/${ARG_NAME}.eds" "${output_dir}/${ARG_NAME}.md"
        "${output_dir}/${ARG_NAME}Od.cpp" "${output_dir}/${ARG_NAME}Od.hpp")
    add_custom_command(
        OUTPUT ${outputs}
        COMMAND "${CMAKE_COMMAND}" -E make_directory "${output_dir}"
        COMMAND "${CMAKE_COMMAND}" -E env "PYTHONPATH=${CANOPENGEN_SOURCE_DIR}"
            "${Python3_EXECUTABLE}" -m canopengen generate "${config}" --output "${output_dir}"
        DEPENDS "${config}" ${module_sources} ${generator_sources}
            "${CANOPENGEN_SOURCE_DIR}/schemas/canopengen.schema.json"
            "${CANOPENGEN_SOURCE_DIR}/third_party/Eds2Od/Eds2Od/Eds2Od.csproj"
        WORKING_DIRECTORY "${CANOPENGEN_SOURCE_DIR}"
        COMMENT "Generating CANopen artifacts for ${ARG_NAME}"
        VERBATIM)
    add_custom_target("${ARG_NAME}_canopen" DEPENDS ${outputs})
endfunction()
