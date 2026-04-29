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

    ctypedef struct AiSearchCounters:
        unsigned long long evaluated_nodes
        unsigned long long leaf_nodes
        unsigned long long tt_probes
        unsigned long long tt_hits
        unsigned long long tt_exact_hits
        unsigned long long tt_lower_hits
        unsigned long long tt_upper_hits
        unsigned long long tt_cached_move_first_tries
        unsigned long long tt_cached_move_first_cutoffs
        unsigned long long piece_candidates_generated
        unsigned long long tile_candidates_generated
        unsigned long long piece_candidates_evaluated
        unsigned long long tile_candidates_evaluated

    void ai_init_tt()
    void ai_reset_search_counters()
    AiSearchCounters ai_get_search_counters()
    MinimaxResult ai_search_iterative_deepening(NonagaBitBoard* board, int current_player, int turn_phase, int max_depth, int maximizing_player, int color, int max_color, const int* params)

cdef class AI:
    
    cdef public int[8] parameter
    cdef public int depth
    cdef public int max_color
    cdef public int min_color
    cdef public int depth_0_color

    cdef MinimaxResult search_iterative_deepening(self, NonagaLogic game_state, int max_depth, bint maximizingPlayer, int color)
    cdef int cost_function(self, NonagaLogic game_state, bint maximizingPlayer, int color, int[8] params)
    cdef MissingInfo missing_tiles_and_enemy_pieces(self, NonagaBitBoard* board, int p0q, int p0r, int p0s, int p1q, int p1r, int p1s, int p2q, int p2r, int p2s, int color)
    cdef int distance_to(self, int q1, int r1, int s1, int q2, int r2, int s2)
    cdef tuple _get_fallback_move(self, game_state)
    cdef bint _is_move_pair_legal(self, NonagaLogic game_state, object piece_move, object tile_move)
    cpdef tuple get_best_move(self, game_state)
    cpdef void reset_search_counters(self)
    cpdef dict get_search_counters(self)
    cpdef unsigned long long count_total_nodes(self, game_state)
