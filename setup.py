from setuptools import setup
from setuptools.extension import Extension
from Cython.Build import cythonize
import os
import sys
# Windows args
if os.name == "nt":
    comp_args = ['/Ox', '/Ob2', '/Ot', '/GL', '/DNDEBUG']
    link_args = ['/LTCG', '/OPT:REF', '/OPT:ICF']
# Linux args
else:
    comp_args = ["-O3", "-march=native", "-flto",
                 "-fomit-frame-pointer", "-DNDEBUG"]
    link_args = ["-flto"]

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
        include_path=["NonagaGame"],
        compiler_directives={
            "language_level": "3",
            "boundscheck": False,
            "wraparound": False,
        },
        annotate=True,
    ),
    zip_safe=False,
)
