from game import Game
from menu import Menu

def main():
    """Main entry point for the game."""
    while True:
        # Show menu and get player choice
        menu = Menu()
        result = menu.run()
        
        if result == "quit":
            break
        elif result == "start":
            # Start the game
            game = Game()
            game.run()

if __name__ == "__main__":
    main()
