# cython: language_level=3, boundscheck=False, wraparound=False, cdivision=True, profile=True
from nonaga_constants import RED, BLACK, PIECE_TO_MOVE, TILE_TO_MOVE
from nonaga_bitboard cimport NonagaBitBoard
from nonaga_bitboard import NonagaBitBoard

cdef int[6][3] _WIN_OFFSETS
_WIN_OFFSETS[0] = [1, -1,  0]
_WIN_OFFSETS[1] = [1,  0, -1]
_WIN_OFFSETS[2] = [0,  1, -1]
_WIN_OFFSETS[3] = [-1, 1,  0]
_WIN_OFFSETS[4] = [-1, 0,  1]
_WIN_OFFSETS[5] = [0, -1,  1]

_PY_NEIGHBOR_OFFSETS = (
    (1, -1, 0),
    (1, 0, -1),
    (0, 1, -1),
    (-1, 1, 0),
    (-1, 0, 1),
    (0, -1, 1),
)



cdef class NonagaLogic:
    """Manages the game logic for Nonaga using BitBoard."""

    def __init__(self, player_red=None, player_black=None, bint new_game=True):
        self.player_red = player_red
        self.player_black = player_black
        self.board = NonagaBitBoard() # Always new game for now
        self.current_player = RED
        self.turn_phase = PIECE_TO_MOVE

    cpdef object get_board_state(self):
        cdef list tiles = []
        cdef list pieces = []
        cdef int q, r, s
        cdef int* pos
        
        for pos in self.board.get_all_tiles():
            tiles.append(pos)
            
        for pos in self.board.get_pieces(RED):
            q, r, s = pos[0], pos[1], pos[2]
            pieces.append((q, r, s, RED))

        for pos in self.board.get_pieces(BLACK):
            q, r, s = pos[0], pos[1], pos[2]
            pieces.append((q, r, s, BLACK))
        
        return {"tiles": tiles, "pieces": pieces}

    cdef is_ai_player(self, int player_color):
        player = self.player_red if player_color == 1 else self.player_black
        return callable(player)

    cdef dict get_all_valid_tile_moves_ai(self):
        cdef dict move = {}
        cdef int* pos
        for pos in self.board.get_movable_tiles():
            move[pos] = self._get_valid_tile_positions(pos)
        return move

    cpdef dict get_all_valid_tile_moves(self):
        cdef dict move = {}
        cdef int* pos
        for pos in self.board.get_movable_tiles():
            move[pos] = self._get_valid_tile_positions(pos)
        return move

    cdef set _get_valid_tile_positions(self, int* tile_position):
        cdef set tile_coords_set = self.board.get_all_tiles()
        
        if tile_position not in tile_coords_set:
            return set()
        
        tile_coords_set.remove(tile_position)

        cdef int* neighbor_offsets = _PY_NEIGHBOR_OFFSETS
        cdef set candidate_positions = set()
        cdef int* existing_pos, offset, candidate, neighbor_pos
        cdef list neighbor_positions
        cdef int neighbor_count
        cdef set valid_positions = set()

        for existing_pos in tile_coords_set:
            for offset in neighbor_offsets:
                candidate = (
                    existing_pos[0] + offset[0],
                    existing_pos[1] + offset[1],
                    existing_pos[2] + offset[2]
                )
                if candidate not in tile_coords_set:
                    candidate_positions.add(candidate)

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
                if neighbor_count <= 2 or self._neighbors_restrain_piece(neighbor_positions):
                    valid_positions.add(candidate)

        valid_positions.discard(tile_position)
        return valid_positions

    cdef bint _neighbors_restrain_piece(self, list neighbors):
        if not neighbors: return False
        cdef set neighbor_set = set(neighbors)
        cdef int* start = <int*>neighbors[0]
        cdef set visited = {start}
        cdef list queue = [start]
        cdef int* curr, adj_pos
        cdef int cq, cr, cs, i
        cdef int n_neighbors = len(neighbors)

        while queue:
            curr = <int*>queue.pop(0)
            cq = curr[0]; cr = curr[1]; cs = curr[2]
            for i in range(6):
                adj_pos = (cq + _WIN_OFFSETS[i][0],
                           cr + _WIN_OFFSETS[i][1],
                           cs + _WIN_OFFSETS[i][2])
                if adj_pos in neighbor_set and adj_pos not in visited:
                    visited.add(adj_pos)
                    queue.append(adj_pos)
        
        return len(visited) == n_neighbors

    cdef dict get_all_valid_piece_moves_ai(self):
        cdef dict moves = {}
        cdef int cur = self.current_player
        cdef int dimension, direction
        cdef int* valid_move
        cdef int* pos
        
        for pos in self.board.get_pieces(cur):
            moves[pos] = []
            for dimension in range(3):
                for direction in range(-1, 2, 2):
                    valid_move = self._get_valid_piece_moves_in_direction(
                        pos, dimension, direction)
                    if valid_move is not None:
                        moves[pos].append(valid_move)
        return moves

    cpdef dict get_all_valid_piece_moves(self):
        cdef dict moves = {}
        cdef int cur = self.current_player
        cdef int dimension, direction
        cdef int* valid_move
        cdef int* pos

        for pos in self.board.get_pieces(cur):
            moves[pos] = []
            for dimension in range(3):
                for direction in range(-1, 2, 2):
                    valid_move = self._get_valid_piece_moves_in_direction(
                        pos, dimension, direction)
                    if valid_move is not None:
                        moves[pos].append(valid_move)
        return moves

    cdef int* _get_valid_piece_moves_in_direction(self, int* piece_pos,
                                                     int dimension, int direction):
        cdef int pq = piece_pos[0], pr = piece_pos[1], ps = piece_pos[2]
        cdef int* destination = NULL
        cdef int i
        cdef int fixed_index = (dimension + 1) % 3
        cdef int dependent_index = (dimension + 2) % 3
        cdef int[3] coords
        cdef int* tile
        
        coords[0] = pq
        coords[1] = pr
        coords[2] = ps

        for i in range(coords[dimension] + direction,
                       direction * 100,
                       direction):
            
            coords[dimension] = i
            coords[dependent_index] = -(coords[dimension] + coords[fixed_index])
            tile = (coords[0], coords[1], coords[2])

            if self.board.is_there_piece(tile):
                break
            elif self.board.is_there_tile(tile):
                destination = tile
            else:
                break
                
            coords[0] = pq
            coords[1] = pr
            coords[2] = ps
            
        return destination

    cdef void move_tile(self, int* tile_pos, int* destination):
        # Assumes valid turn phase and ownership
        self.board.move_tile(tile_pos, destination)
        self._next_turn_phase()

    cdef void move_piece(self, int* piece_pos, int* destination):
        # Assumes valid turn phase and ownership
        self.board.move_piece(piece_pos, destination)
        self._next_turn_phase()

    cdef void undo_tile_move(self, int* tile_pos, int* destination):
        self.board.move_tile(tile_pos, destination)
        self._last_turn_phase()
    
    cpdef void move_piece_py(self, int* from_pos, int* to_pos):
        self.move_piece(from_pos, to_pos)

    cpdef void move_tile_py(self, int* from_pos, int* to_pos):
        self.move_tile(from_pos, to_pos)

    cdef void undo_piece_move(self, int* piece_pos, int* destination):
        self.board.move_piece(piece_pos, destination)
        self._last_turn_phase()

    cdef void _next_turn_phase(self):
        if self.turn_phase == PIECE_TO_MOVE:
            self.turn_phase = TILE_TO_MOVE
        else:
            self.turn_phase = PIECE_TO_MOVE
            self.switch_player()

    cdef void _last_turn_phase(self):
        if self.turn_phase == PIECE_TO_MOVE:
            self.turn_phase = TILE_TO_MOVE
            self.switch_player()
        else:
            self.turn_phase = PIECE_TO_MOVE

    cpdef int get_current_turn_phase(self):
        return self.turn_phase

    cpdef bint check_win_condition(self, int color):
        cdef list pieces
        pieces = list(self.board.get_pieces(color))

        cdef set piece_set = set(pieces)
        if not pieces: return False
        
        cdef int* start = <int*>pieces[0]
        cdef set visited = {start}
        cdef list queue = [start]
        cdef int* curr, adj_pos
        cdef int cq, cr, cs, i

        while queue:
            curr = <int*>queue.pop(0)
            cq = curr[0]; cr = curr[1]; cs = curr[2]
            for i in range(6):
                adj_pos = (cq + _WIN_OFFSETS[i][0],
                           cr + _WIN_OFFSETS[i][1],
                           cs + _WIN_OFFSETS[i][2])
                if adj_pos in piece_set and adj_pos not in visited:
                    visited.add(adj_pos)
                    queue.append(adj_pos)

        return len(visited) == len(pieces)

    cpdef int get_current_player(self):
        return self.current_player

    cpdef void switch_player(self):
        if self.current_player == RED:
            self.current_player = BLACK
        else:
            self.current_player = RED
