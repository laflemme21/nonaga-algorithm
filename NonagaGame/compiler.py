import subprocess
import shutil
import glob
import sys
import os


def compile_cython_files():
    """Compiles the Cython files for improved performance."""
    # setup.py is in the project root (one level up from this file)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nonaga_dir = os.path.join(project_root, "NonagaGame")
    subprocess.check_call(
        [sys.executable, "setup.py", "build_ext", "--inplace"],
        cwd=project_root,
    )
    # Move compiled extension files (.pyd on Windows, .so on Linux/macOS) from project root into NonagaGame/
    for ext_file in glob.glob(os.path.join(project_root, "*.pyd")) + glob.glob(os.path.join(project_root, "*.so")):
        dest = os.path.join(nonaga_dir, os.path.basename(ext_file))
        if os.path.exists(dest):
            os.remove(dest)
        shutil.move(ext_file, dest)
        print(f"Moved {os.path.basename(ext_file)} -> NonagaGame/")
    print("Cython files compiled successfully.")
