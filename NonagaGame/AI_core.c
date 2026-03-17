#include "AI_core.h"
#include <stdio.h>

#define RED 0
#define BLACK 1
#define PIECE_TO_MOVE 0
#define TILE_TO_MOVE 1
#define NEG_INF (-99999999)
#define POS_INF 99999999
#define MAX_TILES 448
#define MAX_TILE_CANDIDATES 2688
#define AI_BOARD_OFFSET 10
#define AI_BOARD_WIDTH 21
#define AI_BOARD_BITS 448
#define AI_BITS_PER_LONG 64
#define AI_BITS_PER_LONG_SHIFT 6
#define AI_BITS_PER_LONG_MASK (AI_BITS_PER_LONG - 1)
#define AI_BITS_PER_LONG_MASK (AI_BITS_PER_LONG - 1)
#define AI_COORDSET_WORDS 7

#define TT_SIZE 1048576 /* 2^20 */
#define TT_EXACT 0
#define TT_LOWER 1
#define TT_UPPER 2

typedef struct {
    unsigned long long hash;
    int depth;
    int flag;
    int value;
    Move2D best_piece_move;
    Move2D best_tile_move;
} TTEntry;

static TTEntry ai_tt[TT_SIZE];
static unsigned long long Z_RED[AI_BOARD_BITS];
static unsigned long long Z_BLACK[AI_BOARD_BITS];
static unsigned long long Z_TILE[AI_BOARD_BITS];
static unsigned long long Z_TURN_PHASE[2];
static unsigned long long Z_CURRENT_PLAYER[2];
static int ai_tt_initialized = 0;

/* Simple pseudo-random generator for Zobrist keys */
static unsigned long long ai_rand64(void)
{
    static unsigned long long seed = 0x123456789ABCDEF0ULL;
    seed ^= seed >> 12;
    seed ^= seed << 25;
    seed ^= seed >> 27;
    return seed * 2685821657736338717ULL;
}

void ai_init_tt(void)
{
    int i;
    int len = sizeof(ai_tt) / sizeof(ai_tt[0]);
    
    for (i = 0; i < len; i++) {
        ai_tt[i].hash = 0;
        ai_tt[i].depth = -1;
        ai_tt[i].flag = 0;
        ai_tt[i].value = 0;
        ai_tt[i].best_piece_move.is_set = 0;
        ai_tt[i].best_tile_move.is_set = 0;
    }

    if (!ai_tt_initialized) {
        for (i = 0; i < AI_BOARD_BITS; ++i) {
            Z_RED[i] = ai_rand64();
            Z_BLACK[i] = ai_rand64();
            Z_TILE[i] = ai_rand64();
        }
        Z_TURN_PHASE[0] = ai_rand64();
        Z_TURN_PHASE[1] = ai_rand64();
        Z_CURRENT_PLAYER[0] = ai_rand64();
        Z_CURRENT_PLAYER[1] = ai_rand64();
        ai_tt_initialized = 1;
    }
}

static unsigned long long ai_compute_hash(const NonagaBitBoard *board, int current_player, int turn_phase)
{
    unsigned long long h = 0;
    int w, b;
    
    for (w = 0; w < 7; ++w) {
        unsigned long long rp = board->red_pieces[w];
        unsigned long long bp = board->black_pieces[w];
        unsigned long long tl = board->all_tiles[w];
        for (b = 0; b < 64; ++b) {
            int flat = w * 64 + b;
            if (flat >= AI_BOARD_BITS) break;
            if ((rp >> b) & 1ULL) h ^= Z_RED[flat];
            if ((bp >> b) & 1ULL) h ^= Z_BLACK[flat];
            if ((tl >> b) & 1ULL) h ^= Z_TILE[flat];
        }
    }
    
    h ^= Z_CURRENT_PLAYER[current_player & 1];
    h ^= Z_TURN_PHASE[turn_phase & 1];
    
    return h;
}

static const int WIN_OFFSETS[6][3] = {
    {1, -1, 0},
    {1, 0, -1},
    {0, 1, -1},
    {-1, 1, 0},
    {-1, 0, 1},
    {0, -1, 1},
};

static int ai_abs(int v)
{
    return (v < 0) ? -v : v;
}

