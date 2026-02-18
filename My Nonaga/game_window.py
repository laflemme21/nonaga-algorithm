import pygame
import math
from nonaga_constants import *
from nonaga_board import NonagaBoard, NonagaPiece, NonagaTile
from nonaga_logic import NonagaLogic


class Game:
    """Manages the PyGame game loop and rendering."""

    def __init__(self, screen_width=800, screen_height=500):
        """Initialize the game."""
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.screen = None
        self.clock = None
        self.running = False
        self.fps = 60

        self.title = "Red to play"
        self.game_logic = NonagaLogic()

        self.hovered_piece: NonagaPiece = None
        self.hovered_tile: NonagaTile = None
        self.hovered_tile_move_pos: tuple[int, int, int] = None

        self.last_clicked_piece: NonagaPiece = None
        self.last_clicked_tile: NonagaTile = None
        self.tile_move_to: tuple[int, int, int] = None

        self.piece_moving: NonagaPiece = None
        self.tile_moving: NonagaTile = None

        self.last_clicked_piece_moves = []
        self.last_clicked_tile_moves = []

        self.board_center_x = None
        self.board_center_y = None

    def setup(self):
        """Set up the game window and resources."""
        pygame.init()
        self.screen = pygame.display.set_mode(
            (self.screen_width, self.screen_height), pygame.RESIZABLE)
        pygame.display.set_caption("Nonaga")
        self.clock = pygame.time.Clock()

    def run(self):
        """Main game loop."""
        self.setup()
        self.running = True

        while self.running:
            self.render_frame()
            self.update_game_state()
            # debug
            # last = ( list(self.game_logic.board.islands[0].pieces))
            # if last != ( list(self.game_logic.board.islands[0].pieces)):
            #     print(list(self.game_logic.board.islands[0].pieces)[0], '1')
            self.update_moves()
            # if last != ( list(self.game_logic.board.islands[0].pieces)):
            #     print(list(self.game_logic.board.islands[0].pieces)[0],'2')
            self.handle_events()
            # if last != ( list(self.game_logic.board.islands[0].pieces)):
            #     print(list(self.game_logic.board.islands[0].pieces)[0],'3')

            self.handle_moves()
            # if last != ( list(self.game_logic.board.islands[0].pieces)):
            #     print(list(self.game_logic.board.islands[0].pieces)[0], '4')
            # print('-----')
        self.running = True

        while self.running:
            self.render_frame()
            self.handle_events()
            self.clock.tick(self.fps)

    def update_game_state(self):
        """Check if there's a winner, update the title and stop the game if so."""
        if self.game_logic.check_win_condition(RED):
            self.title = "Red won!"
            self.running = False
        elif self.game_logic.check_win_condition(BLACK):
            self.title = "Black won!"
            self.running = False
        else:
            current_player = "Red" if self.game_logic.get_current_player() == RED else "Black"
            phase = "Piece" if self.game_logic.get_current_turn_phase() == PIECE_TO_MOVE else "Tile"
            self.title = f"{current_player} has to move a {phase}"

    def render_frame(self):
        """Clear screen and render game state."""
        self.screen.fill((255, 255, 255))  # Clear screen with white background
        state = self.game_logic.get_board_state()
        self.board_center_x = self.screen.get_width() // 2
        self.board_center_y = self.screen.get_height() // 2
        self.render(self.screen, state["tiles"], state["pieces"], self.last_clicked_tile_moves, self.last_clicked_piece_moves,
                    self.board_center_x, self.board_center_y)
        self._draw_title(self.screen)
        pygame.display.flip()

    def handle_events(self):
        """Handle user input events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
            elif event.type == pygame.MOUSEMOTION:
                # Update hovered piece/tile based on mouse position
                self._handle_mouse_motion(event.pos)
                hovered_piece_pos = self.hovered_piece.get_position() if self.hovered_piece else None
                if self.hovered_piece:
                    hovered_tile_pos = None
                else:
                    hovered_tile_pos = self.hovered_tile.get_position() if self.hovered_tile else None
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button click
                    self.last_clicked_piece = self.hovered_piece
                    self.last_clicked_tile = self.hovered_tile
                    self.tile_move_to = self.hovered_tile_move_pos

    def update_moves(self):
        """Update game state."""
        if self.last_clicked_piece is not None and self.last_clicked_piece.get_color() == self.game_logic.get_current_player() and self.game_logic.get_current_turn_phase() == PIECE_TO_MOVE:
            self.last_clicked_piece_moves = self.game_logic.get_all_valid_piece_moves().get(
                self.last_clicked_piece.get_position(), [])
            self.piece_moving = self.last_clicked_piece
        else:
            self.last_clicked_piece_moves = []
            self.piece_moving = None
        if self.last_clicked_tile is not None and self.game_logic.get_current_turn_phase() == TILE_TO_MOVE:
            self.last_clicked_tile_moves = self.game_logic.get_all_valid_tile_moves().get(
                self.last_clicked_tile.get_position(), [])
            self.tile_moving = self.last_clicked_tile
        else:
            self.last_clicked_tile_moves = []

    def handle_moves(self):
        """Handle move execution based on last clicked piece/tile and valid moves."""

        if self.last_clicked_piece_moves is not [] and self.piece_moving is not None and self.last_clicked_tile is not None and self.last_clicked_tile.get_position() in self.last_clicked_piece_moves:

            self.game_logic.move_piece(
                self.piece_moving, self.last_clicked_tile.get_position())
            # to prevent highlighting possibe tile moves
            self.last_clicked_tile = None
        if self.tile_move_to is not None and self.tile_moving is not None and self.tile_move_to in self.last_clicked_tile_moves:

            self.game_logic.move_tile(self.tile_moving, self.tile_move_to)

    def render(self, screen, tiles, pieces, tile_moves, piece_moves,
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
            self._draw_hexagon(screen, q, r, HEX_COLOR, center_x, center_y)

        # Render circles on top (pieces)
        for piece in pieces:
            q, r, s = piece.get_position()
            # Determine circle color
            piece_color = RED_PIECE_COLOR if piece.get_color(
            ) == RED else BLACK_PIECE_COLOR  # Red or Black
            self._draw_circle(screen, q, r,
                              piece_color, center_x, center_y)

        # Render possible moves for last clicked piece
        color = RED_PIECE_MOVE_COLOR if self.last_clicked_piece is not None and self.last_clicked_piece.get_color(
        ) == RED else BLACK_PIECE_MOVE_COLOR
        for move in piece_moves:
            q, r, s = move
            self._draw_circle(screen, q, r,
                              color, center_x, center_y)

        # Render possible moves for last clicked tile
        for move in tile_moves:
            q, r, s = move
            self._draw_hexagon(
                screen, q, r, HEX_MOVE_COLOR, center_x, center_y)

    def _draw_hexagon(self, screen, q, r, color, center_x, center_y):
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
        pygame.draw.polygon(screen, color, points)
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

    def _handle_mouse_motion(self, mouse_pos):
        """Handle mouse movement and update hovered piece/tile.

        Args:
            mouse_pos: tuple of (x, y) mouse position
        """
        state = self.game_logic.get_board_state()
        mx, my = mouse_pos

        # Reset hovered piece first
        self.hovered_piece = None

        # Reset hovered tile
        self.hovered_tile = None
        self.hovered_tile_move_pos = None

        # Check each tile for collision with mouse position
        for tile in state["tiles"]:
            q, r, s = tile.get_position()
            # Convert axial coordinates to pixel coordinates
            x, y = self._axial_to_pixel(
                q, r, self.board_center_x, self.board_center_y)
            # Check if mouse is over this hexagon
            if self._point_in_hexagon(mx, my, x, y, HEX_SIZE):
                # If there's a piece on this tile, prioritize the piece
                if tile in state["pieces"]:
                    self.hovered_piece = state["pieces"][state["pieces"].index(
                        tile)]
                else:
                    self.hovered_tile = tile
                return
        if self.last_clicked_tile_moves is not [] and self.last_clicked_tile is not None:
            for move in self.last_clicked_tile_moves:
                q, r, s = move
                x, y = self._axial_to_pixel(
                    q, r, self.board_center_x, self.board_center_y)
                if self._point_in_hexagon(mx, my, x, y, HEX_SIZE):
                    self.hovered_tile_move_pos = (q, r, s)
                    return


    def _draw_title(self, screen, color=(0, 0, 0)):
        """Draw the title centered at the top of the window."""
        font = pygame.font.Font(None, 32)
        text_surface = font.render(self.title, True, color)
        text_rect = text_surface.get_rect(center=(screen.get_width() // 2, 32))
        screen.blit(text_surface, text_rect)

    def _point_in_circle(self, px, py, cx, cy, radius):
        """Check if a point is inside a circle.

        Args:
            px, py: point coordinates
            cx, cy: circle center coordinates
            radius: circle radius

        Returns:
            True if point is inside the circle
        """
        distance = math.sqrt((px - cx) ** 2 + (py - cy) ** 2)
        return distance <= radius

    def _point_in_hexagon(self, px, py, hx, hy, size):
        """Check if a point is inside a hexagon using distance to edges.

        Args:
            px, py: point coordinates
            hx, hy: hexagon center coordinates
            size: hexagon size (distance from center to vertex)

        Returns:
            True if point is inside the hexagon
        """
        # Translate point to hexagon center
        dx = px - hx
        dy = py - hy

        # For a flat-top hexagon, check if point is within bounds
        # Get the vertices of the hexagon
        vertices = []
        for i in range(6):
            angle = math.pi / 3 * i
            vx = hx + size * math.cos(angle)
            vy = hy + size * math.sin(angle)
            vertices.append((vx, vy))

        # Use cross product method to check if point is inside polygon
        return self._point_in_polygon(px, py, vertices)

    def _point_in_polygon(self, px, py, vertices):
        """Check if a point is inside a polygon using ray casting algorithm.

        Args:
            px, py: point coordinates
            vertices: list of (x, y) tuples representing polygon vertices

        Returns:
            True if point is inside the polygon
        """
        n = len(vertices)
        inside = False

        p1x, p1y = vertices[0]
        for i in range(1, n + 1):
            p2x, p2y = vertices[i % n]
            if py > min(p1y, p2y):
                if py <= max(p1y, p2y):
                    if px <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (py - p1y) * (p2x - p1x) / \
                                (p2y - p1y) + p1x
                        if p1x == p2x or px <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside
