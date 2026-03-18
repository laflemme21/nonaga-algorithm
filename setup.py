from setuptools import setup
from setuptools.extension import Extension
from Cython.Build import cythonize
import os
import sys

if os.name == "nt":
    comp_args = ['/O2', '/Ob2', '/Zi']
    link_args = ['/DEBUG', '/OPT:REF', '/OPT:ICF']
else:
    comp_args = ["-O3", "-march=native"]
    link_args = []

setup(
    name="nonaga",
    ext_modules=cythonize(
        [
            Extension(
                "nonaga_constants",
                ["NonagaGame/nonaga_constants.pyx"],
                extra_compile_args=comp_args,
                extra_link_args=link_args,
            ),
            Extension(
                "nonaga_logic",
                ["NonagaGame/nonaga_logic.pyx", "NonagaGame/nonaga_bitboard.c"],
                include_dirs=["NonagaGame"],
                extra_compile_args=comp_args,
                extra_link_args=link_args,
            ),
            Extension(
                "AI",
                ["NonagaGame/AI.pyx", "NonagaGame/AI_core.c",
                    "NonagaGame/nonaga_bitboard.c"],
                include_dirs=["NonagaGame"],
                extra_compile_args=comp_args,
                extra_link_args=link_args,
            ),
            Extension(
                "nonaga_bitboard_wrapper",
                ["NonagaGame/nonaga_bitboard_wrapper.pyx",
                    "NonagaGame/nonaga_bitboard.c"],
                include_dirs=["NonagaGame"],
                extra_compile_args=comp_args,
                extra_link_args=link_args,
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
