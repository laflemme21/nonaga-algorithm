from game import Game
from menu import Menu
from nonaga_constants import SCREEN_HEIGHT, SCREEN_WIDTH

def main():
    """Main entry point for the game."""
    while True:
        # Show menu and get player choice
        menu = Menu(SCREEN_WIDTH, SCREEN_HEIGHT)
        result = menu.run()
        
        if result == "quit":
            break
        elif result == "start":
            # Start the game
            game = Game(SCREEN_WIDTH, SCREEN_HEIGHT)
            game.run()

if __name__ == "__main__":
    main()
