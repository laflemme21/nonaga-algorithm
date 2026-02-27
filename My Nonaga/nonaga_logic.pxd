# cython: language_level=3

cdef class NonagaLogic:

    
    cdef public object player_red, player_black
    cdef public object board            # NonagaBoard
    cdef public int current_player
    cdef public int turn_phase

    cpdef NonagaLogic clone(self)
    cpdef object get_board_state(self)
    cpdef dict get_all_valid_tile_moves_ai(self)
    cpdef dict get_all_valid_tile_moves(self)
    cpdef dict get_all_valid_piece_moves_ai(self)
    cpdef dict get_all_valid_piece_moves(self)
    cdef is_ai_player(self, int player_color)
    cdef set _get_valid_tile_positions(self, object tile, object island)
    
    cdef object _get_valid_piece_moves_in_direction(self, object piece, object island,
                                                     int dimension, int direction)

    cpdef void move_tile(self, object tile, tuple destination)
    cpdef void move_piece(self, object piece, tuple destination)
    cpdef NonagaLogic move_tile_ai(self, object tile, tuple destination)
    cpdef NonagaLogic move_piece_ai(self, object piece, tuple destination)

    cdef void _next_turn_phase(self)
    cpdef int get_current_turn_phase(self)

    cpdef bint check_win_condition(self, int color)
    cpdef int get_current_player(self)
    cpdef void switch_player(self)
