# PROJECTBASE
### <- CMake related configs (dont change)
##  <- Project related templates (adapt)
#   <- Project specific add-ons (add as needed)

### RESPECT THE CURRENT ORDER OF COMMANDS

### Cmake minimum version
CMAKE_MINIMUM_REQUIRED(VERSION 3.6)

### Setup configuration file in binary tree
#configure_file(TutorialConfig.h.in TutorialConfig.h)

### Obtain this projects' name
MESSAGE("Launching CMake for project ${PROJECT_NAME}")

### Set the project name
PROJECT("${PROJECT_NAME}")
### Eventually add project version
#project("${PROJECT_NAME}" VERSION 1.0)

### Add binary dir to project
#target_include_directories(${PROJECT_NAME} PUBLIC
#                           "${PROJECT_BINARY_DIR}"
#                           )

### Then add this to it
#// the configured options and settings for ${PROJECT_NAME}
##define ${PROJECT_NAME}_VERSION_MAJOR @${PROJECT_NAME}_VERSION_MAJOR@
##define ${PROJECT_NAME}_VERSION_MINOR @${PROJECT_NAME}_VERSION_MINOR@


### c++20 standards
SET(CMAKE_CXX_STANDARD 20)

### Set global module variables
SET(BIN_PATH $$PROJECT_PATH$$/binaries)
SET(OBJS_PATH ${BIN_PATH}/objects)
SET(EXECS_PATH ${OBJS_PATH}/executables)
SET(TESTS_PATH ${OBJS_PATH}/tests)
SET(LIB_PATH ${BIN_PATH}/libs)

### Configure Cmake to behave according to the project structure
SET(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${LIB_PATH})
SET(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${LIB_PATH})
SET(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${OBJS_PATH})

### Set base compiler flags
SET(GCC_COMPILE_FLAGS "")
SET(GLOBAL_COMPILE_FLAGS_BUILD "")

###                 SETUP macros
### Prepare a normal executable to be compiled
MACRO(COMPILE_EXECUTABLE EXECUTABLE_NAME EXECUTABLE_SOURCE)
    ADD_EXECUTABLE(${EXECUTABLE_NAME} ${EXECUTABLE_SOURCE})
    TARGET_LINK_LIBRARIES(${EXECUTABLE_NAME} ${RepositoryName}_lib)
    LIST(APPEND EXECUTABLES ${EXECUTABLE_NAME})
ENDMACRO()

### Prepare a test executable to be compiled
MACRO(COMPILE_TEST TEST_NAME TEST_SOURCE)
    set(FULL_TEST_NAME "${REPO_NAME}_${TEST_NAME}")

    ADD_EXECUTABLE(${FULL_TEST_NAME} ${TEST_SOURCE})
    TARGET_LINK_LIBRARIES(${FULL_TEST_NAME} ${RepositoryName}_lib)
    LIST(APPEND TESTS ${FULL_TEST_NAME})
ENDMACRO()

### Copy file over to tests folder
MACRO(SETUP_GENERIC_FILE PATH_TYPE FILE_TYPE FILE_PATH)
message("Setting up ${FILE_PATH} as a ${FILE_TYPE} file in the ${PATH_TYPE} folder")
execute_process (
    COMMAND python ${PROJECT_BASE_SCRIPT_PATH}/handle_script_setup.py ${PROJECT_NAME} ${PATH_TYPE} ${FILE_TYPE} ${FILE_PATH}
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)
ENDMACRO()

MACRO(SETUP_TEST_DATA FILE_PATH)
    SETUP_GENERIC_FILE("tests" "data" ${FILE_PATH})
ENDMACRO()

### Copy file over to executables folder
MACRO(SETUP_EXECUTABLE_DATA FILE_PATH)
    SETUP_GENERIC_FILE("executables" "data" ${FILE_PATH})
ENDMACRO()

### Copy file over to tests folder and make it executable
MACRO(SETUP_TEST_EXEC FILE_PATH)
SETUP_GENERIC_FILE("tests" "exec" ${FILE_PATH})
ENDMACRO()

### Copy file over to executables folder and make it executable
MACRO(SETUP_EXECUTABLE_EXEC FILE_PATH)
    SETUP_GENERIC_FILE("executables" "exec" ${FILE_PATH})
ENDMACRO()

### Include this modules' CMakeLists
$$INCLUDE_REPOSITORY_CMAKELISTS$$

## Activate compiler flags
#add_definitions(${GCC_COMPILE_FLAGS})
SET(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${GCC_COMPILE_FLAGS} -Wstrict-prototypes -DENABLE_SANITY_CHECKS -g3 -O0  -fwrapv -ftrapv -fno-delete-null-pointer-checks -Wno-missing-field-initializers -Wall -Wextra -Werror -Wconversion -Wno-type-limits -Wno-unused-function")

SET(CMAKE_C_FLAGS "${CMAKE_C_FLAGS}     ${GCC_COMPILE_FLAGS} -Wstrict-prototypes -DENABLE_SANITY_CHECKS -Wno-implicit-int -g3 -O0  -fwrapv -ftrapv -fno-delete-null-pointer-checks -Wno-c90-c99-compat -Wno-missing-field-initializers -Wall -Wextra -Werror -Wconversion -Wno-type-limits -Wno-unused-function")
