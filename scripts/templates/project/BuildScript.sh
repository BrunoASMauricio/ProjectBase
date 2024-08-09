# Remove previous build objects
#rm -rf cmake/*

# Configure and build project
cmake -S . -B cmake

cmake --build cmake
