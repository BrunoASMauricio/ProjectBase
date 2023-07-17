# PROJECTBASE
### <- CMake related configs (dont change)
##  <- Project related templates (adapt)
#   <- Project specific add-ons (add as needed)

### RESPECT THE CURRENT ORDER OF COMMANDS

### Cmake minimum version
CMAKE_MINIMUM_REQUIRED(VERSION 3.18)

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


### c++17 standards
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

### Include this modules' CMakeLists
$$INCLUDEREPOSITORYCMAKELISTS$$

## Activate compiler flags
#add_definitions(${GCC_COMPILE_FLAGS})
SET(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${GCC_COMPILE_FLAGS} -std=c++20 -O0 -lpthread -fPIC -pthread -ggdb3 -Wall -fdata-sections -ffunction-sections")