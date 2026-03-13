# cython: language_level=3

cdef class NonagaBitBoard:
    cdef unsigned long long[7] red_pieces, black_pieces, movable_tiles, unmovable_tiles

    cdef tuple _initialize_board(self)

    cdef inline void _set_bit(self, unsigned long long *board, int q, int r)
    cdef inline void _clear_bit(self, unsigned long long *board, int q, int r)
    cdef inline void _set_bit_flat(self, unsigned long long *board, int flat_index)
    cdef inline bint _check_bit_flat(self, unsigned long long *board, int flat_index)
    cdef inline void _recover_coords(self, int flat_index, int* q, int* r, int* s)
    cdef inline bint _check_bit(self, unsigned long long *board, int q, int r)

    cdef int get_number_of_tiles(self)
    cdef set get_all_tiles(self)
    cdef set get_movable_tiles(self)
    cdef int distance_to(self, c1,c2)

    cdef update_tiles(self)

    cdef bint is_there_tile(self, position)
    cdef bint has_tile(self, int q, int r)
    cdef bint is_there_piece(self, position)
    cdef int get_color(self, int q, int r)
    cdef get_pieces(self, color=*)

    cdef bint _neighbors_are_connected(self, int[6] p, int count)

    cpdef void move_tile(self, tuple current_pos, tuple new_pos)
    cpdef void move_piece(self, tuple current_pos, tuple new_pos)
