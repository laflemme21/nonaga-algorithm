# cython: language_level=3
from nonaga_bitboard cimport NonagaBitBoard
from nonaga_logic cimport NonagaLogic

cdef extern from "AI_core.h":
    ctypedef struct Move2D:
        int from_q
        int from_r
        int to_q
        int to_r
        int is_set

    ctypedef struct MissingInfo:
        int missing_count
        int enemy_count

    ctypedef struct MinimaxResult:
        int cost
        Move2D piece_move
        Move2D tile_move

cdef class AI:
    
    cdef public int[8] parameter
    cdef public int depth
    cdef public int max_color
    cdef public int min_color
    cdef public int depth_0_color

    cdef MinimaxResult minimax_piece(self, NonagaLogic game_state, int depth, bint maximizingPlayer, int color, int alpha, int beta)
    cdef MinimaxResult minimax_tile(self, NonagaLogic game_state, int depth, bint maximizingPlayer, int color, int alpha, int beta)
    cdef int cost_function(self, NonagaLogic game_state, bint maximizingPlayer, int color, int[8] params)
    cdef MissingInfo missing_tiles_and_enemy_pieces(self, NonagaBitBoard* board, int p0q, int p0r, int p0s, int p1q, int p1r, int p1s, int p2q, int p2r, int p2s, int color)
    cdef int distance_to(self, int q1, int r1, int s1, int q2, int r2, int s2)
    cpdef tuple get_best_move(self, game_state)
