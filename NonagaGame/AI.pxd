# cython: language_level=3
from nonaga_bitboard cimport NonagaBitBoard
cdef struct Move:
    int cost
    int* pos
    int* dest

cdef class AI:
    
    cdef public int[8] parameter
    cdef public int depth
    cdef public int max_color
    cdef public int min_color
    cdef public int depth_0_color

    cdef Move minimax_piece(self, game_state, int depth, bint maximizingPlayer, int color, double alpha, double beta)
    cdef void* minimax_tile(self, game_state, int depth, bint maximizingPlayer, int color, double alpha, double beta)
    cdef int cost_function(self, game_state, bint maximizingPlayer, int color, int[8] params)
    cdef int* missing_tiles_and_enemy_pieces(self, NonagaBitBoard board, int[2] p0, int[2] p1, int[2] p2, int color)
    cdef int distance_to(self, int[3] c1, int[3] c2)
    cpdef tuple get_best_move(self, game_state)
