# PROJECTBASE
### <- CMake related configs (dont change)
##  <- Project related templates (adapt)
#   <- Project specific add-ons (add as needed)

### RESPECT THE CURRENT ORDER OF COMMANDS

### Obtain this repositorys' name
get_filename_component(RepositoryName $$REPO_SOURCES$$ NAME)
string(REPLACE " " "_" RepositoryName ${RepositoryName})

MESSAGE("Generating ${RepositoryName}")


### Remove existing variables
unset(repository_source_files)
unset(REPO_CODE_PATH)
unset(REPO_PATH)
unset(PUBLIC_HEADERS)
unset(PRIVATE_HEADERS)
unset(TEST_HEADERS)
unset(DEPENDENCY_LIBS)
unset(EXECUTABLES)
unset(REP_C_FLAGS)
unset(CUSTOM_C_FLAGS)
unset(REP_DEBUG_C_FLAGS)
unset(REP_RELEASE_C_FLAGS)

### Setup useful variables
SET(PROJECT_PATH $$PROJECT_PATH$$)
SET(REPO_CODE_PATH $$REPO_SOURCES$$/code)
SET(REPO_PATH $$REPO_SOURCES$$)
SET(REPO_NAME $$REPO_NAME$$)

### Headers available from dependency repositories
SET(PUBLIC_HEADERS
$$PUBLIC_INCLUDES$$
)

### Headers local to this repository
SET(PRIVATE_HEADERS
$$PRIVATE_INCLUDES$$
)

### Headers for testing only
SET(TEST_HEADERS
$$TESTS_INCLUDES$$
)

SET(DEPENDENCY_LIBS
$$LINK_DEPENDENCIES$$
)

SET(EXECUTABLES)
SET(TESTS)

### Include custom CMakeLists
if(EXISTS $$REPO_SOURCES$$/configs/CMakeLists.txt)
	include($$REPO_SOURCES$$/configs/CMakeLists.txt)

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
		add_library(${RepositoryName}_lib SHARED ${repository_source_files})

		target_include_directories(${RepositoryName}_lib
			PUBLIC
			${PUBLIC_HEADERS}
			${PRIVATE_HEADERS}
			${TEST_HEADERS}
		)

		### Allow extra links to be made
		if( DEFINED extra_libraries_to_link )
			### Set to PRIVATE to isolate the library
			target_link_libraries(${RepositoryName}_lib PRIVATE ${extra_libraries_to_link})
		endif()

		list(APPEND DEPENDENCY_LIBS ${RepositoryName}_lib)
	endif()

	foreach(EXECUTABLE ${EXECUTABLES})
		### Setup executable path
		set_target_properties(${EXECUTABLE} PROPERTIES
			RUNTIME_OUTPUT_DIRECTORY ${EXECS_PATH}
		)

		target_compile_options(${EXECUTABLE} PRIVATE ${CUSTOM_C_FLAGS})

		### Include dependency repository directories 
		target_include_directories(${EXECUTABLE}
			PUBLIC
			${PUBLIC_HEADERS}
			${PRIVATE_HEADERS}
		)

		### Link executable to dependency repositories
		target_link_libraries(${EXECUTABLE}
			-Wl,--whole-archive
			${DEPENDENCY_LIBS}
			-Wl,--no-whole-archive
		)
	endforeach()

	foreach(TEST ${TESTS})

		### Setup test path
		set_target_properties(${TEST} PROPERTIES
			RUNTIME_OUTPUT_DIRECTORY ${TESTS_PATH}
		)

		### Use repository specific C Flags
		target_compile_options(${TEST} PRIVATE ${CUSTOM_C_FLAGS})
		
		### Include dependency repository directories 
		target_include_directories(${TEST}
			PUBLIC
			${PUBLIC_HEADERS}
			${PRIVATE_HEADERS}
			${TEST_HEADERS}
		)

		### Link executable to dependency repositories
		target_link_libraries(${TEST}
			${DEPENDENCY_LIBS}
		)
	endforeach()

endif()