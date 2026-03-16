# cython: language_level=3, boundscheck=False, wraparound=False, Profile = True
from nonaga_bitboard cimport (
    NonagaBitBoard,
    bitboard_initialize,
    bitboard_get_number_of_tiles,
    bitboard_get_all_tiles,
    bitboard_get_movable_tiles,
    bitboard_get_pieces,
    bitboard_is_there_tile,
    bitboard_has_tile,
    bitboard_is_there_piece,
    bitboard_get_color,
    bitboard_move_tile,
    bitboard_move_piece,
)


cdef class NonagaBitBoardWrapper:
    cdef NonagaBitBoard board

    def __cinit__(self):
        bitboard_initialize(&self.board)

    cpdef int get_number_of_tiles(self):
        return bitboard_get_number_of_tiles(&self.board)

    cpdef set get_all_tiles(self):
        cdef int q[448]
        cdef int r[448]
        cdef int s[448]
        cdef int i
        cdef int count = bitboard_get_all_tiles(&self.board, &q[0], &r[0], &s[0], 448)
        cdef set out = set()
        for i in range(count):
            out.add((q[i], r[i], s[i]))
        return out

    cpdef set get_movable_tiles(self):
        cdef int q[448]
        cdef int r[448]
        cdef int s[448]
        cdef int i
        cdef int count = bitboard_get_movable_tiles(&self.board, &q[0], &r[0], &s[0], 448)
        cdef set out = set()
        for i in range(count):
            out.add((q[i], r[i], s[i]))
        return out

    cpdef list get_pieces_py(self, color=None):
        cdef int c = -1
        cdef int q[6]
        cdef int r[6]
        cdef int s[6]
        cdef int i
        cdef int count
        cdef list out = []

        if color is not None:
            c = <int>color

        count = bitboard_get_pieces(&self.board, c, &q[0], &r[0], &s[0])
        for i in range(count):
            out.append((q[i], r[i], s[i]))
        return out

    cpdef bint is_there_tile(self, int q, int r):
        return bitboard_is_there_tile(&self.board, q, r)

    cpdef bint has_tile(self, int q, int r):
        return bitboard_has_tile(&self.board, q, r)

    cpdef bint is_there_piece(self, int q, int r):
        return bitboard_is_there_piece(&self.board, q, r)

    cpdef int get_color(self, int q, int r):
        return bitboard_get_color(&self.board, q, r)

    cpdef void move_tile_py(self, tuple current_pos, tuple new_pos):
        bitboard_move_tile(&self.board, current_pos[0], current_pos[1], new_pos[0], new_pos[1])

    cpdef void move_piece_py(self, tuple current_pos, tuple new_pos):
        bitboard_move_piece(&self.board, current_pos[0], current_pos[1], new_pos[0], new_pos[1])
