# cython: language_level=3

cdef class AI:
    
    cdef public object parameter
    cdef public int depth

    cdef tuple minimax_piece(self, object game_state, int depth, bint maximizingPlayer, color,double alpha, double beta)
    cdef tuple minimax_tile(self, object game_state, int depth, bint maximizingPlayer, color,double alpha, double beta)
    cdef int cost_function(self, object game_state, bint maximizingPlayer, int color,int param1, int param2, int param3, int param4)
    cdef int pieces_aligned(self, object game_state, int color)
    cdef int pieces_distance(self, object game_state, int color)
    cdef int count_missing_tiles(self, object game_state, int color)
    
    cpdef tuple get_best_move(self, object game_state)
