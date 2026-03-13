# cython: language_level=3
from nonaga_bitboard cimport NonagaBitBoard

cdef class NonagaLogic:

    cdef public object player_red, player_black
    cdef public NonagaBitBoard board
    cdef public int current_player
    cdef public int turn_phase

    cpdef object get_board_state(self)
    cdef dict get_all_valid_tile_moves_ai(self)
    cpdef dict get_all_valid_tile_moves(self)
    cdef dict get_all_valid_piece_moves_ai(self)
    cpdef dict get_all_valid_piece_moves(self)
    cdef is_ai_player(self, int player_color)
    
    cdef set _get_valid_tile_positions(self, tuple tile_position)
    cdef tuple _get_valid_piece_moves_in_direction(self, tuple piece_pos, int dimension, int direction)

    cdef void move_tile(self, tuple tile_pos, tuple destination)
    cdef void move_piece(self, tuple piece_pos, tuple destination)
    cdef void undo_tile_move(self, tuple tile_pos, tuple destination)
    cdef void undo_piece_move(self, tuple piece_pos, tuple destination)
    cdef bint _neighbors_restrain_piece(self, list neighbors)

    cdef void _next_turn_phase(self)
    cdef void _last_turn_phase(self)
    cpdef int get_current_turn_phase(self)

    cpdef int get_current_player(self)
    cpdef void switch_player(self)
    cpdef bint check_win_condition(self, int color)


    cpdef bint check_win_condition(self, int color)
    cpdef int get_current_player(self)
    cpdef void switch_player(self)
