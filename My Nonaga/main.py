from game_window import Game
from menu_window import Menu
from nonaga_constants import SCREEN_HEIGHT, SCREEN_WIDTH
from nonaga_logic import NonagaLogic
from nonaga_board import NonagaBoard, NonagaIsland, NonagaPiece, NonagaTile

def main():
    """Main entry point for the game."""
    
    while True:
        # Show menu and get player choice
        menu = Menu(SCREEN_WIDTH, SCREEN_HEIGHT)
        result = menu.run()
        if result == "quit":
            break
        elif result == "two_player":
            # Start the game
            game = Game(False,SCREEN_WIDTH, SCREEN_HEIGHT)
            game.run()
        elif result == "play_ai":
            # Start the game with AI
            game = Game(True,SCREEN_WIDTH, SCREEN_HEIGHT)
            game.run()

if __name__ == "__main__":
    main()
