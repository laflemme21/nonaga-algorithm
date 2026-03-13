# cython: language_level=3, boundscheck=False, wraparound=False, cdivision=True, profile=True
from libc.string cimport memset
from libc.stdlib cimport abs
from nonaga_constants import RED, BLACK

cdef int BOARD_OFFSET = 10
cdef int BOARD_WIDTH = 21
cdef int ARRAY_SIZE = 7
cdef int BITS_PER_LONG = 64

cdef int[6] NEIGHBOR_FLAT_OFFSETS = [-20, 1, 21, 20, -1, -21]

cdef class NonagaBitBoard:
    def __cinit__(self):
        memset(self.red_pieces, 0, sizeof(unsigned long long) * ARRAY_SIZE)
        memset(self.black_pieces, 0, sizeof(unsigned long long) * ARRAY_SIZE)
        memset(self.movable_tiles, 0, sizeof(unsigned long long) * ARRAY_SIZE)
        memset(self.unmovable_tiles, 0, sizeof(unsigned long long) * ARRAY_SIZE)
        self._initialize_board()

    cdef tuple _initialize_board(self):
        cdef int q, r, r_start, r_end
        cdef int radius = 2
        cdef list pieces_coord = [
            (-2,  0, RED),
            (-2,  2, BLACK),
            ( 0,  2, RED),
            ( 2,  0, BLACK),
            ( 2, -2, RED),
            ( 0, -2, BLACK),
        ]
        
        for q in range(-radius, radius + 1):
            r_start = -radius if -q - radius < -radius else -q - radius
            r_end = radius if -q + radius > radius else -q + radius
            for r in range(r_start, r_end + 1):
                self._set_bit(self.movable_tiles, q, r)

        for q, r, color in pieces_coord:
            if color == RED:
                self._set_bit(self.red_pieces, q, r)
            else:
                self._set_bit(self.black_pieces, q, r)

        self.update_tiles()
        return ()

    cdef inline void _set_bit(self, unsigned long long *board, int q, int r):
        cdef int flat_index = (q + BOARD_OFFSET) + (r + BOARD_OFFSET) * BOARD_WIDTH
        if flat_index < 0 or flat_index >= 448: return
        cdef int array_idx = flat_index // BITS_PER_LONG
        cdef int bit_idx = flat_index % BITS_PER_LONG
        board[array_idx] |= (1ULL << bit_idx)

    cdef inline void _clear_bit(self, unsigned long long *board, int q, int r):
        cdef int flat_index = (q + BOARD_OFFSET) + (r + BOARD_OFFSET) * BOARD_WIDTH
        if flat_index < 0 or flat_index >= 448: return
        cdef int array_idx = flat_index // BITS_PER_LONG
        cdef int bit_idx = flat_index % BITS_PER_LONG
        board[array_idx] &= ~(1ULL << bit_idx)
    
    cdef inline void _set_bit_flat(self, unsigned long long *board, int flat_index):
        if flat_index < 0 or flat_index >= 448: return
        cdef int array_idx = flat_index // BITS_PER_LONG
        cdef int bit_idx = flat_index % BITS_PER_LONG
        board[array_idx] |= (1ULL << bit_idx)

    cdef inline bint _check_bit_flat(self, unsigned long long *board, int flat_index):
        if flat_index < 0 or flat_index >= 448: return False
        cdef int array_idx = flat_index // BITS_PER_LONG
        cdef int bit_idx = flat_index % BITS_PER_LONG
        return (board[array_idx] & (1ULL << bit_idx)) != 0

    cdef inline void _recover_coords(self, int flat_index, int* q, int* r, int* s):
        cdef int r_shifted = flat_index // BOARD_WIDTH
        cdef int q_shifted = flat_index % BOARD_WIDTH
        q[0] = q_shifted - BOARD_OFFSET
        r[0] = r_shifted - BOARD_OFFSET
        s[0] = -q[0] - r[0]
    
    cdef inline bint _check_bit(self, unsigned long long *board, int q, int r):
        cdef int flat_index = (q + BOARD_OFFSET) + (r + BOARD_OFFSET) * BOARD_WIDTH
        if flat_index < 0 or flat_index >= 448: return False
        cdef int array_idx = flat_index // BITS_PER_LONG
        cdef int bit_idx = flat_index % BITS_PER_LONG
        return (board[array_idx] & (1ULL << bit_idx)) != 0

    cdef int get_number_of_tiles(self):
        cdef int count = 0
        cdef int i
        cdef unsigned long long val
        for i in range(ARRAY_SIZE):
            val = self.movable_tiles[i] | self.unmovable_tiles[i]
            while val:
                val &= (val - 1)
                count += 1
        return count

    cdef set get_all_tiles(self):
        cdef set tiles = set()
        cdef int i, j
        cdef unsigned long long val
        cdef int q, r, s
        for i in range(ARRAY_SIZE):
            val = self.movable_tiles[i] | self.unmovable_tiles[i]
            if val == 0: continue
            for j in range(BITS_PER_LONG):
                if (val & (1ULL << j)):
                    self._recover_coords(i * 64 + j, &q, &r, &s)
                    tiles.add((q, r, s))
        return tiles

    cdef set get_movable_tiles(self):
        cdef set tiles = set()
        cdef int i, j
        cdef unsigned long long val
        cdef int q, r, s
        for i in range(ARRAY_SIZE):
            val = self.movable_tiles[i]
            if val == 0: continue
            for j in range(BITS_PER_LONG):
                if (val & (1ULL << j)):
                    self._recover_coords(i * 64 + j, &q, &r, &s)
                    tiles.add((q, r, s))
        return tiles

    cdef int distance_to(self, c1, c2):
        cdef int dq = c1[0] - c2[0]
        cdef int dr = c1[1] - c2[1]
        cdef int ds = c1[2] - c2[2]
        return (abs(dq) + abs(dr) + abs(ds)) // 2

    cdef bint is_there_tile(self, position):
        cdef int q = position[0]
        cdef int r = position[1]
        cdef int flat_index = (q + BOARD_OFFSET) + (r + BOARD_OFFSET) * BOARD_WIDTH
        return self._check_bit_flat(self.movable_tiles, flat_index) or \
               self._check_bit_flat(self.unmovable_tiles, flat_index)

    cdef bint is_there_piece(self, position):
        cdef int q = position[0]
        cdef int r = position[1]
        cdef int flat_index = (q + BOARD_OFFSET) + (r + BOARD_OFFSET) * BOARD_WIDTH
        return self._check_bit_flat(self.red_pieces, flat_index) or \
               self._check_bit_flat(self.black_pieces, flat_index)

    cdef int get_color(self, int q, int r):
        cdef int flat_index = (q + BOARD_OFFSET) + (r + BOARD_OFFSET) * BOARD_WIDTH
        if self._check_bit_flat(self.red_pieces, flat_index):
            return RED
        elif self._check_bit_flat(self.black_pieces, flat_index):
            return BLACK
        else:
            return -1
    
    cdef bint has_tile(self, int q, int r):
        cdef int flat_index = (q + BOARD_OFFSET) + (r + BOARD_OFFSET) * BOARD_WIDTH
        return self._check_bit_flat(self.movable_tiles, flat_index) or \
            self._check_bit_flat(self.unmovable_tiles, flat_index)

    cdef get_pieces(self, color=None):
        cdef set pieces = set()
        cdef int i, j
        cdef int q, r, s
        cdef unsigned long long val
        cdef bint get_red = (color == RED or color is None)
        cdef bint get_black = (color == BLACK or color is None)
        
        for i in range(ARRAY_SIZE):
            val = 0
            if get_red: val |= self.red_pieces[i]
            if get_black: val |= self.black_pieces[i]
            
            if val == 0: continue
            for j in range(BITS_PER_LONG):
                if (val & (1ULL << j)):
                    self._recover_coords(i * 64 + j, &q, &r, &s)
                    pieces.add((q, r, s)) 
        return pieces

    cdef update_tiles(self):
        cdef int i, j, k
        cdef unsigned long long all_tiles_mask
        cdef int flat_index
        cdef int[6] neighbors_presence
        cdef int neighbor_count
        cdef int n_idx
        cdef bint is_piece
        
        cdef unsigned long long[7] new_movable
        cdef unsigned long long[7] new_unmovable
        memset(new_movable, 0, sizeof(new_movable))
        memset(new_unmovable, 0, sizeof(new_unmovable))

        for i in range(ARRAY_SIZE):
            all_tiles_mask = self.movable_tiles[i] | self.unmovable_tiles[i]
            if all_tiles_mask == 0: continue
            
            for j in range(BITS_PER_LONG):
                if (all_tiles_mask & (1ULL << j)):
                    flat_index = i * 64 + j
                    
                    is_piece = self._check_bit_flat(self.red_pieces, flat_index) or \
                               self._check_bit_flat(self.black_pieces, flat_index)
                    
                    if is_piece:
                        self._set_bit_flat(new_unmovable, flat_index)
                        continue
                    
                    neighbor_count = 0
                    for k in range(6):
                        n_idx = flat_index + NEIGHBOR_FLAT_OFFSETS[k]
                        if self._check_bit_flat(self.movable_tiles, n_idx) or \
                           self._check_bit_flat(self.unmovable_tiles, n_idx):
                            neighbors_presence[k] = 1
                            neighbor_count += 1
                        else:
                            neighbors_presence[k] = 0

                    if neighbor_count >= 5:
                        self._set_bit_flat(new_unmovable, flat_index)
                    elif neighbor_count <= 2:
                        self._set_bit_flat(new_movable, flat_index)
                    else:
                        if self._neighbors_are_connected(neighbors_presence, neighbor_count):
                             self._set_bit_flat(new_movable, flat_index)
                        else:
                             self._set_bit_flat(new_unmovable, flat_index)

        for i in range(ARRAY_SIZE):
            self.movable_tiles[i] = new_movable[i]
            self.unmovable_tiles[i] = new_unmovable[i]

    cdef bint _neighbors_are_connected(self, int[6] p, int count):
        if count == 0: return True
        cdef int start = -1
        cdef int k
        for k in range(6):
            if p[k]:
                start = k
                break
        
        cdef int visited_count = 0
        cdef int curr = start
        
        while p[curr]:
             visited_count += 1
             curr = (curr + 1) % 6
             if curr == start: break
        
        return visited_count == count

    cpdef void move_tile(self, tuple current_pos, tuple new_pos):
        self._clear_bit(self.movable_tiles, current_pos[0], current_pos[1])
        # We also check unmovable because we don't know for sure where it came from (though it should be movable)
        # Safe to just clear from both since a tile can't be in both.
        self._clear_bit(self.unmovable_tiles, current_pos[0], current_pos[1])
        
        # New tile goes to movable initially? Or does it matter?
        # self.update_tiles() will reassign it properly.
        # But for update_tiles() to see it, it must be in one of the sets.
        # Let's put it in movable.
        self._set_bit(self.movable_tiles, new_pos[0], new_pos[1])

        # Move piece if present
        if self._check_bit(self.red_pieces, current_pos[0], current_pos[1]):
             self._clear_bit(self.red_pieces, current_pos[0], current_pos[1])
             self._set_bit(self.red_pieces, new_pos[0], new_pos[1])
        elif self._check_bit(self.black_pieces, current_pos[0], current_pos[1]):
             self._clear_bit(self.black_pieces, current_pos[0], current_pos[1])
             self._set_bit(self.black_pieces, new_pos[0], new_pos[1])

        self.update_tiles()

    cpdef void move_piece(self, tuple current_pos, tuple new_pos):
        if self._check_bit(self.red_pieces, current_pos[0], current_pos[1]):
             self._clear_bit(self.red_pieces, current_pos[0], current_pos[1])
             self._set_bit(self.red_pieces, new_pos[0], new_pos[1])
        elif self._check_bit(self.black_pieces, current_pos[0], current_pos[1]):
             self._clear_bit(self.black_pieces, current_pos[0], current_pos[1])
             self._set_bit(self.black_pieces, new_pos[0], new_pos[1])
        
        self.update_tiles()
