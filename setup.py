from setuptools import setup
from Cython.Build import cythonize
import os

setup(
    name="nonaga",
    ext_modules=cythonize(
        ["NonagaGame/nonaga_board.pyx", "NonagaGame/nonaga_logic.pyx", "NonagaGame/AI.pyx"],
        compiler_directives={
            "language_level": "3",
            "boundscheck": False,
            "wraparound": False,
        },
    ),
    zip_safe=False,
)

