# cython: language_level=3, boundscheck=False, wraparound=False, profile=True
from nonaga_constants import RED, BLACK

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

    Move2D ai_empty_move()
    MinimaxResult ai_new_result(int cost)
    void ai_init_tt()
    MinimaxResult ai_search_iterative_deepening(NonagaBitBoard* board, int current_player, int turn_phase, int max_depth, int maximizing_player, int color, int max_color, const int* params)

    int ai_cost_function(NonagaBitBoard* board, int maximizing_player, int max_color, const int* params)
    int ai_distance_to(int q1, int r1, int s1, int q2, int r2, int s2)
    MissingInfo ai_missing_tiles_and_enemy_pieces_from_board(NonagaBitBoard* board, int p0q, int p0r, int p0s, int p1q, int p1r, int p1s, int p2q, int p2r, int p2s, int color)


cdef int NEG_INF = -99999999
cdef int POS_INF = 99999999


cdef class AI:
    """Minimax AI with alpha-beta pruning for Nonaga."""

    def __init__(self, parameter, int depth=3, int color=BLACK):
        cdef int i
        self.depth = depth
        self.max_color = color
        self.min_color = (color + 1) % 2
        self.depth_0_color = (color + depth) % 2
        for i in range(8):
            self.parameter[i] = <int>parameter[i]

    cdef MinimaxResult search_iterative_deepening(self, NonagaLogic game_state, int max_depth, bint maximizingPlayer, int color):
        return ai_search_iterative_deepening(&game_state.board, game_state.current_player, game_state.turn_phase, max_depth, 1 if maximizingPlayer else 0, color, self.max_color, &self.parameter[0])

    cdef int cost_function(self, NonagaLogic game_state, bint maximizingPlayer, int color, int[8] params):
        return ai_cost_function(&game_state.board, 1 if maximizingPlayer else 0, color, &params[0])

    cdef int distance_to(self, int q1, int r1, int s1, int q2, int r2, int s2):
        return ai_distance_to(q1, r1, s1, q2, r2, s2)

    cdef MissingInfo missing_tiles_and_enemy_pieces(
        self,
        NonagaBitBoard* board,
        int p0q,
        int p0r,
        int p0s,
        int p1q,
        int p1r,
        int p1s,
        int p2q,
        int p2r,
        int p2s,
        int color,
    ):
        return ai_missing_tiles_and_enemy_pieces_from_board(board, p0q, p0r, p0s, p1q, p1r, p1s, p2q, p2r, p2s, color)

    cdef tuple _get_fallback_move(self, game_state):
        """Return an arbitrary legal (piece_move, tile_move) pair for the current player."""
        cdef object best_piece_move = None
        cdef object best_tile_move = None
        cdef dict piece_moves = game_state.get_all_valid_piece_moves()
        cdef dict tile_moves = game_state.get_all_valid_tile_moves()
        cdef object from_pos
        cdef object destinations
        cdef object to_pos

        if piece_moves is None or tile_moves is None:
            return (None, None)

        for from_pos, destinations in piece_moves.items():
            if destinations:
                to_pos = destinations[0]
                best_piece_move = (
                    (from_pos[0], from_pos[1]),
                    (to_pos[0], to_pos[1]),
                )
                break

        for from_pos, destinations in tile_moves.items():
            if destinations:
                to_pos = next(iter(destinations))
                best_tile_move = (
                    (from_pos[0], from_pos[1]),
                    (to_pos[0], to_pos[1]),
                )
                break

        return (best_piece_move, best_tile_move)

    cpdef tuple get_best_move(self, game_state):
        cdef MinimaxResult result
        cdef tuple fallback_piece_move
        cdef tuple fallback_tile_move
        cdef object best_piece_move = None
        cdef object best_tile_move = None

        ai_init_tt()

        result = self.search_iterative_deepening(
            game_state,
            self.depth,
            True,
            game_state.get_current_player()
        )

        if result.piece_move.is_set:
            best_piece_move = (
                (result.piece_move.from_q, result.piece_move.from_r),
                (result.piece_move.to_q, result.piece_move.to_r),
            )
        if result.tile_move.is_set:
            best_tile_move = (
                (result.tile_move.from_q, result.tile_move.from_r),
                (result.tile_move.to_q, result.tile_move.to_r),
            )

        if best_piece_move is None or best_tile_move is None:
            fallback_piece_move, fallback_tile_move = self._get_fallback_move(game_state)
            if best_piece_move is None:
                best_piece_move = fallback_piece_move
            if best_tile_move is None:
                best_tile_move = fallback_tile_move

        # Keep the no-move outcome explicit and consistent for callers.
        if best_piece_move is None or best_tile_move is None:
            return (None, None)

        return (best_piece_move, best_tile_move)

    def execute_best_move(self, game_state: object):
        cdef object best_piece_move
        cdef object best_tile_move
        best_piece_move, best_tile_move = self.get_best_move(game_state)
        print(best_piece_move, best_tile_move)
        if best_piece_move is not None and best_tile_move is not None:
            game_state.move_piece_py(best_piece_move[0], best_piece_move[1])
            game_state.move_tile_py(best_tile_move[0], best_tile_move[1])
