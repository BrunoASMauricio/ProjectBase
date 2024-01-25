# PROJECTBASE
### <- CMake related configs (dont change)
##  <- Project related templates (adapt)
#   <- Project specific add-ons (add as needed)

### RESPECT THE CURRENT ORDER OF COMMANDS

### Cmake minimum version
CMAKE_MINIMUM_REQUIRED(VERSION 3.28)

### Setup configuration file in binary tree
#configure_file(TutorialConfig.h.in TutorialConfig.h)

### Obtain this projects' name
get_filename_component(ProjectName ${CMAKE_CURRENT_LIST_DIR} NAME)
string(REPLACE " " "_" ProjectName ${ProjectName})

MESSAGE("Launching CMake for project ${ProjectName}")

### Set the project name
PROJECT("${ProjectName}")
### Eventually add project version
#project("${ProjectName}" VERSION 1.0)

### Add binary dir to project
#target_include_directories(${ProjectName} PUBLIC
#                           "${PROJECT_BINARY_DIR}"
#                           )

### Then add this to it
#// the configured options and settings for ${ProjectName}
##define ${ProjectName}_VERSION_MAJOR @${ProjectName}_VERSION_MAJOR@
##define ${ProjectName}_VERSION_MINOR @${ProjectName}_VERSION_MINOR@


### c++20 standards
SET(CMAKE_CXX_STANDARD 20)

### Set global module variables
SET(BASE_DIR ${CMAKE_CURRENT_LIST_DIR})
SET(BIN_PATH ${CMAKE_CURRENT_LIST_DIR}/binaries)
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

### Default to debug build
IF (NOT DEFINED BUILD_MODE)
  SET(BUILD_MODE "DEBUG")
ENDIF()

MACRO(COMPILE_EXECUTABLE EXECUTABLE_NAME EXECUTABLE_SOURCE)
    ADD_EXECUTABLE(${EXECUTABLE_NAME} ${EXECUTABLE_SOURCE})
    TARGET_LINK_LIBRARIES(${EXECUTABLE_NAME} ${RepositoryName}_lib)
    LIST(APPEND EXECUTABLES ${EXECUTABLE_NAME})
ENDMACRO()

MACRO(COMPILE_TEST TEST_NAME TEST_SOURCE)
    ADD_EXECUTABLE(${TEST_NAME} ${TEST_SOURCE})
    TARGET_LINK_LIBRARIES(${TEST_NAME} ${RepositoryName}_lib)
    LIST(APPEND TESTS ${TEST_NAME})
ENDMACRO()

### Include this modules' CMakeLists
$$INCLUDEREPOSITORYCMAKELISTS$$

## Activate compiler flags
#add_definitions(${GCC_COMPILE_FLAGS})
SET(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${GCC_COMPILE_FLAGS}")

SET(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} ${GCC_COMPILE_FLAGS}")