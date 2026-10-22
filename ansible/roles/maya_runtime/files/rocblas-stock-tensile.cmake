# Build orchestration only: use the pinned runtime's existing full kernel data.
# Tensile's supported TENSILE_SKIP_LIBRARY avoids generation, while rocBLAS
# still unconditionally adds a dependency on this target. Supply that target
# without changing either the upstream source or any device arithmetic.
if(NOT "$ENV{TENSILE_SKIP_LIBRARY}" STREQUAL "1")
    message(FATAL_ERROR "This initializer requires TENSILE_SKIP_LIBRARY=1")
endif()
if(NOT TARGET TENSILE_LIBRARY_TARGET)
    add_custom_target(TENSILE_LIBRARY_TARGET)
endif()
