from nonaga_constants import RED, BLACK, PIECE_TO_MOVE, TILE_TO_MOVE

from nonaga_board import NonagaBoard, NonagaIsland, NonagaPiece, NonagaTile


class NonagaLogic:
    """Manages the game logic for Nonaga."""

    __slots__ = ['player_red', 'player_black', 'board', 'current_player', 'turn_phase']
    def __init__(self, player_red=None, player_black=None, new_game:bool = True):
        """Initialize the game logic.

        Args:
            player_red: Player 1 - can be None for human or a callable for AI.
            player_black: Player 2 - can be None for human or a callable for AI.
        """

        # Players
        self.player_red = player_red
        self.player_black = player_black

        # Board
        self.board = NonagaBoard(new_game=new_game)

        # Current player ("red" or "black")
        self.current_player = RED
        
        self.turn_phase = PIECE_TO_MOVE
        
    def clone(self)-> "NonagaLogic":
        """Return a fast deep clone with identical attributes."""
        cloned = NonagaLogic(self.player_red, self.player_black, new_game=False)
        cloned.board = self.board.clone()
        cloned.current_player = self.current_player
        cloned.turn_phase = self.turn_phase
        return cloned

    def get_board_state(self):
        """Get the current board state for display."""
        return self.board.get_state()

    def is_ai_player(self, player_color):
        """Check if a player is controlled by AI.

        Args:
            player_color: "red" or "black"
        Returns:
            True if the player is AI (callable), False if human.
        """
        player = self.player_red if player_color == 1 else self.player_black
        return callable(player)

    def get_all_valid_tile_moves_ai(self) -> dict[NonagaTile, list[tuple[int, int, int]]]:
        """Get valid moves for a specific tile. (used by the AI)

        Args:
            tile: NonagaTile object
        Returns:
            List of valid positions for all tiles.
        """
        island = self.board.islands[0]
        move = {}
        for tile in island.get_movable_tiles():
            move[tile] = self._get_valid_tile_positions(tile, island)
        return move

    
    def get_all_valid_tile_moves(self)-> dict[tuple[int, int, int], list[tuple[int, int, int]]]:
        """Get valid moves for a specific tile. (used by the UI)

        Args:
            tile: NonagaTile object
        Returns:
            List of valid positions for all tiles.
        """
        island = self.board.islands[0]
        move = {}
        for tile in island.get_movable_tiles():
            move[tile.get_position()] = self._get_valid_tile_positions(tile, island)
        return move 

    def _get_valid_tile_positions(self, tile: NonagaTile, island: NonagaIsland):
        """Get valid moves for a specific tile.

        Args:
            tile: NonagaTile object
        Returns:
            List of valid positions for the tile.
        """

        """
        multiple things matter here
        1- is there a piece on the tile
        2- is the tile movable
        3- where can the tile move
        """

        tile_coords_set = island._get_tile_coords_set()
        tile_position = tile.get_position()
        if tile_position not in tile_coords_set:
            return set([])
        tile_coords_set.remove(tile_position)
        neighbor_offsets = island._NEIGHBOR_OFFSETS

        candidate_positions = set()
        for existing_pos in tile_coords_set:
            for offset in neighbor_offsets:
                candidate_positions.add(
                    (
                        existing_pos[0] + offset[0],
                        existing_pos[1] + offset[1],
                        existing_pos[2] + offset[2],
                    )
                )

        candidate_positions.difference_update(tile_coords_set)

        valid_positions = set([])
        for candidate in candidate_positions:
            neighbor_positions = []
            for offset in neighbor_offsets:
                neighbor_pos = (
                    candidate[0] + offset[0],
                    candidate[1] + offset[1],
                    candidate[2] + offset[2],
                )
                if neighbor_pos in tile_coords_set:
                    neighbor_positions.append(neighbor_pos)

            neighbor_count = len(neighbor_positions)

            if 2 <= neighbor_count <= 4:
                if neighbor_count <= 2 or island._neighbors_restrain_piece(neighbor_positions):
                    valid_positions.add(candidate)
        if tile.get_position() in valid_positions:
            valid_positions.remove(tile.get_position())
        return valid_positions

    def get_all_valid_piece_moves_ai(self)-> dict[NonagaPiece, list[tuple[int, int, int]]]:
        """Get valid moves for a specific piece. (Used by the AI)

        Args:
            piece: NonagaPiece object
        Returns:
            List of valid positions for the piece.
        """
        moves = {}
        for piece in self.board.get_pieces():
            if piece.color == self.get_current_player():
                island: NonagaIsland = self.board.islands[piece.island_id]
                moves[piece] = []
                for dimension in range(3):
                    for direction in [-1, 1]:
                        valid_move = self._get_valid_piece_moves_in_direction(
                            piece, island, dimension, direction)
                        if valid_move:
                            moves[piece].append(valid_move)
        return moves

    def get_all_valid_piece_moves(self)-> dict[tuple[int, int, int], list[tuple[int, int, int]]]:
        """Get valid moves for a specific piece. (Used by the UI)

        Args:
            piece: NonagaPiece object
        Returns:
            List of valid positions for the piece.
        """
        """
        Another phrasing for the problem we are trying to solve is:
        Given 
        a list of three numbers x,y,z and 
        a list containing multiple lists of three numbers,
        
        Find 3 lists of three numbers a,b,c from the second list
        such that respectively
        a=x or y=b or z=c and
        c   or a   or b are minimum
        
        and three other lists where the same conditions hold but
        c or a or b are maximum.
        
        This should give us the closest available tile in each of the six directions
        """
        moves = {}
        for piece in self.board.get_pieces():
            island: NonagaIsland = self.board.islands[piece.island_id]
            moves[piece.get_position()] = []
            for dimension in range(3):
                for direction in [-1, 1]:
                    valid_move = self._get_valid_piece_moves_in_direction(
                        piece, island, dimension, direction)
                    if valid_move:
                        moves[piece.get_position()].append(valid_move)
        return moves

    def _get_valid_piece_moves_in_direction(self, piece: NonagaPiece, island: NonagaIsland, dimension: int, direction: int):
        destination = None
        # iterate through one dimension in the specified direction
        for i in range(piece.get_position()[dimension]+direction, direction*island.get_number_of_tiles(), direction):

            # calculate the tile coordinates in the current dimension respecting the hexagonal coordinate system
            tile_coords_list = list(piece.get_position())
            tile_coords_list[dimension] = i
            fixed_index = (dimension + 1) % 3
            dependent_index = (dimension + 2) % 3
            tile_coords_list[dependent_index] = - \
                (tile_coords_list[dimension] + tile_coords_list[fixed_index])

            tile = tuple(tile_coords_list)
            if tile in island.pieces:
                break
            elif tile in island.get_all_tiles():
                destination = tile
            else:

                break
        return destination

    def move_tile(self, tile: NonagaTile, destination: tuple[int, int, int]):
        """Execute a tile move."""
        if self.turn_phase == TILE_TO_MOVE:
            self.board.move_tile(tile, destination)
            self._next_turn_phase()
        else:
            raise ValueError("Invalid move: It's not the tile move phase.")

    def move_piece(self, piece: NonagaPiece, destination: tuple[int, int, int]):
        """Execute a piece move."""
        if self.turn_phase == PIECE_TO_MOVE and self.get_current_player() == piece.color:
            self.board.move_piece(piece, destination)
            self._next_turn_phase()
        else:
            raise ValueError("Invalid move: It's either not the piece move phase or the piece does not belong to the current player.")

    def move_tile_ai(self, tile: NonagaTile, destination: tuple[int, int, int]):
        """Execute a tile move."""
        new_self = self.clone()
        tile = new_self.board.get_tile(tile.get_position())  # Ensure we are moving the correct tile object in the cloned board
        if new_self.turn_phase == TILE_TO_MOVE:
            new_self.board.move_tile(tile, destination)
            new_self._next_turn_phase()
        else:
            raise ValueError("Invalid move: It's not the tile move phase.")
        return new_self

    def move_piece_ai(self, piece: NonagaPiece, destination: tuple[int, int, int]):
        """Execute a piece move."""
        new_self = self.clone()
        piece = new_self.board.get_piece(piece.get_position())  # Ensure we are moving the correct piece object in the cloned board
        if new_self.turn_phase == PIECE_TO_MOVE and new_self.get_current_player() == piece.color:
            new_self.board.move_piece(piece, destination)
            new_self._next_turn_phase()
        else:
            raise ValueError("Invalid move: It's either not the piece move phase or the piece does not belong to the current player.")
        return new_self

    def _next_turn_phase(self):
        """Advance to the next turn phase."""
        if self.turn_phase == PIECE_TO_MOVE:
            self.turn_phase = TILE_TO_MOVE
        else:
            self.turn_phase = PIECE_TO_MOVE
            self.switch_player()
            
    def get_current_turn_phase(self):
        """Get the current turn phase."""
        return self.turn_phase
    
    def check_win_condition(self, color: int):
        """Check if the three pieces of a player are connected"""
        if color == RED:
            pieces = self.board.get_pieces(RED)
        else:
            pieces = self.board.get_pieces(BLACK)

        pieces = [piece.get_position() for piece in pieces]
        
        start = pieces[0]
        visited = {start}
        queue = [start]

        neighbor_offsets = ((1, -1, 0),
        (1, 0, -1),
        (0, 1, -1),
        (-1, 1, 0),
        (-1, 0, 1),
        (0, -1, 1))

        while queue:
            curr = queue.pop(0)
            for offset in neighbor_offsets:
                adj_pos = (
                    curr[0] + offset[0],
                    curr[1] + offset[1],
                    curr[2] + offset[2]
                )
                if adj_pos in pieces and adj_pos not in visited:
                    visited.add(adj_pos)
                    queue.append(adj_pos)
        

        return len(visited) == len(pieces)

    def get_current_player(self):
        """Get the current player."""
        return self.current_player

    def switch_player(self):
        """Switch to the next player."""
        if self.current_player == RED:
            self.current_player = BLACK
        else:
            self.current_player = RED
