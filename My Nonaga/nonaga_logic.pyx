# cython: language_level=3, boundscheck=False, wraparound=False
from nonaga_constants import RED, BLACK, PIECE_TO_MOVE, TILE_TO_MOVE
from nonaga_board import NonagaBoard, NonagaIsland, NonagaPiece, NonagaTile

# Module-level C neighbor offsets for check_win_condition
cdef int _WIN_OFFSETS[6][3]
_WIN_OFFSETS[0] = [1, -1,  0]
_WIN_OFFSETS[1] = [1,  0, -1]
_WIN_OFFSETS[2] = [0,  1, -1]
_WIN_OFFSETS[3] = [-1, 1,  0]
_WIN_OFFSETS[4] = [-1, 0,  1]
_WIN_OFFSETS[5] = [0, -1,  1]

# Python-visible tuple version for _get_valid_tile_positions
_PY_NEIGHBOR_OFFSETS = (
    (1, -1, 0),
    (1, 0, -1),
    (0, 1, -1),
    (-1, 1, 0),
    (-1, 0, 1),
    (0, -1, 1),
)


cdef class NonagaLogic:
    """Manages the game logic for Nonaga."""

    cdef public object player_red, player_black
    cdef public object board            # NonagaBoard
    cdef public int current_player
    cdef public int turn_phase

    def __init__(self, player_red=None, player_black=None, bint new_game=True):
        self.player_red = player_red
        self.player_black = player_black
        self.board = NonagaBoard(new_game=new_game)
        self.current_player = RED
        self.turn_phase = PIECE_TO_MOVE

    # ── clone ────────────────────────────────────────────
    cpdef NonagaLogic clone(self):
        cdef NonagaLogic c = NonagaLogic.__new__(NonagaLogic)
        c.player_red = self.player_red
        c.player_black = self.player_black
        c.board = self.board.clone()
        c.current_player = self.current_player
        c.turn_phase = self.turn_phase
        return c

    # ── board state ──────────────────────────────────────
    def get_board_state(self):
        return self.board.get_state()

    def is_ai_player(self, int player_color):
        player = self.player_red if player_color == 1 else self.player_black
        return callable(player)

    # ── tile moves ───────────────────────────────────────
    def get_all_valid_tile_moves_ai(self):
        """Get valid tile moves keyed by NonagaTile objects (for the AI)."""
        cdef object island = self.board.islands[0]
        cdef dict move = {}
        for tile in island.get_movable_tiles():
            move[tile] = self._get_valid_tile_positions(tile, island)
        return move

    def get_all_valid_tile_moves(self):
        """Get valid tile moves keyed by position tuples (for the UI)."""
        cdef object island = self.board.islands[0]
        cdef dict move = {}
        for tile in island.get_movable_tiles():
            move[tile.get_position()] = self._get_valid_tile_positions(tile, island)
        return move

    cdef set _get_valid_tile_positions(self, object tile, object island):
        cdef set tile_coords_set = island._get_tile_coords_set()
        cdef tuple tile_position = tile.get_position()

        if tile_position not in tile_coords_set:
            return set()
        tile_coords_set.remove(tile_position)

        cdef tuple neighbor_offsets = _PY_NEIGHBOR_OFFSETS
        cdef set candidate_positions = set()
        cdef tuple existing_pos, offset, candidate, neighbor_pos
        cdef list neighbor_positions
        cdef int neighbor_count

        for existing_pos in tile_coords_set:
            for offset in neighbor_offsets:
                candidate_positions.add((
                    existing_pos[0] + offset[0],
                    existing_pos[1] + offset[1],
                    existing_pos[2] + offset[2],
                ))

        candidate_positions.difference_update(tile_coords_set)

        cdef set valid_positions = set()
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

        valid_positions.discard(tile_position)
        return valid_positions

    # ── piece moves ──────────────────────────────────────
    def get_all_valid_piece_moves_ai(self):
        """Get valid piece moves keyed by NonagaPiece objects (for the AI)."""
        cdef dict moves = {}
        cdef int cur = self.current_player
        cdef object island
        cdef int dimension, direction
        cdef object valid_move

        for piece in self.board.get_pieces():
            if piece.color == cur:
                island = self.board.islands[piece.island_id]
                moves[piece] = []
                for dimension in range(3):
                    for direction in range(-1, 2, 2):   # -1, 1
                        valid_move = self._get_valid_piece_moves_in_direction(
                            piece, island, dimension, direction)
                        if valid_move is not None:
                            moves[piece].append(valid_move)
        return moves

    def get_all_valid_piece_moves(self):
        """Get valid piece moves keyed by position tuples (for the UI)."""
        cdef dict moves = {}
        cdef object island
        cdef int dimension, direction
        cdef object valid_move
        cdef tuple pos

        for piece in self.board.get_pieces():
            island = self.board.islands[piece.island_id]
            pos = piece.get_position()
            moves[pos] = []
            for dimension in range(3):
                for direction in range(-1, 2, 2):
                    valid_move = self._get_valid_piece_moves_in_direction(
                        piece, island, dimension, direction)
                    if valid_move is not None:
                        moves[pos].append(valid_move)
        return moves

    cdef object _get_valid_piece_moves_in_direction(self, object piece, object island,
                                                     int dimension, int direction):
        cdef tuple piece_pos = piece.get_position()
        cdef int num_tiles = island.get_number_of_tiles()
        cdef object destination = None
        cdef int i
        cdef int fixed_index = (dimension + 1) % 3
        cdef int dependent_index = (dimension + 2) % 3
        cdef list tc
        cdef tuple tile
        cdef set all_tiles = island.get_all_tiles()
        cdef set pieces_set = island.pieces

        for i in range(piece_pos[dimension] + direction,
                       direction * num_tiles, direction):
            tc = list(piece_pos)
            tc[dimension] = i
            tc[dependent_index] = -(tc[dimension] + tc[fixed_index])
            tile = tuple(tc)

            if tile in pieces_set:
                break
            elif tile in all_tiles:
                destination = tile
            else:
                break
        return destination

    # ── execute moves ────────────────────────────────────
    def move_tile(self, object tile, tuple destination):
        if self.turn_phase == TILE_TO_MOVE:
            self.board.move_tile(tile, destination)
            self._next_turn_phase()
        else:
            raise ValueError("Invalid move: It's not the tile move phase.")

    def move_piece(self, object piece, tuple destination):
        if self.turn_phase == PIECE_TO_MOVE and self.current_player == piece.color:
            self.board.move_piece(piece, destination)
            self._next_turn_phase()
        else:
            raise ValueError(
                "Invalid move: It's either not the piece move phase "
                "or the piece does not belong to the current player.")

    def move_tile_ai(self, object tile, tuple destination):
        cdef NonagaLogic new_self = self.clone()
        tile = new_self.board.get_tile(tile.get_position())
        if new_self.turn_phase == TILE_TO_MOVE:
            new_self.board.move_tile(tile, destination)
            new_self._next_turn_phase()
        else:
            raise ValueError("Invalid move: It's not the tile move phase.")
        return new_self

    def move_piece_ai(self, object piece, tuple destination):
        cdef NonagaLogic new_self = self.clone()
        piece = new_self.board.get_piece(piece.get_position())
        if new_self.turn_phase == PIECE_TO_MOVE and new_self.current_player == piece.color:
            new_self.board.move_piece(piece, destination)
            new_self._next_turn_phase()
        else:
            raise ValueError(
                "Invalid move: It's either not the piece move phase "
                "or the piece does not belong to the current player.")
        return new_self

    # ── turn management ──────────────────────────────────
    cdef void _next_turn_phase(self):
        if self.turn_phase == PIECE_TO_MOVE:
            self.turn_phase = TILE_TO_MOVE
        else:
            self.turn_phase = PIECE_TO_MOVE
            self.switch_player()

    cpdef int get_current_turn_phase(self):
        return self.turn_phase

    # ── win condition ────────────────────────────────────
    cpdef bint check_win_condition(self, int color):
        """Check if the three pieces of a player are connected."""
        cdef list pieces
        if color == RED:
            pieces = [p.get_position() for p in self.board.get_pieces(RED)]
        else:
            pieces = [p.get_position() for p in self.board.get_pieces(BLACK)]

        cdef set piece_set = set(pieces)
        cdef tuple start = <tuple>pieces[0]
        cdef set visited = {start}
        cdef list queue = [start]
        cdef tuple curr, adj_pos
        cdef int cq, cr, cs, i

        while queue:
            curr = <tuple>queue.pop(0)
            cq = curr[0]; cr = curr[1]; cs = curr[2]
            for i in range(6):
                adj_pos = (cq + _WIN_OFFSETS[i][0],
                           cr + _WIN_OFFSETS[i][1],
                           cs + _WIN_OFFSETS[i][2])
                if adj_pos in piece_set and adj_pos not in visited:
                    visited.add(adj_pos)
                    queue.append(adj_pos)

        return len(visited) == len(pieces)

    # ── player management ────────────────────────────────
    cpdef int get_current_player(self):
        return self.current_player

    cpdef void switch_player(self):
        if self.current_player == RED:
            self.current_player = BLACK
        else:
            self.current_player = RED