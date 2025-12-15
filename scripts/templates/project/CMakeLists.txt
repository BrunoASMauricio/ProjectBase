# PROJECTBASE
### <- CMake related configs (dont change)
##  <- Project related templates (adapt)
#   <- Project specific add-ons (add as needed)

### RESPECT THE CURRENT ORDER OF COMMANDS

### Cmake minimum version
CMAKE_MINIMUM_REQUIRED(VERSION 4.0)
### Setup configuration file in binary tree
#configure_file(TutorialConfig.h.in TutorialConfig.h)

### Set global module variables
SET(PROJ_NAME       $$PROJ_NAME$$)
SET(PROJ_PATH       $$PROJ_PATH$$)
SET(PROJ_BUILD_PATH $$PROJ_BUILD_PATH$$)
SET(PROJ_BIN_PATH   $$PROJ_BIN_PATH$$)
SET(PROJ_LIB_PATH   $$PROJ_LIB_PATH$$)
SET(PROJ_OBJS_PATH  $$PROJ_OBJS_PATH$$)
SET(PROJ_EXECS_PATH $$PROJ_EXECS_PATH$$)
SET(PROJ_TESTS_PATH $$PROJ_TESTS_PATH$$)

### Obtain this projects' name
MESSAGE("Launching CMake for project ${PROJ_NAME}")

### Set the project name
PROJECT("${PROJ_NAME}")
### Eventually add project version
#project("${PROJ_NAME}" VERSION 1.0)

### Then add this to it
#// the configured options and settings for ${PROJ_NAME}
##define ${PROJ_NAME}_VERSION_MAJOR @${PROJ_NAME}_VERSION_MAJOR@
##define ${PROJ_NAME}_VERSION_MINOR @${PROJ_NAME}_VERSION_MINOR@


### c++20 standards
SET(CMAKE_CXX_STANDARD 20)

### Configure Cmake to behave according to the project structure
SET(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${PROJ_LIB_PATH})
SET(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${PROJ_LIB_PATH})
SET(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${PROJ_OBJS_PATH})

### Set base compiler flags
SET(GCC_COMPILE_FLAGS "-I $$AUTOGEN_HEADERS_PATH$$")
SET(GLOBAL_COMPILE_FLAGS_BUILD "")

###                 SETUP macros
### Prepare a normal executable to be compiled
MACRO(COMPILE_EXECUTABLE EXECUTABLE_NAME EXECUTABLE_SOURCE)
    ADD_EXECUTABLE(${EXECUTABLE_NAME} ${EXECUTABLE_SOURCE})
    #TARGET_LINK_LIBRARIES(${EXECUTABLE_NAME} ${RepositoryName}_lib)
    LIST(APPEND EXECUTABLES ${EXECUTABLE_NAME})
ENDMACRO()

### Prepare a test executable to be compiled
MACRO(COMPILE_TEST TEST_NAME TEST_SOURCE)
    set(FULL_TEST_NAME "${REPO_NAME}_${TEST_NAME}")
    ADD_EXECUTABLE(${FULL_TEST_NAME} ${TEST_SOURCE})
    ##TARGET_LINK_LIBRARIES(${FULL_TEST_NAME} ${RepositoryName}_lib)
    LIST(APPEND TESTS ${FULL_TEST_NAME})
ENDMACRO()

### Copy file over to tests folder
MACRO(SETUP_FILE PATH_TYPE FILE_TYPE FILE_PATH)
message("Setting up ${FILE_PATH} as a ${FILE_TYPE} file in the ${PATH_TYPE} folder")
execute_process (
    COMMAND python ${PROJECT_BASE_SCRIPT_PATH}/handle_script_setup.py ${PROJ_NAME} ${PATH_TYPE} ${FILE_TYPE} ${FILE_PATH}
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)
ENDMACRO()

MACRO(SETUP_TEST_DATA FILE_PATH)
    SETUP_FILE("tests" "data" ${FILE_PATH})
ENDMACRO()

### Copy file over to executables folder
MACRO(SETUP_EXECUTABLE_DATA FILE_PATH)
    SETUP_FILE("executables" "data" ${FILE_PATH})
ENDMACRO()

### Copy file over to tests folder and make it executable
MACRO(SETUP_TEST_EXEC FILE_PATH)
SETUP_FILE("tests" "exec" ${FILE_PATH})
ENDMACRO()

### Copy file over to executables folder and make it executable
MACRO(SETUP_EXECUTABLE_EXEC FILE_PATH)
    SETUP_FILE("executables" "exec" ${FILE_PATH})
ENDMACRO()

link_directories(AFTER ${PROJ_LIB_PATH})

### Include this modules' CMakeLists
$$INCLUDE_REPOSITORY_CMAKELISTS$$

## Activate compiler flags
#add_definitions(${GCC_COMPILE_FLAGS})
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${GCC_COMPILE_FLAGS} \
    -Wstrict-prototypes -DENABLE_SANITY_CHECKS -g3 -O0 \
    -fwrapv -ftrapv -fno-delete-null-pointer-checks \
    -Wno-missing-field-initializers -Wall -Wextra -Werror \
    -Wconversion -Wno-type-limits -Wno-unused-function -pg")

set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} ${GCC_COMPILE_FLAGS} \
    -Wstrict-prototypes -DENABLE_SANITY_CHECKS -Wno-implicit-int \
    -g3 -O0 -fwrapv -ftrapv -fno-delete-null-pointer-checks \
    -Wno-c90-c99-compat -Wno-missing-field-initializers -Wall \
    -Wextra -Werror -Wconversion -Wno-type-limits \
    -Wno-unused-function -pg")

# link flags: libraries and profiling
set(CMAKE_EXE_LINKER_FLAGS   "${CMAKE_EXE_LINKER_FLAGS}   -pg -lX11 -lXext -lncurses -lm")
set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -pg -lX11 -lXext -lncurses -lm")
