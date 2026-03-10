# cython: language_level=3
from nonaga_board cimport NonagaBoard, NonagaIsland, NonagaTile, NonagaPiece

cdef class NonagaLogic:

    cdef public object player_red, player_black
    cdef public NonagaBoard board
    cdef public int current_player
    cdef public int turn_phase

    cpdef NonagaLogic clone(self)
    cpdef object get_board_state(self)
    cdef dict get_all_valid_tile_moves_ai(self)
    cpdef dict get_all_valid_tile_moves(self)
    cdef dict get_all_valid_piece_moves_ai(self)
    cpdef dict get_all_valid_piece_moves(self)
    cdef is_ai_player(self, int player_color)
    cdef set _get_valid_tile_positions(self, NonagaTile tile, NonagaIsland island)

    cdef tuple _get_valid_piece_moves_in_direction(self, NonagaPiece piece, NonagaIsland island,
                                                     int dimension, int direction)

    cpdef void move_tile(self, NonagaTile tile, tuple destination)
    cpdef void move_piece(self, NonagaPiece piece, tuple destination)
    cdef NonagaLogic move_tile_ai(self, NonagaTile tile, tuple destination)
    cdef NonagaLogic move_piece_ai(self, NonagaPiece piece, tuple destination)

    cdef void _next_turn_phase(self)
    cpdef int get_current_turn_phase(self)

    cpdef bint check_win_condition(self, int color)
    cpdef int get_current_player(self)
    cpdef void switch_player(self)
