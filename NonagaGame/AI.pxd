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
    cdef tuple missing_tiles_and_enemy_pieces(self, NonagaBoard board, NonagaPiece p0, NonagaPiece p1, NonagaPiece p2, int color)
    cpdef tuple get_best_move(self, NonagaLogic game_state)
