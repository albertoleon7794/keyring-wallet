cmake_minimum_required(VERSION 3.13)
set(CMAKE_VERBOSE_MAKEFILE on)

file(GLOB react_codegen_SRCS CONFIGURE_DEPENDS *.cpp)

add_library(
  react_codegen_RNBcscCoreSpec
  OBJECT
  ${react_codegen_SRCS}
)

target_include_directories(react_codegen_RNBcscCoreSpec PUBLIC .)

target_link_libraries(
  react_codegen_RNBcscCoreSpec
  fbjni
  jsi
  reactnative
)

target_compile_options(
  react_codegen_RNBcscCoreSpec
  PRIVATE
  -DLOG_TAG=\"ReactNative\"
  -fexceptions
  -frtti
  -std=c++20
  -Wall
)
