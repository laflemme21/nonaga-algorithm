import subprocess
import shutil
import glob
import sys
import os


def compile_cython_files():
    """Compiles the Cython files for improved performance."""
    # setup.py is in the project root (one level up from this file)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nonaga_dir = os.path.join(project_root, "My Nonaga")
    try:
        subprocess.check_call(
            [sys.executable, "setup.py", "build_ext", "--inplace"],
            cwd=project_root,
        )
        # Move .pyd files from project root into My Nonaga/
        for pyd_file in glob.glob(os.path.join(project_root, "*.pyd")):
            dest = os.path.join(nonaga_dir, os.path.basename(pyd_file))
            if os.path.exists(dest):
                os.remove(dest)
            shutil.move(pyd_file, dest)
            print(f"Moved {os.path.basename(pyd_file)} -> My Nonaga/")
        print("Cython files compiled successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error compiling Cython files: {e}")


def game_loop():
    """Main entry point for the game."""
    # Import game modules here, after Cython compilation is done
    from nonaga_board import NonagaBoard, NonagaIsland, NonagaPiece, NonagaTile
    from nonaga_logic import NonagaLogic
    from nonaga_constants import SCREEN_HEIGHT, SCREEN_WIDTH
    from menu_window import Menu
    from game_window import Game

    while True:
        # Show menu and get player choice
        menu = Menu(SCREEN_WIDTH, SCREEN_HEIGHT)
        result = menu.run()
        if result == "quit":
            break
        elif result == "two_player":
            # Start the game
            game = Game(False, SCREEN_WIDTH, SCREEN_HEIGHT)
            game.run()
        elif result == "play_ai":
            # Start the game with AI
            game = Game(True, SCREEN_WIDTH, SCREEN_HEIGHT)
            game.run()


if __name__ == "__main__":
    compile_cython_files()
    game_loop()