static int ai_has_tile_flat(const NonagaBitBoard *board, int flat)
{
    if ((unsigned int)flat >= AI_BOARD_BITS)
    {
        return 0;
    }
    return (board->all_tiles[(unsigned int)flat >> AI_BITS_PER_LONG_SHIFT] >> (flat & AI_BITS_PER_LONG_MASK)) & 1ULL;
}

static int ai_enemy_piece_flat(const unsigned long long *enemy_bits, int flat)
{
    if (flat < 0 || flat >= AI_BOARD_BITS)
    {
        return 0;
    }
    return enemy_bits[(unsigned int)flat >> AI_BITS_PER_LONG_SHIFT] & (1ULL << (flat & AI_BITS_PER_LONG_MASK));
}

static int ai_axis_pair_matches(const int *axis)
{
    return (axis[0] == axis[1]) + (axis[1] == axis[2]) + (axis[2] == axis[0]);
}

static int ai_alignment_score(const int *q, const int *r, const int *s)
{
    return ai_axis_pair_matches(q) + ai_axis_pair_matches(r) + ai_axis_pair_matches(s);
}

static int ai_piece_compactness_distance(const int *q, const int *r, const int *s)
{
    int d1 = ai_distance_to(q[0], r[0], s[0], q[1], r[1], s[1]);
    int d2 = ai_distance_to(q[1], r[1], s[1], q[2], r[2], s[2]);
    int d3 = ai_distance_to(q[2], r[2], s[2], q[0], r[0], s[0]);
    int max_d = d1;

    if (d2 > max_d)
    {
        max_d = d2;
    }
    if (d3 > max_d)
    {
        max_d = d3;
    }

    return d1 + d2 + d3 - max_d;
}

static int ai_same_coord2(int q1, int r1, int q2, int r2)
{
    return q1 == q2 && r1 == r2;
}

typedef struct AiCoordSet
{
    unsigned long long bits[AI_COORDSET_WORDS];
} AiCoordSet;

static int ai_flat_index(int q, int r)
{
    return (q + AI_BOARD_OFFSET) + (r + AI_BOARD_OFFSET) * AI_BOARD_WIDTH;
}

static void ai_coordset_clear(AiCoordSet *set)
{
    int i;
    for (i = 0; i < AI_COORDSET_WORDS; ++i)
    {
        set->bits[i] = 0ULL;
    }
}

static void ai_coordset_add(AiCoordSet *set, int q, int r)
{
    int flat = ai_flat_index(q, r);
    if (flat < 0 || flat >= AI_BOARD_BITS)
    {
        return;
    }
    set->bits[(unsigned int)flat >> AI_BITS_PER_LONG_SHIFT] |= (1ULL << (flat & AI_BITS_PER_LONG_MASK));
}

static int ai_coordset_contains(const AiCoordSet *set, int q, int r)
{
    int flat = ai_flat_index(q, r);
    if (flat < 0 || flat >= AI_BOARD_BITS)
    {
        return 0;
    }
    return (set->bits[(unsigned int)flat >> AI_BITS_PER_LONG_SHIFT] & (1ULL << (flat & AI_BITS_PER_LONG_MASK))) != 0;
}

static int ai_contains_coord2_fallback(const int *q, const int *r, int count, int cq, int cr)
{
    int i;
    for (i = 0; i < count; ++i)
    {
        if (ai_same_coord2(q[i], r[i], cq, cr))
        {
            return 1;
        }
    }
    return 0;
}

static int ai_contains_coord2_set(
    const AiCoordSet *set,
    const int *q,
    const int *r,
    int count,
    int cq,
    int cr)
{
    int flat = ai_flat_index(cq, cr);
    if (flat < 0 || flat >= AI_BOARD_BITS)
    {
        return ai_contains_coord2_fallback(q, r, count, cq, cr);
    }
    return ai_coordset_contains(set, cq, cr);
}

static void ai_switch_player(int *current_player)
{
    *current_player = (*current_player == RED) ? BLACK : RED;
}

static void ai_next_turn_phase(int *current_player, int *turn_phase)
{
    if (*turn_phase == PIECE_TO_MOVE)
    {
        *turn_phase = TILE_TO_MOVE;
    }
    else
    {
        *turn_phase = PIECE_TO_MOVE;
        ai_switch_player(current_player);
    }
}

