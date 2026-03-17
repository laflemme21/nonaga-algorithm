#ifndef NONAGA_AI_CORE_H
#define NONAGA_AI_CORE_H

#include "nonaga_bitboard.h"

#ifdef __cplusplus
extern "C"
{
#endif

    typedef struct Move2D
    {
        int from_q;
        int from_r;
        int to_q;
        int to_r;
        int is_set;
    } Move2D;

    typedef struct MissingInfo
    {
        int missing_count;
        int enemy_count;
    } MissingInfo;

    typedef struct MinimaxResult
    {
        int cost;
        Move2D piece_move;
        Move2D tile_move;
    } MinimaxResult;

    Move2D ai_empty_move(void);
    MinimaxResult ai_new_result(int cost);

    MinimaxResult ai_minimax_piece(
        NonagaBitBoard *board,
        int *current_player,
        int *turn_phase,
        int depth,
        int maximizing_player,
        int color,
        int alpha,
        int beta,
        int max_color,
        const int *params);

    MinimaxResult ai_minimax_tile(
        NonagaBitBoard *board,
        int *current_player,
        int *turn_phase,
        int depth,
        int maximizing_player,
        int color,
        int alpha,
        int beta,
        int max_color,
        const int *params);

    MinimaxResult ai_search_iterative_deepening(
        NonagaBitBoard *board,
        int current_player,
        int turn_phase,
        int max_depth,
        int maximizing_player,
        int color,
        int max_color,
        const int *params);

    void ai_init_tt(void);

    int ai_cost_function(
        NonagaBitBoard *board,
        int maximizing_player,
        int max_color,
        const int *params);

    int ai_distance_to(int q1, int r1, int s1, int q2, int r2, int s2);

    MissingInfo ai_missing_tiles_and_enemy_pieces_from_board(
        NonagaBitBoard *board,
        int p0q,
        int p0r,
        int p0s,
        int p1q,
        int p1r,
        int p1s,
        int p2q,
        int p2r,
        int p2s,
        int color);

#ifdef __cplusplus
}
#endif

#endif
