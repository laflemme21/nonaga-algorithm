# RED and BLACK are constants representing the two players.
RED = 0
BLACK = 1

PIECE_TO_MOVE = 0
TILE_TO_MOVE = 1


HEX_SIZE = 50  # Size of each hex tile in pixels
HEX_COLOR = (188, 158, 106)  # Default hex color
HEX_MOVE_COLOR = tuple(
    (h + r) // 2 for h, r in zip(HEX_COLOR, (255,255,255)))


CIRCLE_SIZE = HEX_SIZE * 0.66  # Size of each piece in pixels

RED_PIECE_COLOR = (200, 20, 15)  # Color for RED pieces
RED_PIECE_MOVE_COLOR = tuple((h + r) // 2 for h, r in zip(HEX_COLOR, RED_PIECE_COLOR))  # Highlight color for RED pieces

BLACK_PIECE_COLOR = (20, 30, 30)  # Color for BLACK pieces
BLACK_PIECE_MOVE_COLOR = tuple((h + b) // 2 for h, b in zip(HEX_COLOR, BLACK_PIECE_COLOR))  # Highlight color for BLACK pieces


SCREEN_WIDTH = 800  # Width of the game window
SCREEN_HEIGHT = 500  # Height of the game window