typedef struct AiSearchState
{
    NonagaBitBoard board;
    int current_player;
    int turn_phase;
} AiSearchState;

static void ai_save_state(AiSearchState *snapshot, const NonagaBitBoard *board, int current_player, int turn_phase)
{
    snapshot->board = *board;
    snapshot->current_player = current_player;
    snapshot->turn_phase = turn_phase;
}

static void ai_restore_state(NonagaBitBoard *board, int *current_player, int *turn_phase, const AiSearchState *snapshot)
{
    *board = snapshot->board;
    *current_player = snapshot->current_player;
    *turn_phase = snapshot->turn_phase;
}

static void ai_move_piece_state(NonagaBitBoard *board, int *current_player, int *turn_phase, int from_q, int from_r, int to_q, int to_r)
{
    bitboard_move_piece(board, from_q, from_r, to_q, to_r);
    ai_next_turn_phase(current_player, turn_phase);
}

static void ai_move_tile_state(NonagaBitBoard *board, int *current_player, int *turn_phase, int from_q, int from_r, int to_q, int to_r)
{
    bitboard_move_tile(board, from_q, from_r, to_q, to_r);
    ai_next_turn_phase(current_player, turn_phase);
}

Move2D ai_empty_move(void)
{
    Move2D move;
    move.from_q = 0;
    move.from_r = 0;
    move.to_q = 0;
    move.to_r = 0;
    move.is_set = 0;
    return move;
}

MinimaxResult ai_new_result(int cost)
{
    MinimaxResult result;
    result.cost = cost;
    result.piece_move = ai_empty_move();
    result.tile_move = ai_empty_move();
    return result;
}

int ai_distance_to(int q1, int r1, int s1, int q2, int r2, int s2)
{
    /* Cube-coordinate hex distance. */
    int dq = ai_abs(q1 - q2);
    int dr = ai_abs(r1 - r2);
    int ds = ai_abs(s1 - s2);
    return (dq + dr + ds) / 2;
}

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
    int color)
{
    MissingInfo info;
    const unsigned long long *enemy_bits = (color == RED) ? board->black_pieces : board->red_pieces;
    int q_min = p0q;
    int q_max = p0q;
    int r_min = p0r;
    int r_max = p0r;
    int s_min = p0s;
    int s_max = p0s;
    int q;
    int r;

    info.missing_count = 0;
    info.enemy_count = 0;

    if (p1q < q_min)
        q_min = p1q;
    if (p2q < q_min)
        q_min = p2q;
    if (p1q > q_max)
        q_max = p1q;
    if (p2q > q_max)
        q_max = p2q;

    if (p1r < r_min)
        r_min = p1r;
    if (p2r < r_min)
        r_min = p2r;
    if (p1r > r_max)
        r_max = p1r;
    if (p2r > r_max)
        r_max = p2r;

    if (p1s < s_min)
        s_min = p1s;
    if (p2s < s_min)
        s_min = p2s;
    if (p1s > s_max)
        s_max = p1s;
    if (p2s > s_max)
        s_max = p2s;

    for (q = q_min; q <= q_max; ++q)
    {
        for (r = r_min; r <= r_max; ++r)
        {
            int s = -q - r;
            int flat;
            if (s < s_min || s > s_max)
            {
                continue;
            }

            flat = ai_flat_index(q, r);
            if (!ai_has_tile_flat(board, flat))
            {
                info.missing_count += 1;
            }
            else if (ai_enemy_piece_flat(enemy_bits, flat))
            {
                info.enemy_count += 1;
            }
        }
    }

    return info;
}

static int ai_check_win_condition(NonagaBitBoard *board, int color)
{
    int q[3];
    int r[3];
    int s[3];
    int visited[3] = {0, 0, 0};
    int queue[3];
    int piece_count;
    int head = 0;
    int tail = 0;
    int visited_count = 0;

    piece_count = bitboard_get_pieces(board, color, &q[0], &r[0], &s[0]);
    if (piece_count <= 0)
    {
        return 0;
    }

    visited[0] = 1;
    queue[tail++] = 0;
    visited_count = 1;

    /* BFS over adjacent friendly pieces to test full connectivity. */
    while (head < tail)
    {
        int idx = queue[head++];
        int cq = q[idx];
        int cr = r[idx];
        int i;

        for (i = 0; i < 6; ++i)
        {
            int adj_q = cq + WIN_OFFSETS[i][0];
            int adj_r = cr + WIN_OFFSETS[i][1];
            int j;
            for (j = 0; j < piece_count; ++j)
            {
                if (visited[j])
                {
                    continue;
                }
                if (q[j] == adj_q && r[j] == adj_r)
                {
                    visited[j] = 1;
                    queue[tail++] = j;
                    visited_count += 1;
                    break;
                }
            }
        }
    }

    return visited_count == piece_count;
}

