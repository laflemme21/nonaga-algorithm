# cython: language_level=3, boundscheck=False, wraparound=False, cdivision=True, profile=True
from nonaga_constants import RED, BLACK, PIECE_TO_MOVE, TILE_TO_MOVE
from nonaga_bitboard cimport (
    NonagaBitBoard,
    bitboard_initialize,
    bitboard_set_board_state,
    bitboard_get_all_tiles,
    bitboard_get_movable_tiles,
    bitboard_get_pieces,
    bitboard_is_there_piece,
    bitboard_is_there_tile,
    bitboard_move_tile,
    bitboard_move_piece,
)

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
        bitboard_initialize(&self.board)
        self.current_player = RED
        self.turn_phase = PIECE_TO_MOVE

    cpdef object get_board_state(self):
        cdef list tiles = []
        cdef list pieces = []
        cdef int q[3]
        cdef int r[3]
        cdef int s[3]
        cdef int count
        cdef int tile_q[448]
        cdef int tile_r[448]
        cdef int tile_s[448]
        cdef int tile_count
        cdef int i
        
        tile_count = bitboard_get_all_tiles(&self.board, &tile_q[0], &tile_r[0], &tile_s[0], 448)
        for i in range(tile_count):
            tiles.append((tile_q[i], tile_r[i], tile_s[i]))
            
        count = bitboard_get_pieces(&self.board, RED, &q[0], &r[0], &s[0])
        for i in range(count):
            pieces.append((q[i], r[i], s[i], RED))

        count = bitboard_get_pieces(&self.board, BLACK, &q[0], &r[0], &s[0])
        for i in range(count):
            pieces.append((q[i], r[i], s[i], BLACK))
        
        return {"tiles": tiles, "pieces": pieces}

    cpdef void load_board_state(self, list tiles, list red_pieces, list black_pieces, int current_player, int turn_phase):
        cdef int tile_q[448]
        cdef int tile_r[448]
        cdef int rq[3]
        cdef int rr[3]
        cdef int bq[3]
        cdef int br[3]
        cdef int i

        for i in range(len(tiles)):
            tile_q[i] = tiles[i][0]
            tile_r[i] = tiles[i][1]

        for i in range(len(red_pieces)):
            rq[i] = red_pieces[i][0]
            rr[i] = red_pieces[i][1]

        for i in range(len(black_pieces)):
            bq[i] = black_pieces[i][0]
            br[i] = black_pieces[i][1]

        bitboard_set_board_state(
            &self.board,
            &tile_q[0], &tile_r[0], len(tiles),
            &rq[0], &rr[0], len(red_pieces),
            &bq[0], &br[0], len(black_pieces)
        )
        self.current_player = current_player
        self.turn_phase = turn_phase

    cdef is_ai_player(self, int player_color):
        player = self.player_red if player_color == 1 else self.player_black
        return callable(player)

    cdef dict get_all_valid_tile_moves_ai(self):
        cdef dict move = {}
        cdef int q[448]
        cdef int r[448]
        cdef int s[448]
        cdef int i
        cdef int count = bitboard_get_movable_tiles(&self.board, &q[0], &r[0], &s[0], 448)
        cdef tuple pos
        for i in range(count):
            pos = (q[i], r[i], s[i])
            move[pos] = self._get_valid_tile_positions(pos)
        return move

    cpdef dict get_all_valid_tile_moves(self):
        cdef dict move = {}
        cdef int q[448]
        cdef int r[448]
        cdef int s[448]
        cdef int i
        cdef int count = bitboard_get_movable_tiles(&self.board, &q[0], &r[0], &s[0], 448)
        cdef tuple pos
        for i in range(count):
            pos = (q[i], r[i], s[i])
            move[pos] = self._get_valid_tile_positions(pos)
        return move

    cdef set _get_valid_tile_positions(self, tuple tile_position):
        cdef int q[448]
        cdef int r[448]
        cdef int s[448]
        cdef int i
        cdef int count = bitboard_get_all_tiles(&self.board, &q[0], &r[0], &s[0], 448)
        cdef set tile_coords_set = set()
        cdef tuple tile_key
        for i in range(count):
            tile_coords_set.add((q[i], r[i]))

        tile_key = (tile_position[0], tile_position[1])
        
        if tile_key not in tile_coords_set:
            return set()

        tile_coords_set.remove(tile_key)

        cdef tuple neighbor_offsets = _PY_NEIGHBOR_OFFSETS
        cdef set candidate_positions = set()
        cdef tuple existing_pos, offset, candidate, neighbor_pos
        cdef list neighbor_positions
        cdef int neighbor_count
        cdef set valid_positions = set()

        for existing_pos in tile_coords_set:
            for offset in neighbor_offsets:
                candidate = (
                    existing_pos[0] + offset[0],
                    existing_pos[1] + offset[1],
                )
                if candidate not in tile_coords_set:
                    candidate_positions.add(candidate)

        for candidate in candidate_positions:
            neighbor_positions = []
            for offset in neighbor_offsets:
                neighbor_pos = (
                    candidate[0] + offset[0],
                    candidate[1] + offset[1],
                )
                if neighbor_pos in tile_coords_set:
                    neighbor_positions.append(neighbor_pos)

            neighbor_count = len(neighbor_positions)
            if 2 <= neighbor_count <= 4:
                if neighbor_count <= 2 or self._neighbors_restrain_piece(neighbor_positions):
                    valid_positions.add((candidate[0], candidate[1], -candidate[0] - candidate[1]))

        valid_positions.discard(tile_position)
        return valid_positions

    cdef bint _neighbors_restrain_piece(self, list neighbors):
        if not neighbors: return False
        cdef set neighbor_set = set(neighbors)
        cdef tuple start = neighbors[0]
        cdef set visited = {start}
        cdef list queue = [start]
        cdef tuple curr, adj_pos
        cdef int cq, cr, i
        cdef int n_neighbors = len(neighbors)

        while queue:
            curr = queue.pop(0)
            cq = curr[0]; cr = curr[1]
            for i in range(6):
                adj_pos = (cq + _WIN_OFFSETS[i][0],
                           cr + _WIN_OFFSETS[i][1])
                if adj_pos in neighbor_set and adj_pos not in visited:
                    visited.add(adj_pos)
                    queue.append(adj_pos)
        
        return len(visited) == n_neighbors

    cdef dict get_all_valid_piece_moves_ai(self):
        cdef dict moves = {}
        cdef int cur = self.current_player
        cdef int q[3]
        cdef int r[3]
        cdef int s[3]
        cdef int piece_count
        cdef int piece_index
        cdef int dimension, direction
        cdef tuple valid_move
        cdef tuple pos

        piece_count = bitboard_get_pieces(&self.board, cur, &q[0], &r[0], &s[0])
        for piece_index in range(piece_count):
            pos = (q[piece_index], r[piece_index], s[piece_index])
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
        cdef int q[3]
        cdef int r[3]
        cdef int s[3]
        cdef int piece_count
        cdef int piece_index
        cdef int dimension, direction
        cdef tuple valid_move
        cdef tuple pos

        piece_count = bitboard_get_pieces(&self.board, cur, &q[0], &r[0], &s[0])
        for piece_index in range(piece_count):
            pos = (q[piece_index], r[piece_index], s[piece_index])
            moves[pos] = []
            for dimension in range(3):
                for direction in range(-1, 2, 2):
                    valid_move = self._get_valid_piece_moves_in_direction(
                        pos, dimension, direction)
                    if valid_move is not None:
                        moves[pos].append(valid_move)
        return moves

    cdef tuple _get_valid_piece_moves_in_direction(self, tuple piece_pos,
                                                   int dimension, int direction):
        cdef int pq = piece_pos[0], pr = piece_pos[1], ps = piece_pos[2]
        cdef tuple destination = None
        cdef int i
        cdef int fixed_index = (dimension + 1) % 3
        cdef int dependent_index = (dimension + 2) % 3
        cdef int[3] coords
        cdef tuple tile
        
        coords[0] = pq
        coords[1] = pr
        coords[2] = ps

        for i in range(coords[dimension] + direction,
                       direction * 100,
                       direction):
            
            coords[dimension] = i
            coords[dependent_index] = -(coords[dimension] + coords[fixed_index])
            tile = (coords[0], coords[1], coords[2])

            if bitboard_is_there_piece(&self.board, tile[0], tile[1]):
                break
            elif bitboard_is_there_tile(&self.board, tile[0], tile[1]):
                destination = tile
            else:
                break
                
            coords[0] = pq
            coords[1] = pr
            coords[2] = ps
            
        return destination

    cdef void move_tile(self, int from_q, int from_r, int to_q, int to_r):
        # Assumes valid turn phase and ownership
        bitboard_move_tile(&self.board, from_q, from_r, to_q, to_r)
        self._next_turn_phase()

    cdef void move_piece(self, int from_q, int from_r, int to_q, int to_r):
        # Assumes valid turn phase and ownership
        bitboard_move_piece(&self.board, from_q, from_r, to_q, to_r)
        self._next_turn_phase()

    cpdef void move_piece_py(self, tuple from_pos, tuple to_pos):
        self.move_piece(from_pos[0], from_pos[1], to_pos[0], to_pos[1])

    cpdef void move_tile_py(self, tuple from_pos, tuple to_pos):
        self.move_tile(from_pos[0], from_pos[1], to_pos[0], to_pos[1])


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

    cdef bint check_win_condition(self, int color):
        cdef int q[3]
        cdef int r[3]
        cdef int s[3]
        cdef int visited[3]
        cdef int queue[3]
        cdef int piece_count
        cdef int head = 0
        cdef int tail = 0
        cdef int visited_count = 0
        cdef int idx, i, j
        cdef int cq, cr
        cdef int adj_q, adj_r

        piece_count = bitboard_get_pieces(&self.board, color, &q[0], &r[0], &s[0])
        if piece_count == 0:
            return False

        for i in range(3):
            visited[i] = 0

        visited[0] = 1
        queue[tail] = 0
        tail += 1
        visited_count = 1

        while head < tail:
            idx = queue[head]
            head += 1
            cq = q[idx]
            cr = r[idx]

            for i in range(6):
                adj_q = cq + _WIN_OFFSETS[i][0]
                adj_r = cr + _WIN_OFFSETS[i][1]
                for j in range(piece_count):
                    if visited[j]:
                        continue
                    if q[j] == adj_q and r[j] == adj_r:
                        visited[j] = 1
                        queue[tail] = j
                        tail += 1
                        visited_count += 1
                        break

        return visited_count == piece_count

    cpdef bint check_win_condition_py(self, int color):
        return self.check_win_condition(color)

    cpdef int get_current_player(self):
        return self.current_player

    cpdef void switch_player(self):
        if self.current_player == RED:
            self.current_player = BLACK
        else:
            self.current_player = RED
