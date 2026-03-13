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
    
    cdef set _get_valid_tile_positions(self, int* tile_position)
    cdef int* _get_valid_piece_moves_in_direction(self, int* piece_pos, int dimension, int direction)

    cdef void move_tile(self, int* tile_pos, int* destination)
    cdef void move_piece(self, int* piece_pos, int* destination)
    cpdef void move_piece_py(self, int* from_pos, int* to_pos)
    cpdef void move_tile_py(self, int* from_pos, int* to_pos)
    cdef void undo_tile_move(self, int* tile_pos, int* destination)
    cdef void undo_piece_move(self, int* piece_pos, int* destination)
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