static int ai_check_any_win(NonagaBitBoard *board)
{
    return ai_check_win_condition(board, RED) || ai_check_win_condition(board, BLACK);
}

static int ai_piece_destination_in_direction(
    NonagaBitBoard *board,
    int piece_q,
    int piece_r,
    int piece_s,
    int dimension,
    int direction,
    int *out_q,
    int *out_r,
    int *out_s)
{
    int coords[3];
    int fixed_index = (dimension + 1) % 3;
    int dependent_index = (dimension + 2) % 3;
    int i;
    int found = 0;

    coords[0] = piece_q;
    coords[1] = piece_r;
    coords[2] = piece_s;

    for (i = coords[dimension] + direction; i != direction * 100; i += direction)
    {
        int q;
        int r;
        int s;

        coords[0] = piece_q;
        coords[1] = piece_r;
        coords[2] = piece_s;
        coords[dimension] = i;
        coords[dependent_index] = -(coords[dimension] + coords[fixed_index]);

        q = coords[0];
        r = coords[1];
        s = coords[2];

        if (bitboard_is_there_piece(board, q, r))
        {
            break;
        }
        if (bitboard_is_there_tile(board, q, r))
        {
            *out_q = q;
            *out_r = r;
            *out_s = s;
            found = 1;
        }
        else
        {
            break;
        }
    }

    return found;
}

static int ai_neighbors_restrain_piece(const int *nq, const int *nr, int neighbor_count)
{
    int visited[6];
    int queue[6];
    int head = 0;
    int tail = 0;
    int visited_count = 0;
    int i;

    if (neighbor_count <= 0)
    {
        return 0;
    }

    for (i = 0; i < neighbor_count; ++i)
    {
        visited[i] = 0;
    }

    visited[0] = 1;
    queue[tail++] = 0;
    visited_count = 1;

    while (head < tail)
    {
        int idx = queue[head++];
        int cq = nq[idx];
        int cr = nr[idx];
        int offset_idx;

        for (offset_idx = 0; offset_idx < 6; ++offset_idx)
        {
            int aq = cq + WIN_OFFSETS[offset_idx][0];
            int ar = cr + WIN_OFFSETS[offset_idx][1];
            int j;
            for (j = 0; j < neighbor_count; ++j)
            {
                if (visited[j])
                {
                    continue;
                }
                if (nq[j] == aq && nr[j] == ar)
                {
                    visited[j] = 1;
                    queue[tail++] = j;
                    visited_count += 1;
                    break;
                }
            }
        }
    }

    return visited_count == neighbor_count;
}

