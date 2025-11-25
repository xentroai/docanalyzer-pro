cmake_minimum_required(VERSION 3.10)
project(DocAnalyzerPro)

set(CMAKE_CXX_STANDARD 17)

find_package(PkgConfig REQUIRED)

# 1. Find Libraries
pkg_check_modules(POPPLER REQUIRED poppler-cpp)
pkg_check_modules(TESSERACT REQUIRED tesseract)
pkg_check_modules(LEPTONICA REQUIRED lept)

# 2. Find OpenCV (The new "Glasses")
find_package(OpenCV REQUIRED)

# 3. Find JSON
find_path(JSON_INCLUDE_DIR nlohmann/json.hpp)

include_directories(
    ${POPPLER_INCLUDE_DIRS}
    ${TESSERACT_INCLUDE_DIRS}
    ${LEPTONICA_INCLUDE_DIRS}
    ${JSON_INCLUDE_DIR}
    ${OpenCV_INCLUDE_DIRS} 
)

add_executable(docproc src/cpp/main.cpp)

target_link_libraries(docproc 
    ${POPPLER_LIBRARIES} 
    ${TESSERACT_LIBRARIES}
    ${LEPTONICA_LIBRARIES}
    ${OpenCV_LIBS} # Link OpenCV
)