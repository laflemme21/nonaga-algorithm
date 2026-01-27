import pygame
import math
from nonaga_constants import *
from nonaga_board import NonagaBoard


class Game:
    """Manages the PyGame game loop and rendering."""

    def __init__(self):
        """Initialize the game."""
        self.screen = None
        self.clock = None
        self.running = False
        self.fps = 60
        self.title = "Red to play"
        self.board = NonagaBoard()

    def setup(self):
        """Set up the game window and resources."""
        pygame.init()
        self.screen = pygame.display.set_mode((1200, 800), pygame.RESIZABLE)
        pygame.display.set_caption("Nonaga")
        self.clock = pygame.time.Clock()

    def run(self):
        """Main game loop."""
        self.setup()
        self.running = True

        while self.running:
            self.render_frame()
            self.handle_events()
            self.update()
            self.clock.tick(self.fps)

        self.cleanup()

    def render_frame(self):
        """Clear screen and render game state."""
        self.screen.fill((255, 255, 255))  # Clear screen with white background
        state = self.board.get_state()
        self.render(self.screen, state["tiles"], state["pieces"])
        pygame.display.flip()

    def handle_events(self):
        """Handle user input events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
            # TODO: Handle other events (mouse clicks, etc.)

    def update(self):
        """Update game state."""
        # TODO: Implement game state updates
        pass

    def render(self, screen, tiles, pieces,
               center_x=None, center_y=None):
        """Render hexagons and circles on the board.

        Args:
            screen: pygame surface to render to
            tiles: list of NonagaTile objects to render as hexagons
            pieces: list of NonagaPiece objects to render as circles
            hex_size: size of hexagons and circles (distance from center to vertex)
            center_x: x-coordinate of board center (defaults to screen center)
            center_y: y-coordinate of board center (defaults to screen center)
        """
        # Set default center if not provided
        if center_x is None:
            center_x = screen.get_width() // 2
        if center_y is None:
            center_y = screen.get_height() // 2

        # Render hexagons first (tiles)
        for tile in tiles:
            q, r, s = tile.get_position()
            self._draw_hexagon(screen, q, r, center_x, center_y)

        # Render circles on top (pieces)
        for piece in pieces:
            q, r, s = piece.get_position()
            # Determine circle color
            piece_color = RED_PIECE_COLOR if piece.get_color(
            ) == RED else BLACK_PIECE_COLOR  # Red or Black
            self._draw_circle(screen, q, r,
                              piece_color, center_x, center_y)

    def _draw_hexagon(self, screen, q, r, center_x, center_y):
        """Draw a hexagon at axial coordinates (q, r).

        Args:
            screen: pygame surface to draw on
            q: axial q coordinate
            r: axial r coordinate
            center_x: x-coordinate of board center
            center_y: y-coordinate of board center
        """
        # Convert axial coordinates to pixel coordinates
        x, y = self._axial_to_pixel(q, r, center_x, center_y)
        cx, cy = round(x), round(y)

        # Generate hexagon vertices (flat-top orientation)
        points = []
        for i in range(6):
            angle = math.pi / 3 * i
            px = cx + HEX_SIZE * math.cos(angle)
            py = cy + HEX_SIZE * math.sin(angle)
            points.append((px, py))

        # Draw the hexagon
        pygame.draw.polygon(screen, HEX_COLOR, points)
        pygame.draw.polygon(screen, (0, 0, 0), points, 2)  # Draw border

    def _draw_circle(self, screen, q, r, color, center_x, center_y):
        """Draw a circle at axial coordinates (q, r).

        Args:
            screen: pygame surface to draw on
            q: axial q coordinate
            r: axial r coordinate
            color: RGB tuple for circle color
            center_x: x-coordinate of board center
            center_y: y-coordinate of board center
        """
        # Convert axial coordinates to pixel coordinates
        x, y = self._axial_to_pixel(q, r, center_x, center_y)

        # Draw the circle
        pygame.draw.circle(screen, color, (round(x), round(y)), CIRCLE_SIZE)

    def _axial_to_pixel(self, q, r, center_x, center_y):
        """Convert axial coordinates to pixel coordinates.

        Args:
            q: axial q coordinate
            r: axial r coordinate
            center_x: x-coordinate of board center
            center_y: y-coordinate of board center

        Returns:
            Tuple of (x, y) pixel coordinates
        """
        # For flat-top hexagons, the spacing formula is:
        x = HEX_SIZE * (3/2 * q)
        y = HEX_SIZE * (math.sqrt(3)/2 * q + math.sqrt(3) * r)

        return center_x + x, center_y + y

    def cleanup(self):
        """Clean up resources before exiting."""
        # TODO: Implement cleanup and resource release
        pass