int ai_cost_function(NonagaBitBoard *board, int maximizing_player, int max_color, const int *params)
{
    int min_color = (max_color + 1) % 2;
    int max_q[3];
    int max_r[3];
    int max_s[3];
    int min_q[3];
    int min_r[3];
    int min_s[3];
    int max_count;
    int min_count;
    int max_aligned;
    int min_aligned;
    int max_distance;
    int min_distance;
    int max_cost;
    int min_cost;
    MissingInfo max_missing;
    MissingInfo min_missing;

    (void)maximizing_player;

    /* Evaluation combines alignment, compactness, missing tiles, and enemy blockers. */
    max_count = bitboard_get_pieces(board, max_color, &max_q[0], &max_r[0], &max_s[0]);
    min_count = bitboard_get_pieces(board, min_color, &min_q[0], &min_r[0], &min_s[0]);

    if (max_count < 3 || min_count < 3)
    {
        return 0;
    }

    max_aligned = ai_alignment_score(&max_q[0], &max_r[0], &max_s[0]);
    max_distance = ai_piece_compactness_distance(&max_q[0], &max_r[0], &max_s[0]);

    max_missing = ai_missing_tiles_and_enemy_pieces_from_board(
        board,
        max_q[0], max_r[0], max_s[0],
        max_q[1], max_r[1], max_s[1],
        max_q[2], max_r[2], max_s[2],
        max_color);

    max_cost = params[0] * max_aligned - params[1] * max_distance - params[2] * max_missing.missing_count - params[3] * max_missing.enemy_count;

    min_aligned = ai_alignment_score(&min_q[0], &min_r[0], &min_s[0]);
    min_distance = ai_piece_compactness_distance(&min_q[0], &min_r[0], &min_s[0]);

    min_missing = ai_missing_tiles_and_enemy_pieces_from_board(
        board,
        min_q[0], min_r[0], min_s[0],
        min_q[1], min_r[1], min_s[1],
        min_q[2], min_r[2], min_s[2],
        min_color);

    min_cost = -params[4] * min_aligned + params[5] * min_distance + params[6] * min_missing.missing_count + params[7] * min_missing.enemy_count;

    return max_cost + min_cost;
}

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
    const int *params)
{
    MinimaxResult result;
    MinimaxResult out;
    Move2D best_piece_move = ai_empty_move();
    Move2D best_tile_move = ai_empty_move();
    int value;
    int piece_q[3];
    int piece_r[3];
    int piece_s[3];
    int piece_count;
    int piece_idx;
    AiSearchState snapshot;
    unsigned long long current_hash;
    TTEntry *tt_entry;
    int tt_hit = 0;
    Move2D tt_piece_move = ai_empty_move();
    Move2D tt_tile_move = ai_empty_move();
    int alpha_orig = alpha;
    
    /* Candidate move structs for ordering */
    struct Candidate {
        int piece_q, piece_r, dest_q, dest_r;
        int score;    
    };
    struct Candidate candidates[18]; /* 3 pieces * 6 directions = max 18 candidate slide destinations */
    int num_candidates = 0;
    int i, j;

    (void)color;


    if (ai_check_any_win(board))
    {
        return maximizing_player ? ai_new_result(NEG_INF-depth) : ai_new_result(POS_INF+depth);
    }

    if (depth == 0)
    {
        return ai_new_result(ai_cost_function(board, maximizing_player, max_color, params));
    }
    /* TT Lookup */
    current_hash = ai_compute_hash(board, *current_player, *turn_phase);
    tt_entry = &ai_tt[current_hash & (TT_SIZE - 1)];

    if (tt_entry->hash == current_hash) {
        tt_hit = 1;
        tt_piece_move = tt_entry->best_piece_move;
        tt_tile_move = tt_entry->best_tile_move;
        if (tt_entry->depth >= depth) {
            if (tt_entry->flag == TT_EXACT) {
                out = ai_new_result(tt_entry->value);
                out.piece_move = tt_piece_move;
                out.tile_move = tt_tile_move;
                return out;
            } else if (tt_entry->flag == TT_LOWER) {
                if (tt_entry->value > alpha) alpha = tt_entry->value;
            } else if (tt_entry->flag == TT_UPPER) {
                if (tt_entry->value < beta) beta = tt_entry->value;
            }
            if (alpha >= beta) {
                out = ai_new_result(tt_entry->value);
                out.piece_move = tt_piece_move;
                out.tile_move = tt_tile_move;
                return out;
            }
        }
    }

    piece_count = bitboard_get_pieces(board, *current_player, &piece_q[0], &piece_r[0], &piece_s[0]);
    if (piece_count <= 0)
    {
        return ai_new_result(ai_cost_function(board, maximizing_player, max_color, params));
    }

    value = maximizing_player ? NEG_INF - 1000 : POS_INF + 1000;

    /* 
     * Move Ordering: Try TT move FIRST 
     * By attempting the 'best move' cached from a previous shallow depth search, 
     * we are statistically highly likely to cause an immediate beta-cutoff. 
     */
    if (tt_hit && tt_piece_move.is_set) {
        ai_save_state(&snapshot, board, *current_player, *turn_phase);
        ai_move_piece_state(board, current_player, turn_phase, tt_piece_move.from_q, tt_piece_move.from_r, tt_piece_move.to_q, tt_piece_move.to_r);
        result = ai_minimax_tile(board, current_player, turn_phase, depth, maximizing_player, color, alpha, beta, max_color, params);
        ai_restore_state(board, current_player, turn_phase, &snapshot);

        if (maximizing_player) {
            if (result.cost >= value) {
                value = result.cost;
                best_piece_move = tt_piece_move;
                best_piece_move.is_set = 1;
                best_tile_move = result.tile_move;
            }
            if (value > alpha) alpha = value;
        } else {
            if (result.cost <= value) {
                value = result.cost;
                best_piece_move = tt_piece_move;
                best_piece_move.is_set = 1;
                best_tile_move = result.tile_move;
            }
            if (value < beta) beta = value;
        }

        if (alpha >= beta) {
            /* Alpha-Beta Pruning: The cached TT move successfully bounded the search. 
               We can completely skip generating other destination candidates! */
            goto store_and_return;
        }
    }

    /* Move Ordering: Generate Candidates */
    for (piece_idx = 0; piece_idx < piece_count; ++piece_idx)
    {
        int dim;
        for (dim = 0; dim < 3; ++dim)
        {
            int dir;
            for (dir = -1; dir <= 1; dir += 2)
            {
                int dest_q, dest_r, dest_s;

                if (!ai_piece_destination_in_direction(
                        board, piece_q[piece_idx], piece_r[piece_idx], piece_s[piece_idx],
                        dim, dir, &dest_q, &dest_r, &dest_s))
                {
                    continue;
                }

                /* Skip the TT move we already evaluated */
                if (tt_hit && tt_piece_move.is_set && 
                    piece_q[piece_idx] == tt_piece_move.from_q && piece_r[piece_idx] == tt_piece_move.from_r &&
                    dest_q == tt_piece_move.to_q && dest_r == tt_piece_move.to_r) {
                    continue;
                }

                candidates[num_candidates].piece_q = piece_q[piece_idx];
                candidates[num_candidates].piece_r = piece_r[piece_idx];
                candidates[num_candidates].dest_q = dest_q;
                candidates[num_candidates].dest_r = dest_r;
                /* Note: Candidates are initialized with a neutral score. In deeper extensions, 
                   History Heuristics or static piece compactness weights would update this score. */
                candidates[num_candidates].score = 0; 
                num_candidates++;
            }
        }
    }

    /* 
     * Standard Alpha-Beta Loop: Enumerate through the newly generated candidates. 
     * The TT move is naturally handled due to the generation skip rules above.
     */
    for (i = 0; i < num_candidates; ++i) {
        ai_save_state(&snapshot, board, *current_player, *turn_phase);

        ai_move_piece_state(
            board, current_player, turn_phase,
            candidates[i].piece_q, candidates[i].piece_r,
            candidates[i].dest_q, candidates[i].dest_r);

        result = ai_minimax_tile(
            board, current_player, turn_phase, depth, maximizing_player, color,
            alpha, beta, max_color, params);

        ai_restore_state(board, current_player, turn_phase, &snapshot);

        if (maximizing_player)
        {
            if (result.cost >= value)
            {
                value = result.cost;
                best_piece_move.from_q = candidates[i].piece_q;
                best_piece_move.from_r = candidates[i].piece_r;
                best_piece_move.to_q = candidates[i].dest_q;
                best_piece_move.to_r = candidates[i].dest_r;
                best_piece_move.is_set = 1;
                best_tile_move = result.tile_move;
            }
            if (value > alpha) alpha = value;
        }
        else
        {
            if (result.cost <= value)
            {
                value = result.cost;
                best_piece_move.from_q = candidates[i].piece_q;
                best_piece_move.from_r = candidates[i].piece_r;
                best_piece_move.to_q = candidates[i].dest_q;
                best_piece_move.to_r = candidates[i].dest_r;
                best_piece_move.is_set = 1;
                best_tile_move = result.tile_move;
            }
            if (value < beta) beta = value;
        }

        if (alpha >= beta) break;
    }

store_and_return:
    if (!best_piece_move.is_set || !best_tile_move.is_set)
    {
        return ai_new_result(ai_cost_function(board, maximizing_player, max_color, params));
    }

    out = ai_new_result(value);
    out.piece_move = best_piece_move;
    out.tile_move = best_tile_move;

    /* Write to TT */
    tt_entry->hash = current_hash;
    tt_entry->depth = depth;
    tt_entry->value = value;
    tt_entry->best_piece_move = best_piece_move;
    tt_entry->best_tile_move = best_tile_move;
    if (value <= alpha_orig) {
        tt_entry->flag = TT_UPPER;
    } else if (value >= beta) {
        tt_entry->flag = TT_LOWER;
    } else {
        tt_entry->flag = TT_EXACT;
    }

    return out;
}

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
    const int *params)
{
    MinimaxResult result = ai_new_result(0);
    MinimaxResult out;
    Move2D best_tile_move = ai_empty_move();
    int value;
    int tile_q[MAX_TILES];
    int tile_r[MAX_TILES];
    int tile_s[MAX_TILES];
    int tile_count;
    int tile_idx;
    AiSearchState snapshot;
    unsigned long long current_hash;
    TTEntry *tt_entry;
    int tt_hit = 0;
    Move2D tt_tile_move = ai_empty_move();
    int alpha_orig = alpha;

    struct Candidate {
        int tile_q, tile_r, dest_q, dest_r;
        int score;
    };
    /* Max possible tiles is large, dynamically limit to sensible candidate size */
    struct Candidate candidates[MAX_TILE_CANDIDATES];
    int num_candidates = 0;
    int i;

    tile_count = bitboard_get_movable_tiles(board, &tile_q[0], &tile_r[0], &tile_s[0], MAX_TILES);
    if (tile_count <= 0)
    {
        return ai_new_result(ai_cost_function(board, maximizing_player, max_color, params));
    }

    /* TT Lookup */
    current_hash = ai_compute_hash(board, *current_player, *turn_phase);
    tt_entry = &ai_tt[current_hash & (TT_SIZE - 1)];

    if (tt_entry->hash == current_hash) {
        tt_hit = 1;
        tt_tile_move = tt_entry->best_tile_move;
        if (tt_entry->depth >= depth) {
            if (tt_entry->flag == TT_EXACT) {
                out = ai_new_result(tt_entry->value);
                out.tile_move = tt_tile_move;
                return out;
            } else if (tt_entry->flag == TT_LOWER) {
                if (tt_entry->value > alpha) alpha = tt_entry->value;
            } else if (tt_entry->flag == TT_UPPER) {
                if (tt_entry->value < beta) beta = tt_entry->value;
            }
            if (alpha >= beta) {
                out = ai_new_result(tt_entry->value);
                out.tile_move = tt_tile_move;
                return out;
            }
        }
    }

    value = maximizing_player ? NEG_INF - 1000 : POS_INF + 1000;

    /* Move Ordering: Evaluate the TT cache's best tile move first to maximize beta-cutoff speed. */
    if (tt_hit && tt_tile_move.is_set) {
        ai_save_state(&snapshot, board, *current_player, *turn_phase);
        ai_move_tile_state(board, current_player, turn_phase, tt_tile_move.from_q, tt_tile_move.from_r, tt_tile_move.to_q, tt_tile_move.to_r);
        result = ai_minimax_piece(board, current_player, turn_phase, depth - 1, !maximizing_player, (color + 1) % 2, alpha, beta, max_color, params);
        ai_restore_state(board, current_player, turn_phase, &snapshot);

        if (maximizing_player) {
            if (result.cost >= value) {
                value = result.cost;
                best_tile_move = tt_tile_move;
                best_tile_move.is_set = 1;
            }
            if (value > alpha) alpha = value;
        } else {
            if (result.cost <= value) {
                value = result.cost;
                best_tile_move = tt_tile_move;
                best_tile_move.is_set = 1;
            }
            if (value < beta) beta = value;
        }

        if (alpha >= beta) {
            /* Alpha-Beta Pruning: Found immediate tile move cutoff. */
            goto store_and_return_tile;
        }
    }

    /* Move Ordering: Generate Candidates */
    for (tile_idx = 0; tile_idx < tile_count; ++tile_idx)
    {
        int valid_q[MAX_TILE_CANDIDATES];
        int valid_r[MAX_TILE_CANDIDATES];
        int valid_s[MAX_TILE_CANDIDATES];
        int valid_count, d_idx;

        valid_count = bitboard_get_valid_tile_positions_for_tile(
            board, tile_q[tile_idx], tile_r[tile_idx], tile_s[tile_idx],
            &valid_q[0], &valid_r[0], &valid_s[0], MAX_TILE_CANDIDATES);

        for (d_idx = 0; d_idx < valid_count; ++d_idx)
        {
            if (tt_hit && tt_tile_move.is_set &&
                tile_q[tile_idx] == tt_tile_move.from_q && tile_r[tile_idx] == tt_tile_move.from_r &&
                valid_q[d_idx] == tt_tile_move.to_q && valid_r[d_idx] == tt_tile_move.to_r) {
                continue;
            }
            if (num_candidates >= MAX_TILE_CANDIDATES) break;

            candidates[num_candidates].tile_q = tile_q[tile_idx];
            candidates[num_candidates].tile_r = tile_r[tile_idx];
            candidates[num_candidates].dest_q = valid_q[d_idx];
            candidates[num_candidates].dest_r = valid_r[d_idx];
            num_candidates++;
        }
        if (num_candidates >= MAX_TILE_CANDIDATES) break;
    }

    /* Standard Alpha-Beta Loop for tile evaluation. */
    for (i = 0; i < num_candidates; ++i) {
        ai_save_state(&snapshot, board, *current_player, *turn_phase);

        ai_move_tile_state(
            board, current_player, turn_phase,
            candidates[i].tile_q, candidates[i].tile_r,
            candidates[i].dest_q, candidates[i].dest_r);

        result = ai_minimax_piece(
            board, current_player, turn_phase, depth - 1, !maximizing_player,
            (color + 1) % 2, alpha, beta, max_color, params);

        ai_restore_state(board, current_player, turn_phase, &snapshot);

        if (maximizing_player)
        {
            if (result.cost >= value)
            {
                value = result.cost;
                best_tile_move.from_q = candidates[i].tile_q;
                best_tile_move.from_r = candidates[i].tile_r;
                best_tile_move.to_q = candidates[i].dest_q;
                best_tile_move.to_r = candidates[i].dest_r;
                best_tile_move.is_set = 1;
            }
            if (value > alpha) alpha = value;
        }
        else
        {
            if (result.cost <= value)
            {
                value = result.cost;
                best_tile_move.from_q = candidates[i].tile_q;
                best_tile_move.from_r = candidates[i].tile_r;
                best_tile_move.to_q = candidates[i].dest_q;
                best_tile_move.to_r = candidates[i].dest_r;
                best_tile_move.is_set = 1;
            }
            if (value < beta) beta = value;
        }

        if (alpha >= beta) break;
    }

store_and_return_tile:

    if (!best_tile_move.is_set)
    {
        return ai_new_result(ai_cost_function(board, maximizing_player, max_color, params));
    }

    out = ai_new_result(value);
    out.tile_move = best_tile_move;

    /* Write to TT */
    tt_entry->hash = current_hash;
    tt_entry->depth = depth;
    tt_entry->value = value;
    tt_entry->best_piece_move = ai_empty_move();
    tt_entry->best_tile_move = best_tile_move;
    if (value <= alpha_orig) {
        tt_entry->flag = TT_UPPER;
    } else if (value >= beta) {
        tt_entry->flag = TT_LOWER;
    } else {
        tt_entry->flag = TT_EXACT;
    }

    return out;
}

MinimaxResult ai_search_iterative_deepening(
    NonagaBitBoard *board,
    int current_player,
    int turn_phase,
    int max_depth,
    int maximizing_player,
    int color,
    int max_color,
    const int *params)
{
    MinimaxResult overall_best;
    int current_player_copy;
    int turn_phase_copy;
    int d;

    overall_best = ai_new_result(0);

    /* 
     * Iterative Deepening leverages Transposition Tables by saving the best path from 
     * Depth N to automatically re-order and accelerate the search of Depth N+1.
     * The TT is intentionally preserved across game turns. Because board fragments typically 
     * remain unmodified, previously searched branches maintain their boundary validity deep 
     * into the late-game, multiplying performance drastically.
     */

    for (d = 1; d <= max_depth; d++) {
        current_player_copy = current_player;
        turn_phase_copy = turn_phase;

        overall_best = ai_minimax_piece(
            board,
            &current_player_copy,
            &turn_phase_copy,
            d,
            maximizing_player,
            color,
            NEG_INF,
            POS_INF,
            max_color,
            params
        );
    }

    return overall_best;
}
