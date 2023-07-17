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

	### In case the custom CMakeLists defined any source files
	list(LENGTH repository_source_files ${RepositoryName}ListSize)
	if( NOT ${RepositoryName}ListSize EQUAL 0)

		### Setup library to be imported by other repositorys
		add_library(${RepositoryName}_lib ${repository_source_files})

		list(APPEND EXECUTABLES ${RepositoryName}_lib)

	endif()

	foreach(EXECUTABLE ${EXECUTABLES})
		set_target_properties(${EXECUTABLE} PROPERTIES
			RUNTIME_OUTPUT_DIRECTORY ${EXECS_PATH}
		)

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

		set_target_properties(${TEST} PROPERTIES
			RUNTIME_OUTPUT_DIRECTORY ${TESTS_PATH}
		)

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