from turtle import color

import pygame
import math
from nonaga_constants import *
from nonaga_logic import NonagaLogic
from AI import AI
import cProfile
import json
import os


class Game:
    """Manages the PyGame game loop and rendering."""

    def __init__(self, ai: bool = False, screen_width=800, screen_height=500):
        """Initialize the game."""
        self.ai_playing: bool = ai
        self.ai = AI(AI_PARAM)
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.screen = None
        self.clock = None
        self.running = False
        self.fps = 60

        self.title = "Red to play"
        self.game_logic: NonagaLogic = NonagaLogic(None, self.ai_playing)

        self.hovered_piece: tuple = None
        self.hovered_tile: tuple = None
        self.hovered_tile_move_pos: tuple[int, int, int] = None

        self.last_clicked_piece: tuple = None
        self.last_clicked_tile: tuple = None
        self.tile_move_to: tuple[int, int, int] = None

        self.piece_moving: tuple = None
        self.tile_moving: tuple = None

        self.last_clicked_piece_moves = []
        self.last_clicked_tile_moves = []

        self.board_center_x = None
        self.board_center_y = None

        self.move_history = []
        self.current_history_index = 0

        self.btn_back_rect = None
        self.btn_fwd_rect = None
        self.btn_current_rect = None
        self.btn_bot_move_rect = None
        self.btn_free_rect = None
        self.btn_save_rect = None
        self.btn_load_rect = None
        self.free_move_mode = False

    def setup(self):
        """Set up the game window and resources."""
        pygame.init()
        self.screen = pygame.display.set_mode(
            (self.screen_width, self.screen_height), pygame.RESIZABLE)
        pygame.display.set_caption("Nonaga")
        self.clock = pygame.time.Clock()

    def _is_game_over(self):
        return self.game_logic.check_win_condition_py(RED) or self.game_logic.check_win_condition_py(BLACK)

    def run(self):
        """Main game loop."""
        self.setup()
        self.running = True

        while self.running:
            self.render_frame()

            winning = self._is_game_over()
            if not winning and self.current_history_index == len(self.move_history):
                self.ai_plays()
                self.update_game_state()
                self.update_moves()
                self.handle_events()
                self.handle_moves()
            else:
                self.last_clicked_piece_moves = []
                self.last_clicked_tile_moves = []
                # Also reset selection when navigating history
                if self.current_history_index != len(self.move_history):
                    self.last_clicked_piece = None
                    self.last_clicked_tile = None
                    self.piece_moving = None
                    self.tile_moving = None

                self.update_game_state()
                self.handle_events()

            self.clock.tick(self.fps)

    def _rebuild_state_from_history(self):
        """Restore board state from the snapshot stored at current_history_index."""
        ai_player = self.ai if self.ai_playing else None
        self.game_logic = NonagaLogic(None, ai_player)
        if self.current_history_index == 0:
            pass  # fresh default board is already correct
        else:
            snap = self.move_history[self.current_history_index - 1]['snapshot']
            tiles = [(t[0], t[1]) for t in snap['tiles']]
            red_pieces = [(p[0], p[1]) for p in snap['pieces'] if p[3] == RED]
            black_pieces = [(p[0], p[1]) for p in snap['pieces'] if p[3] == BLACK]
            self.game_logic.load_board_state(
                tiles, red_pieces, black_pieces,
                snap['current_player'], snap['turn_phase']
            )
        self.update_game_state()
        self.last_clicked_piece = None
        self.last_clicked_tile = None
        self.piece_moving = None
        self.tile_moving = None
        self.last_clicked_piece_moves = []
        self.last_clicked_tile_moves = []

    def _take_snapshot(self):
        """Return a compact snapshot of the current board state."""
        state = self.game_logic.get_board_state()
        return {
            'tiles': list(state['tiles']),
            'pieces': list(state['pieces']),
            'current_player': self.game_logic.get_current_player(),
            'turn_phase': self.game_logic.get_current_turn_phase(),
        }

    def update_game_state(self):
        """Check if there's a winner, update the title and stop the game if so."""
        if self.game_logic.check_win_condition_py(RED):
            self.title = "Red won!"
        elif self.game_logic.check_win_condition_py(BLACK):
            self.title = "Black won!"
        else:
            if getattr(self, 'free_move_mode', False):
                self.title = "Free Move Mode (State Configuration)"
            elif self.current_history_index < len(self.move_history):
                self.title = f"Viewing past move ({self.current_history_index}/{len(self.move_history)})"
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
        self._draw_buttons(self.screen)
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
                hovered_piece_pos = self.hovered_piece if self.hovered_piece else None
                if self.hovered_piece:
                    hovered_tile_pos = None
                else:
                    hovered_tile_pos = self.hovered_tile if self.hovered_tile else None
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button click
                    if self.btn_back_rect and self.btn_back_rect.collidepoint(event.pos):
                        if self.current_history_index > 0:
                            self.current_history_index -= 1
                            self._rebuild_state_from_history()
                        return
                    if self.btn_fwd_rect and self.btn_fwd_rect.collidepoint(event.pos):
                        if self.current_history_index < len(self.move_history):
                            self.current_history_index += 1
                            self._rebuild_state_from_history()
                        return
                    if self.btn_current_rect and self.btn_current_rect.collidepoint(event.pos):
                        if self.current_history_index < len(self.move_history):
                            self.move_history = self.move_history[:self.current_history_index]
                            self._rebuild_state_from_history()

                            # If AI is black, and AI is supposed to move a tile (meaning human mid-turn quit/resume),
                            # rollback the last piece move so AI plays its full piece+tile turn.
                            if self.ai_playing and self.game_logic.get_current_player() == BLACK \
                                    and self.game_logic.get_current_turn_phase() == TILE_TO_MOVE:
                                if len(self.move_history) > 0 and self.move_history[-1]['type'] == 'piece':
                                    self.move_history.pop()
                                    self.current_history_index -= 1
                                    self._rebuild_state_from_history()
                        return
                    if self.btn_bot_move_rect and self.btn_bot_move_rect.collidepoint(event.pos):
                        # Force current player's history pointer to end if we are in past, or ignore
                        if self.current_history_index < len(self.move_history):
                            pass
                        else:
                            # Revert human piece move if they started their turn but didn't finish
                            if self.game_logic.get_current_turn_phase() == TILE_TO_MOVE:
                                if len(self.move_history) > 0 and self.move_history[-1]['type'] == 'piece':
                                    self.move_history.pop()
                                    self.current_history_index -= 1
                                    self._rebuild_state_from_history()
                            # Perform the AI move
                            self._make_bot_move()
                        return
                    if self.btn_free_rect and self.btn_free_rect.collidepoint(event.pos):
                        self.free_move_mode = not getattr(self, 'free_move_mode', False)
                        self.last_clicked_piece = None
                        self.last_clicked_tile = None
                        return
                    if getattr(self, 'btn_red_turn_rect', None) and self.btn_red_turn_rect.collidepoint(event.pos):
                        self.game_logic.current_player = RED
                        self.game_logic.turn_phase = PIECE_TO_MOVE
                        return
                    if getattr(self, 'btn_black_turn_rect', None) and self.btn_black_turn_rect.collidepoint(event.pos):
                        self.game_logic.current_player = BLACK
                        self.game_logic.turn_phase = PIECE_TO_MOVE
                        return
                    if getattr(self, 'btn_save_rect', None) and self.btn_save_rect.collidepoint(event.pos):
                        self._save_board_state()
                        return
                    if getattr(self, 'btn_load_rect', None) and self.btn_load_rect.collidepoint(event.pos):
                        self._load_board_state()
                        return

                    self.last_clicked_piece = self.hovered_piece
                    self.last_clicked_tile = self.hovered_tile
                    self.tile_move_to = self.hovered_tile_move_pos

    def ai_plays(self):

        if self.ai_playing and self.game_logic.get_current_player() == BLACK:
            self._make_bot_move()

    def _make_bot_move(self):
        self.title = "AI is thinking..."
        self.render_frame()

        best_piece_move, best_tile_move = self.ai.get_best_move(
            self.game_logic)

        # Debug output for AI move ===================================
        print("Best piece move:", best_piece_move)
        print("Best tile move:", best_tile_move)
        # end debug

        if best_piece_move is not None and best_tile_move is not None:
            if self.current_history_index < len(self.move_history):
                self.move_history = self.move_history[:self.current_history_index]

            self.game_logic.move_piece_py(
                best_piece_move[0], best_piece_move[1])
            self.move_history.append({'type': 'piece', 'from': best_piece_move[0], 'to': best_piece_move[1], 'snapshot': self._take_snapshot()})
            self.current_history_index += 1

            self.game_logic.move_tile_py(
                best_tile_move[0], best_tile_move[1])
            self.move_history.append({'type': 'tile', 'from': best_tile_move[0], 'to': best_tile_move[1], 'snapshot': self._take_snapshot()})
            self.current_history_index += 1

        self.update_game_state()

    def _save_board_state(self):
        """Save the current board state to a JSON file."""
        state = self.game_logic.get_board_state()
        data = {
            "board": {
                "tiles": list(state["tiles"]),
                "pieces": list(state["pieces"]),
            },
            "current_player": self.game_logic.get_current_player(),
        }
        with open("saved_board.json", "w") as f:
            json.dump(data, f, indent=2)
        print("Board state saved to saved_board.json")

    def _load_board_state(self):
        """Load a board state from saved_board.json."""
        if not os.path.exists("saved_board.json"):
            print("No saved state found.")
            return

        with open("saved_board.json", "r") as f:
            data = json.load(f)

        ai_player = self.ai if self.ai_playing else None
        self.game_logic = NonagaLogic(None, ai_player)
        tiles = [(t[0], t[1]) for t in data.get("board", {}).get("tiles", [])]
        red_pieces = [(p[0], p[1]) for p in data.get("board", {}).get("pieces", []) if p[3] == RED]
        black_pieces = [(p[0], p[1]) for p in data.get("board", {}).get("pieces", []) if p[3] == BLACK]
        current_player = data.get("current_player", RED)

        self.game_logic.load_board_state(tiles, red_pieces, black_pieces, current_player, PIECE_TO_MOVE)
        self.move_history = []
        self.current_history_index = 0
        self.update_game_state()
        print("Board state loaded successfully.")

    def update_moves(self):
        """Update game state."""
        if getattr(self, 'free_move_mode', False):
            state = self.game_logic.get_board_state()
            if self.last_clicked_piece is not None:
                occupied_tiles = set((p[0], p[1], p[2]) for p in state["pieces"])
                self.last_clicked_piece_moves = [(t[0], t[1], t[2]) for t in state["tiles"] if (t[0], t[1], t[2]) not in occupied_tiles]
                self.piece_moving = self.last_clicked_piece
            else:
                self.last_clicked_piece_moves = []
                self.piece_moving = None

            if self.last_clicked_tile is not None:
                tiles = set((t[0], t[1], t[2]) for t in state["tiles"])
                valid_spots = set()
                for t in tiles:
                    for offset in [(1,-1,0), (1,0,-1), (0,1,-1), (-1,1,0), (-1,0,1), (0,-1,1)]:
                        cand = (t[0]+offset[0], t[1]+offset[1], t[2]+offset[2])
                        if cand not in tiles:
                            valid_spots.add(cand)
                self.last_clicked_tile_moves = list(valid_spots)
                self.tile_moving = self.last_clicked_tile
            else:
                self.last_clicked_tile_moves = []
        else:
            if self.last_clicked_piece is not None and self.last_clicked_piece[3] == self.game_logic.get_current_player() and self.game_logic.get_current_turn_phase() == PIECE_TO_MOVE:
                self.last_clicked_piece_moves = self.game_logic.get_all_valid_piece_moves().get(
                    (self.last_clicked_piece[0], self.last_clicked_piece[1], self.last_clicked_piece[2]), [])
                self.piece_moving = self.last_clicked_piece
            else:
                self.last_clicked_piece_moves = []
                self.piece_moving = None
            if self.last_clicked_tile is not None and self.game_logic.get_current_turn_phase() == TILE_TO_MOVE:
                self.last_clicked_tile_moves = self.game_logic.get_all_valid_tile_moves().get(
                    self.last_clicked_tile, [])
                self.tile_moving = self.last_clicked_tile
            else:
                self.last_clicked_tile_moves = []

    def handle_moves(self):
        """Handle move execution based on last clicked piece/tile and valid moves."""

        if self.last_clicked_piece_moves is not [] and self.piece_moving is not None and self.last_clicked_tile is not None and self.last_clicked_tile in self.last_clicked_piece_moves:

            if self.current_history_index < len(self.move_history):
                self.move_history = self.move_history[:self.current_history_index]

            self.game_logic.move_piece_py(
                self.piece_moving, self.last_clicked_tile)
            self.move_history.append({'type': 'piece', 'from': self.piece_moving, 'to': self.last_clicked_tile, 'snapshot': self._take_snapshot()})
            self.current_history_index += 1
            # to prevent highlighting possible tile moves
            self.last_clicked_tile = None
        if self.tile_move_to is not None and self.tile_moving is not None and self.tile_move_to in self.last_clicked_tile_moves:

            if self.current_history_index < len(self.move_history):
                self.move_history = self.move_history[:self.current_history_index]

            self.game_logic.move_tile_py(self.tile_moving, self.tile_move_to)
            self.move_history.append({'type': 'tile', 'from': self.tile_moving, 'to': self.tile_move_to, 'snapshot': self._take_snapshot()})
            self.current_history_index += 1

    def render(self, screen, tiles, pieces, tile_moves, piece_moves,
               center_x=None, center_y=None):
        """Render hexagons and circles on the board.

        Args:
            screen: pygame surface to render to
            tiles: list of tuple objects to render as hexagons
            pieces: list of tuple objects to render as circles
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
            q, r = tile[0], tile[1]
            self._draw_hexagon(screen, q, r, HEX_COLOR, center_x, center_y)

        # Render circles on top (pieces)
        for piece in pieces:
            q, r = piece[0], piece[1]
            # Determine circle color
            # Red or Black
            piece_color = RED_PIECE_COLOR if piece[3] == RED else BLACK_PIECE_COLOR
            self._draw_circle(screen, q, r,
                              piece_color, center_x, center_y)

        # Render possible moves for last clicked piece
        color = RED_PIECE_MOVE_COLOR if self.last_clicked_piece is not None and self.last_clicked_piece[
            3] == RED else BLACK_PIECE_MOVE_COLOR
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
            # Convert axial coordinates to pixel coordinates
            x, y = self._axial_to_pixel(
                tile[0], tile[1], self.board_center_x, self.board_center_y)
            # Check if mouse is over this hexagon
            if self._point_in_hexagon(mx, my, x, y, HEX_SIZE):
                # If there's a piece on this tile, prioritize the piece
                tile_red = (tile[0], tile[1], tile[2], RED)
                tile_black = (tile[0], tile[1], tile[2], BLACK)
                if tile_red in state["pieces"]:
                    self.hovered_piece = state["pieces"][state["pieces"].index(
                        tile_red)]
                elif tile_black in state["pieces"]:
                    self.hovered_piece = state["pieces"][state["pieces"].index(
                        tile_black)]
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

    def _draw_buttons(self, screen):
        """Draw the forward and backward buttons."""
        # Draw "Backward" button
        self.btn_back_rect = pygame.Rect(10, 10, 50, 30)
        color_back = (200, 200, 200) if self.current_history_index > 0 else (240, 240, 240)
        pygame.draw.rect(screen, color_back, self.btn_back_rect)
        pygame.draw.rect(screen, (0, 0, 0), self.btn_back_rect, 2)
        font = pygame.font.Font(None, 24)
        text_back = font.render("<<", True, (0, 0, 0))
        screen.blit(text_back, text_back.get_rect(center=self.btn_back_rect.center))

        # Draw "Forward" button
        self.btn_fwd_rect = pygame.Rect(65, 10, 50, 30)
        color_fwd = (200, 200, 200) if self.current_history_index < len(self.move_history) else (240, 240, 240)
        pygame.draw.rect(screen, color_fwd, self.btn_fwd_rect)
        pygame.draw.rect(screen, (0, 0, 0), self.btn_fwd_rect, 2)
        text_fwd = font.render(">>", True, (0, 0, 0))
        screen.blit(text_fwd, text_fwd.get_rect(center=self.btn_fwd_rect.center))

        # Draw "Play Here" button
        if self.current_history_index < len(self.move_history):
            self.btn_current_rect = pygame.Rect(125, 10, 100, 40)
            pygame.draw.rect(screen, (200, 200, 200), self.btn_current_rect)
            pygame.draw.rect(screen, (0, 0, 0), self.btn_current_rect, 2)
            text_current = font.render("Play Here", True, (0, 0, 0))
            screen.blit(text_current, text_current.get_rect(center=self.btn_current_rect.center))
        else:
            self.btn_current_rect = None

        # Draw "Bot Move" button (only visible in 2 player mode and not viewing history)
        if not self.ai_playing and self.current_history_index == len(self.move_history):
            self.btn_bot_move_rect = pygame.Rect(125, 10, 100, 40)
            pygame.draw.rect(screen, (200, 200, 255), self.btn_bot_move_rect)
            pygame.draw.rect(screen, (0, 0, 0), self.btn_bot_move_rect, 2)
            text_bot = font.render("Bot Move", True, (0, 0, 0))
            screen.blit(text_bot, text_bot.get_rect(center=self.btn_bot_move_rect.center))
            
            # Draw "Free Move" button next to it
            self.btn_free_rect = pygame.Rect(235, 10, 100, 40)
            color_free = (200, 255, 200) if getattr(self, 'free_move_mode', False) else (240, 240, 240)
            pygame.draw.rect(screen, color_free, self.btn_free_rect)
            pygame.draw.rect(screen, (0, 0, 0), self.btn_free_rect, 2)
            text_free = font.render("Free Move", True, (0, 0, 0))
            screen.blit(text_free, text_free.get_rect(center=self.btn_free_rect.center))

            if getattr(self, 'free_move_mode', False):
                # Draw Red Turn
                self.btn_red_turn_rect = pygame.Rect(345, 10, 100, 40)
                color_red = (255, 150, 150) if self.game_logic.get_current_player() == RED else (240, 240, 240)
                pygame.draw.rect(screen, color_red, self.btn_red_turn_rect)
                pygame.draw.rect(screen, (0, 0, 0), self.btn_red_turn_rect, 2)
                text_red = font.render("Red Turn", True, (0, 0, 0))
                screen.blit(text_red, text_red.get_rect(center=self.btn_red_turn_rect.center))

                # Draw Black Turn
                self.btn_black_turn_rect = pygame.Rect(455, 10, 110, 40)
                color_black = (150, 150, 255) if self.game_logic.get_current_player() == BLACK else (240, 240, 240)
                pygame.draw.rect(screen, color_black, self.btn_black_turn_rect)
                pygame.draw.rect(screen, (0, 0, 0), self.btn_black_turn_rect, 2)
                text_black = font.render("Black Turn", True, (0, 0, 0))
                screen.blit(text_black, text_black.get_rect(center=self.btn_black_turn_rect.center))

                # Draw Save
                self.btn_save_rect = pygame.Rect(575, 10, 70, 40)
                pygame.draw.rect(screen, (200, 200, 200), self.btn_save_rect)
                pygame.draw.rect(screen, (0, 0, 0), self.btn_save_rect, 2)
                text_save = font.render("Save", True, (0, 0, 0))
                screen.blit(text_save, text_save.get_rect(center=self.btn_save_rect.center))

                # Draw Load
                self.btn_load_rect = pygame.Rect(655, 10, 70, 40)
                pygame.draw.rect(screen, (200, 200, 200), self.btn_load_rect)
                pygame.draw.rect(screen, (0, 0, 0), self.btn_load_rect, 2)
                text_load = font.render("Load", True, (0, 0, 0))
                screen.blit(text_load, text_load.get_rect(center=self.btn_load_rect.center))

            else:
                self.btn_red_turn_rect = None
                self.btn_black_turn_rect = None
                self.btn_save_rect = None
                self.btn_load_rect = None
        else:
            self.btn_bot_move_rect = None
            self.btn_free_rect = None
            self.btn_red_turn_rect = None
            self.btn_black_turn_rect = None
            self.btn_save_rect = None
            self.btn_load_rect = None

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
