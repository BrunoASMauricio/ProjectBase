# PROJECTBASE
### <- CMake related configs (dont change)
##  <- Project related templates (adapt)
#   <- Project specific add-ons (add as needed)

### RESPECT THE CURRENT ORDER OF COMMANDS

### Obtain this repositorys' name
get_filename_component(RepositoryName ${CMAKE_CURRENT_LIST_DIR} NAME)
string(REPLACE " " "_" RepositoryName ${RepositoryName})

MESSAGE("Generating ${RepositoryName}")


### Remove existing variables
unset(repository_source_files)
unset(src_path)
unset(header_path)
unset(REPO_CODE_PATH)
unset(REPO_PATH)
unset(DEPENDENCY_HEADER_INCLUDES)
unset(DEPENDENCY_LIBS)
unset(EXECUTABLES)
unset(REP_C_FLAGS)
unset(CUSTOM_C_FLAGS)
unset(REP_DEBUG_C_FLAGS)
unset(REP_RELEASE_C_FLAGS)

###Setup useful variables
SET(src_path ${CMAKE_CURRENT_LIST_DIR}/code/source)
SET(header_path ${CMAKE_CURRENT_LIST_DIR}/code/headers)
SET(REPO_CODE_PATH ${CMAKE_CURRENT_LIST_DIR}/code)
SET(REPO_PATH ${CMAKE_CURRENT_LIST_DIR})

SET(DEPENDENCY_HEADER_INCLUDES
$$INCLUDEREPOSITORYDIRECTORIES$$
)

SET(DEPENDENCY_LIBS
$$LINKDEPENDENCIES$$
)

SET(EXECUTABLES)
SET(TESTS)

### Include custom CMakeLists
if(EXISTS ${CMAKE_CURRENT_LIST_DIR}/configs/CMakeLists.txt)
	include(${CMAKE_CURRENT_LIST_DIR}/configs/CMakeLists.txt)

	SET(CUSTOM_C_FLAGS "")
	### Use repository specific C Flags
	if( DEFINED REP_C_FLAGS )
		LIST(APPEND CUSTOM_C_FLAGS ${REP_C_FLAGS})
	endif()

	IF ( DEFINED REP_DEBUG_C_FLAGS  AND "${BUILD_MODE}" STREQUAL "Debug")
		LIST(APPEND CUSTOM_C_FLAGS ${REP_DEBUG_C_FLAGS})
	ENDIF()

	IF ( DEFINED REP_RELEASE_C_FLAGS  AND "${BUILD_MODE}" STREQUAL "Release")
		LIST(APPEND CUSTOM_C_FLAGS ${REP_RELEASE_C_FLAGS})
	ENDIF()

	### In case the custom CMakeLists defined any source files
	list(LENGTH repository_source_files ${RepositoryName}ListSize)
	if( NOT ${RepositoryName}ListSize EQUAL 0)

		### Setup library to be imported by other repositorys
		add_library(${RepositoryName}_lib ${repository_source_files})

		list(APPEND EXECUTABLES ${RepositoryName}_lib)

	endif()

	foreach(EXECUTABLE ${EXECUTABLES})
		### Setup executable path
		set_target_properties(${EXECUTABLE} PROPERTIES
			RUNTIME_OUTPUT_DIRECTORY ${EXECS_PATH}
		)

		target_compile_options(${EXECUTABLE} PRIVATE ${CUSTOM_C_FLAGS})

		### Allow extra links to be made
		if( DEFINED extra_libraries_to_link )
			target_link_libraries(${EXECUTABLE} ${extra_libraries_to_link})
		endif()
		
		### Include dependency repository directories 
		target_include_directories(${EXECUTABLE}
			PUBLIC
			${DEPENDENCY_HEADER_INCLUDES}
		)

		### Link executable to dependency repositories
		target_link_libraries(${EXECUTABLE}
			${DEPENDENCY_LIBS}
		)
	endforeach()

	foreach(TEST ${TESTS})

		### Setup test path
		set_target_properties(${TEST} PROPERTIES
			RUNTIME_OUTPUT_DIRECTORY ${TESTS_PATH}
		)

		### Use repository specific C Flags
		target_compile_options(${TEST} PRIVATE ${CUSTOM_C_FLAGS})

		### Allow extra links to be made
		if( DEFINED extra_libraries_to_link )
			target_link_libraries(${TEST} ${extra_libraries_to_link})
		endif()
		
		### Include dependency repository directories 
		target_include_directories(${TEST}
			PUBLIC
			${DEPENDENCY_HEADER_INCLUDES}
			$$TEST_HEADER_INCLUDES$$
		)

		### Link executable to dependency repositories
		target_link_libraries(${TEST}
			${DEPENDENCY_LIBS}
		)
	endforeach()


endif()