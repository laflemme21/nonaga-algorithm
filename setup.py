from setuptools import setup
from setuptools.extension import Extension
from Cython.Build import cythonize
import os
comp_args = ["-g"]
setup(
    name="nonaga",
    ext_modules=cythonize(
        [
            Extension("nonaga_constants", ["NonagaGame/nonaga_constants.pyx"]),
            Extension(
                "nonaga_logic",
                ["NonagaGame/nonaga_logic.pyx", "NonagaGame/nonaga_bitboard.c"],
                include_dirs=["NonagaGame"],
                extra_compile_args=comp_args
            ),
            Extension(
                "AI",
                ["NonagaGame/AI.pyx", "NonagaGame/AI_core.c",
                    "NonagaGame/nonaga_bitboard.c"],
                include_dirs=["NonagaGame"],
                extra_compile_args=comp_args
            ),
            Extension(
                "nonaga_bitboard_wrapper",
                ["NonagaGame/nonaga_bitboard_wrapper.pyx",
                    "NonagaGame/nonaga_bitboard.c"],
                include_dirs=["NonagaGame"],
                extra_compile_args=comp_args
            ),
        ],
        compiler_directives={
            "language_level": "3",
            "boundscheck": False,
            "wraparound": False,
        },
        annotate=True,
    ),
    zip_safe=False,
)
