include_guard(GLOBAL)
include(CMakeParseArguments)

get_filename_component(CANOPENGEN_SOURCE_DIR "${CMAKE_CURRENT_LIST_DIR}/.." ABSOLUTE)
set(CANOPEN_GEN_DIR "${CANOPENGEN_SOURCE_DIR}" CACHE PATH "CanOpenGen checkout directory")
set(CANOPEN_DEFINITIONS_DIR "" CACHE PATH "CanOpenDefinitions checkout directory")
set(CANOPEN_LOCAL_DEVICE "" CACHE STRING "Local CANopen Device YAML filename stem")
set(CANOPEN_REMOTE_DEVICES "" CACHE STRING "Semicolon-separated remote Device YAML filename stems")
set(CANOPENGEN_EDS2OD "" CACHE FILEPATH "Optional Eds2Od executable override")

find_package(Python3 3.11 REQUIRED COMPONENTS Interpreter)

function(canopen_device)
    cmake_parse_arguments(ARG "" "NAME;CONFIG;OUTPUT_DIR;EDS2OD_NAMESPACE" "" ${ARGN})
    foreach(required NAME CONFIG OUTPUT_DIR)
        if(NOT ARG_${required})
            message(FATAL_ERROR "canopen_device requires ${required}")
        endif()
    endforeach()
    get_filename_component(config "${ARG_CONFIG}" ABSOLUTE BASE_DIR "${CMAKE_CURRENT_SOURCE_DIR}")
    if(NOT EXISTS "${config}")
        message(FATAL_ERROR "CANopen Device YAML does not exist: ${config}")
    endif()
    get_filename_component(config_directory "${config}" DIRECTORY)
    get_filename_component(project_root "${config_directory}" DIRECTORY)
    get_filename_component(artifact_name "${config}" NAME_WE)
    get_filename_component(output_dir "${ARG_OUTPUT_DIR}" ABSOLUTE BASE_DIR "${CMAKE_CURRENT_BINARY_DIR}")
    file(GLOB_RECURSE generator_sources CONFIGURE_DEPENDS "${CANOPENGEN_SOURCE_DIR}/canopengen/*.py")
    file(GLOB_RECURSE module_sources CONFIGURE_DEPENDS "${project_root}/Modules/*.yml")
    set(outputs
        "${output_dir}/${artifact_name}.eds"
        "${output_dir}/${artifact_name}.md"
        "${output_dir}/${artifact_name}Objects.hpp"
        "${output_dir}/${artifact_name}Od.cpp"
        "${output_dir}/${artifact_name}Od.hpp"
    )
    set(namespace_argument)
    if(ARG_EDS2OD_NAMESPACE)
        set(namespace_argument --eds2od-namespace "${ARG_EDS2OD_NAMESPACE}")
    endif()
    set(eds2od_argument)
    if(CANOPENGEN_EDS2OD)
        set(eds2od_argument --eds2od "${CANOPENGEN_EDS2OD}")
    endif()
    add_custom_command(
        OUTPUT ${outputs}
        COMMAND "${CMAKE_COMMAND}" -E make_directory "${output_dir}"
        COMMAND "${CMAKE_COMMAND}" -E env "PYTHONPATH=${CANOPENGEN_SOURCE_DIR}"
            "${Python3_EXECUTABLE}" -m canopengen.cli generate "${config}" --output "${output_dir}"
            ${namespace_argument} ${eds2od_argument}
        DEPENDS "${config}" ${module_sources} ${generator_sources}
            "${CANOPENGEN_SOURCE_DIR}/schemas/canopengen.schema.json"
            "${CANOPENGEN_SOURCE_DIR}/third_party/Eds2Od/Eds2Od/Eds2Od.csproj"
        WORKING_DIRECTORY "${CANOPENGEN_SOURCE_DIR}"
        COMMENT "Generating CANopen artifacts for ${artifact_name}"
        VERBATIM
    )
    add_custom_target("${ARG_NAME}_canopen" DEPENDS ${outputs})
endfunction()

function(canopen_firmware)
    cmake_parse_arguments(ARG "" "TARGET;DEFINITIONS_DIR;OUTPUT_DIR" "LOCAL;REMOTE" ${ARGN})
    foreach(required TARGET LOCAL DEFINITIONS_DIR)
        if(NOT ARG_${required})
            message(FATAL_ERROR "canopen_firmware requires ${required}")
        endif()
    endforeach()
    get_filename_component(definitions_dir "${ARG_DEFINITIONS_DIR}" ABSOLUTE BASE_DIR "${CMAKE_CURRENT_SOURCE_DIR}")
    if(NOT IS_DIRECTORY "${definitions_dir}/Device" OR NOT IS_DIRECTORY "${definitions_dir}/Modules")
        message(FATAL_ERROR
            "DEFINITIONS_DIR must contain Device/ and Modules/: ${definitions_dir}"
        )
    endif()
    if(ARG_OUTPUT_DIR)
        get_filename_component(output_root "${ARG_OUTPUT_DIR}" ABSOLUTE BASE_DIR "${CMAKE_CURRENT_BINARY_DIR}")
    else()
        set(output_root "${CMAKE_CURRENT_BINARY_DIR}/generated/canopen")
    endif()

    set(device_names "${ARG_LOCAL}" ${ARG_REMOTE})
    list(REMOVE_DUPLICATES device_names)
    set(generation_targets)
    foreach(device_name IN LISTS device_names)
        set(config "${definitions_dir}/Device/${device_name}.yml")
        set(output_dir "${output_root}/${device_name}")
        set(generation_target "${ARG_TARGET}_${device_name}")
        if(device_name STREQUAL ARG_LOCAL)
            canopen_device(
                NAME "${generation_target}"
                CONFIG "${config}"
                OUTPUT_DIR "${output_dir}"
            )
        else()
            canopen_device(
                NAME "${generation_target}"
                CONFIG "${config}"
                OUTPUT_DIR "${output_dir}"
                EDS2OD_NAMESPACE "${device_name}"
            )
        endif()
        list(APPEND generation_targets "${generation_target}_canopen")
    endforeach()
    add_custom_target("${ARG_TARGET}_canopen" DEPENDS ${generation_targets})
    if(TARGET "${ARG_TARGET}")
        add_dependencies("${ARG_TARGET}" "${ARG_TARGET}_canopen")
    endif()
endfunction()
