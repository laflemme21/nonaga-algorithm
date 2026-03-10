# cython: language_level=3
from nonaga_logic cimport NonagaLogic
from nonaga_board cimport NonagaBoard, NonagaPiece

cdef class AI:
    
    cdef public object parameter
    cdef public int depth
    cdef public int max_color
    cdef public int min_color
    cdef public int depth_0_color

    cdef tuple minimax_piece(self, NonagaLogic game_state, int depth, bint maximizingPlayer, int color, double alpha, double beta)
    cdef tuple minimax_tile(self, NonagaLogic game_state, int depth, bint maximizingPlayer, int color, double alpha, double beta)
    cdef int cost_function(self, NonagaLogic game_state, bint maximizingPlayer, int color, list params)
    cdef int pieces_aligned(self, NonagaLogic game_state, list pieces, list pieces_pos, int color)
    cdef int pieces_distance(self, NonagaLogic game_state, list pieces, int color)
    cdef tuple missing_tiles_and_enemy_pieces(self, NonagaLogic game_state, list pieces, list pieces_pos, int color)
    cpdef tuple get_best_move(self, NonagaLogic game_state)
