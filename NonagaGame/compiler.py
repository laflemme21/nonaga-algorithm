import subprocess
import shutil
import glob
import sys
import os


def _get_clean_build_env():
    env = os.environ.copy()
    env.pop("VSCMD_ARG_TGT_ARCH", None)
    env.pop("VSCMD_ARG_HOST_ARCH", None)
    env.pop("Platform", None)
    env.pop("PreferredToolArchitecture", None)
    return env


def compile_cython_files():
    """Compiles the Cython files for improved performance."""
    # setup.py is in the project root (one level up from this file)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nonaga_dir = os.path.join(project_root, "NonagaGame")
    subprocess.check_call(
        [sys.executable, "setup.py", "build_ext", "--inplace"],
        cwd=project_root,
        env=_get_clean_build_env(),
    )

    # Collect build artifacts from both --inplace output (project root) and build/lib output,
    # then deploy the newest binary for each extension module into NonagaGame/.
    modules = ["AI", "nonaga_bitboard_wrapper",
               "nonaga_constants", "nonaga_logic"]
    search_roots = [project_root] + \
        glob.glob(os.path.join(project_root, "build", "lib*"))
    copied = 0
    deployed_paths = set()

    for module in modules:
        candidates = []
        for root in search_roots:
            candidates.extend(glob.glob(os.path.join(root, f"{module}*.pyd")))
            candidates.extend(glob.glob(os.path.join(root, f"{module}*.so")))

        if not candidates:
            print(f"Warning: no compiled artifact found for {module}.")
            continue

        newest = max(candidates, key=os.path.getmtime)
        dest = os.path.join(nonaga_dir, os.path.basename(newest))
        try:
            shutil.copy2(newest, dest)
            copied += 1
            deployed_paths.add(os.path.abspath(dest))
            print(
                f"Copied {os.path.basename(newest)} -> NonagaGame/ (from {os.path.dirname(newest)})")
        except PermissionError:
            print(
                f"Warning: could not overwrite {os.path.basename(dest)} (file is in use). "
                "Close Python processes using that module and rerun compilation."
            )

    # Remove duplicate artifacts outside NonagaGame so runtime imports use the deployed binaries.
    for module in modules:
        for root in search_roots:
            for pattern in (f"{module}*.pyd", f"{module}*.so"):
                for artifact in glob.glob(os.path.join(root, pattern)):
                    artifact_abs = os.path.abspath(artifact)
                    if artifact_abs in deployed_paths:
                        continue
                    try:
                        os.remove(artifact)
                        print(f"Removed outside artifact: {artifact}")
                    except PermissionError:
                        print(
                            f"Warning: could not remove {artifact} (file is in use). "
                            "Close Python processes using that module and rerun compilation."
                        )
                    except FileNotFoundError:
                        pass

    if copied == 0:
        print("Warning: no extension binaries were deployed to NonagaGame/.")
    print("Cython files compiled successfully.")
