from setuptools import setup
from Cython.Build import cythonize
import os

setup(
    name="nonaga",
    ext_modules=cythonize(
        ["My Nonaga/nonaga_board.pyx", "My Nonaga/nonaga_logic.pyx"],
        compiler_directives={
            "language_level": "3",
            "boundscheck": False,
            "wraparound": False,
        },
    ),
    zip_safe=False,
)

