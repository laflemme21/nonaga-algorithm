#include "AI_core.h"

#define RED 0
#define BLACK 1
#define PIECE_TO_MOVE 0
#define TILE_TO_MOVE 1
#define NEG_INF (-99999999)
#define POS_INF 99999999
#define MAX_TILES 448
#define MAX_TILE_CANDIDATES 2688

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

static int ai_same_coord3(int q1, int r1, int s1, int q2, int r2, int s2)
{
    return q1 == q2 && r1 == r2 && s1 == s2;
}

static int ai_contains_coord3(const int *q, const int *r, const int *s, int count, int cq, int cr, int cs)
{
    int i;
    for (i = 0; i < count; ++i)
    {
        if (ai_same_coord3(q[i], r[i], s[i], cq, cr, cs))
        {
            return 1;
        }
    }
    return 0;
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

static void ai_last_turn_phase(int *current_player, int *turn_phase)
{
    if (*turn_phase == PIECE_TO_MOVE)
    {
        *turn_phase = TILE_TO_MOVE;
        ai_switch_player(current_player);
    }
    else
    {
        *turn_phase = PIECE_TO_MOVE;
    }
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

static void ai_undo_piece_state(NonagaBitBoard *board, int *current_player, int *turn_phase, int from_q, int from_r, int to_q, int to_r)
{
    bitboard_move_piece(board, from_q, from_r, to_q, to_r);
    ai_last_turn_phase(current_player, turn_phase);
}

static void ai_undo_tile_state(NonagaBitBoard *board, int *current_player, int *turn_phase, int from_q, int from_r, int to_q, int to_r)
{
    bitboard_move_tile(board, from_q, from_r, to_q, to_r);
    ai_last_turn_phase(current_player, turn_phase);
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
            if (s < s_min || s > s_max)
            {
                continue;
            }
            if (!bitboard_has_tile(board, q, r))
            {
                info.missing_count += 1;
            }
            else
            {
                int found = bitboard_get_color(board, q, r);
                if (found != -1 && found != color)
                {
                    info.enemy_count += 1;
                }
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

    while (head < tail)
    {
        int idx = queue[head++];
        int cq = q[idx];
        int cr = r[idx];
        int cs = s[idx];
        int i;

        for (i = 0; i < 6; ++i)
        {
            int adj_q = cq + WIN_OFFSETS[i][0];
            int adj_r = cr + WIN_OFFSETS[i][1];
            int adj_s = cs + WIN_OFFSETS[i][2];
            int j;
            for (j = 0; j < piece_count; ++j)
            {
                if (visited[j])
                {
                    continue;
                }
                if (q[j] == adj_q && r[j] == adj_r && s[j] == adj_s)
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

static int ai_neighbors_restrain_piece(const int *nq, const int *nr, const int *ns, int neighbor_count)
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
        int cs = ns[idx];
        int offset_idx;

        for (offset_idx = 0; offset_idx < 6; ++offset_idx)
        {
            int aq = cq + WIN_OFFSETS[offset_idx][0];
            int ar = cr + WIN_OFFSETS[offset_idx][1];
            int as = cs + WIN_OFFSETS[offset_idx][2];
            int j;
            for (j = 0; j < neighbor_count; ++j)
            {
                if (visited[j])
                {
                    continue;
                }
                if (nq[j] == aq && nr[j] == ar && ns[j] == as)
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

static int ai_get_valid_tile_positions_for_tile(
    NonagaBitBoard *board,
    int tile_q,
    int tile_r,
    int tile_s,
    int *out_q,
    int *out_r,
    int *out_s,
    int max_out)
{
    int all_q[MAX_TILES];
    int all_r[MAX_TILES];
    int all_s[MAX_TILES];
    int base_q[MAX_TILES];
    int base_r[MAX_TILES];
    int base_s[MAX_TILES];
    int candidate_q[MAX_TILE_CANDIDATES];
    int candidate_r[MAX_TILE_CANDIDATES];
    int candidate_s[MAX_TILE_CANDIDATES];
    int tile_count;
    int base_count = 0;
    int candidate_count = 0;
    int valid_count = 0;
    int i;

    tile_count = bitboard_get_all_tiles(board, &all_q[0], &all_r[0], &all_s[0], MAX_TILES);
    if (!ai_contains_coord3(all_q, all_r, all_s, tile_count, tile_q, tile_r, tile_s))
    {
        return 0;
    }

    for (i = 0; i < tile_count; ++i)
    {
        if (!ai_same_coord3(all_q[i], all_r[i], all_s[i], tile_q, tile_r, tile_s))
        {
            base_q[base_count] = all_q[i];
            base_r[base_count] = all_r[i];
            base_s[base_count] = all_s[i];
            base_count += 1;
        }
    }

    for (i = 0; i < base_count; ++i)
    {
        int offset_idx;
        for (offset_idx = 0; offset_idx < 6; ++offset_idx)
        {
            int cq = base_q[i] + WIN_OFFSETS[offset_idx][0];
            int cr = base_r[i] + WIN_OFFSETS[offset_idx][1];
            int cs = base_s[i] + WIN_OFFSETS[offset_idx][2];
            if (ai_contains_coord3(base_q, base_r, base_s, base_count, cq, cr, cs))
            {
                continue;
            }
            if (ai_contains_coord3(candidate_q, candidate_r, candidate_s, candidate_count, cq, cr, cs))
            {
                continue;
            }
            if (candidate_count < MAX_TILE_CANDIDATES)
            {
                candidate_q[candidate_count] = cq;
                candidate_r[candidate_count] = cr;
                candidate_s[candidate_count] = cs;
                candidate_count += 1;
            }
        }
    }

    for (i = 0; i < candidate_count; ++i)
    {
        int neighbor_q[6];
        int neighbor_r[6];
        int neighbor_s[6];
        int neighbor_count = 0;
        int offset_idx;

        for (offset_idx = 0; offset_idx < 6; ++offset_idx)
        {
            int nq = candidate_q[i] + WIN_OFFSETS[offset_idx][0];
            int nr = candidate_r[i] + WIN_OFFSETS[offset_idx][1];
            int ns = candidate_s[i] + WIN_OFFSETS[offset_idx][2];
            if (ai_contains_coord3(base_q, base_r, base_s, base_count, nq, nr, ns))
            {
                neighbor_q[neighbor_count] = nq;
                neighbor_r[neighbor_count] = nr;
                neighbor_s[neighbor_count] = ns;
                neighbor_count += 1;
            }
        }

        if (neighbor_count >= 2 && neighbor_count <= 4)
        {
            int ok = 0;
            if (neighbor_count <= 2)
            {
                ok = 1;
            }
            else
            {
                ok = ai_neighbors_restrain_piece(neighbor_q, neighbor_r, neighbor_s, neighbor_count);
            }

            if (ok && !ai_same_coord3(candidate_q[i], candidate_r[i], candidate_s[i], tile_q, tile_r, tile_s))
            {
                if (valid_count < max_out)
                {
                    out_q[valid_count] = candidate_q[i];
                    out_r[valid_count] = candidate_r[i];
                    out_s[valid_count] = candidate_s[i];
                    valid_count += 1;
                }
            }
        }
    }

    return valid_count;
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
    int max_aligned = 0;
    int min_aligned = 0;
    int max_distance;
    int min_distance;
    int max_cost;
    int min_cost;
    MissingInfo max_missing;
    MissingInfo min_missing;
    int d1;
    int d2;
    int d3;

    (void)maximizing_player;

    max_count = bitboard_get_pieces(board, max_color, &max_q[0], &max_r[0], &max_s[0]);
    min_count = bitboard_get_pieces(board, min_color, &min_q[0], &min_r[0], &min_s[0]);

    if (max_count < 3 || min_count < 3)
    {
        return 0;
    }

    if (max_q[0] == max_q[1])
        max_aligned += 1;
    if (max_q[1] == max_q[2])
        max_aligned += 1;
    if (max_q[2] == max_q[0])
        max_aligned += 1;
    if (max_r[0] == max_r[1])
        max_aligned += 1;
    if (max_r[1] == max_r[2])
        max_aligned += 1;
    if (max_r[2] == max_r[0])
        max_aligned += 1;
    if (max_s[0] == max_s[1])
        max_aligned += 1;
    if (max_s[1] == max_s[2])
        max_aligned += 1;
    if (max_s[2] == max_s[0])
        max_aligned += 1;

    d1 = ai_distance_to(max_q[0], max_r[0], max_s[0], max_q[1], max_r[1], max_s[1]);
    d2 = ai_distance_to(max_q[1], max_r[1], max_s[1], max_q[2], max_r[2], max_s[2]);
    d3 = ai_distance_to(max_q[2], max_r[2], max_s[2], max_q[0], max_r[0], max_s[0]);
    max_distance = (d1 > d2 && d1 > d3) ? (d2 + d3) : ((d2 > d1 && d2 > d3) ? (d3 + d1) : (d1 + d2));

    max_missing = ai_missing_tiles_and_enemy_pieces_from_board(
        board,
        max_q[0], max_r[0], max_s[0],
        max_q[1], max_r[1], max_s[1],
        max_q[2], max_r[2], max_s[2],
        max_color);

    max_cost = params[0] * max_aligned - params[1] * max_distance - params[2] * max_missing.missing_count - params[3] * max_missing.enemy_count;

    if (min_q[0] == min_q[1])
        min_aligned += 1;
    if (min_q[1] == min_q[2])
        min_aligned += 1;
    if (min_q[2] == min_q[0])
        min_aligned += 1;
    if (min_r[0] == min_r[1])
        min_aligned += 1;
    if (min_r[1] == min_r[2])
        min_aligned += 1;
    if (min_r[2] == min_r[0])
        min_aligned += 1;
    if (min_s[0] == min_s[1])
        min_aligned += 1;
    if (min_s[1] == min_s[2])
        min_aligned += 1;
    if (min_s[2] == min_s[0])
        min_aligned += 1;

    d1 = ai_distance_to(min_q[0], min_r[0], min_s[0], min_q[1], min_r[1], min_s[1]);
    d2 = ai_distance_to(min_q[1], min_r[1], min_s[1], min_q[2], min_r[2], min_s[2]);
    d3 = ai_distance_to(min_q[2], min_r[2], min_s[2], min_q[0], min_r[0], min_s[0]);
    min_distance = (d1 > d2 && d1 > d3) ? (d2 + d3) : ((d2 > d1 && d2 > d3) ? (d3 + d1) : (d1 + d2));

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

    (void)color;

    if (depth == 0)
    {
        return ai_new_result(ai_cost_function(board, maximizing_player, max_color, params));
    }

    if (ai_check_any_win(board))
    {
        return maximizing_player ? ai_new_result(NEG_INF) : ai_new_result(POS_INF);
    }

    piece_count = bitboard_get_pieces(board, *current_player, &piece_q[0], &piece_r[0], &piece_s[0]);
    if (piece_count <= 0)
    {
        return ai_new_result(ai_cost_function(board, maximizing_player, max_color, params));
    }

    value = maximizing_player ? NEG_INF : POS_INF;

    for (piece_idx = 0; piece_idx < piece_count; ++piece_idx)
    {
        int dim;
        for (dim = 0; dim < 3; ++dim)
        {
            int dir;
            for (dir = -1; dir <= 1; dir += 2)
            {
                int dest_q;
                int dest_r;
                int dest_s;

                if (!ai_piece_destination_in_direction(
                        board,
                        piece_q[piece_idx],
                        piece_r[piece_idx],
                        piece_s[piece_idx],
                        dim,
                        dir,
                        &dest_q,
                        &dest_r,
                        &dest_s))
                {
                    continue;
                }

                ai_move_piece_state(
                    board,
                    current_player,
                    turn_phase,
                    piece_q[piece_idx],
                    piece_r[piece_idx],
                    dest_q,
                    dest_r);

                result = ai_minimax_tile(
                    board,
                    current_player,
                    turn_phase,
                    depth,
                    maximizing_player,
                    color,
                    alpha,
                    beta,
                    max_color,
                    params);

                ai_undo_piece_state(
                    board,
                    current_player,
                    turn_phase,
                    dest_q,
                    dest_r,
                    piece_q[piece_idx],
                    piece_r[piece_idx]);

                if (maximizing_player)
                {
                    if (result.cost >= value)
                    {
                        value = result.cost;
                        best_piece_move.from_q = piece_q[piece_idx];
                        best_piece_move.from_r = piece_r[piece_idx];
                        best_piece_move.to_q = dest_q;
                        best_piece_move.to_r = dest_r;
                        best_piece_move.is_set = 1;
                        best_tile_move = result.tile_move;
                    }
                    if (value > alpha)
                    {
                        alpha = value;
                    }
                }
                else
                {
                    if (result.cost <= value)
                    {
                        value = result.cost;
                        best_piece_move.from_q = piece_q[piece_idx];
                        best_piece_move.from_r = piece_r[piece_idx];
                        best_piece_move.to_q = dest_q;
                        best_piece_move.to_r = dest_r;
                        best_piece_move.is_set = 1;
                        best_tile_move = result.tile_move;
                    }
                    if (value < beta)
                    {
                        beta = value;
                    }
                }

                if (alpha >= beta)
                {
                    break;
                }
            }
            if (alpha >= beta)
            {
                break;
            }
        }
        if (alpha >= beta)
        {
            break;
        }
    }

    if (!best_piece_move.is_set || !best_tile_move.is_set)
    {
        return ai_new_result(ai_cost_function(board, maximizing_player, max_color, params));
    }

    out = ai_new_result(value);
    out.piece_move = best_piece_move;
    out.tile_move = best_tile_move;
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

    tile_count = bitboard_get_movable_tiles(board, &tile_q[0], &tile_r[0], &tile_s[0], MAX_TILES);
    if (tile_count <= 0)
    {
        return ai_new_result(ai_cost_function(board, maximizing_player, max_color, params));
    }

    value = maximizing_player ? NEG_INF : POS_INF;

    for (tile_idx = 0; tile_idx < tile_count; ++tile_idx)
    {
        int valid_q[MAX_TILE_CANDIDATES];
        int valid_r[MAX_TILE_CANDIDATES];
        int valid_s[MAX_TILE_CANDIDATES];
        int valid_count;
        int d_idx;

        valid_count = ai_get_valid_tile_positions_for_tile(
            board,
            tile_q[tile_idx],
            tile_r[tile_idx],
            tile_s[tile_idx],
            &valid_q[0],
            &valid_r[0],
            &valid_s[0],
            MAX_TILE_CANDIDATES);

        for (d_idx = 0; d_idx < valid_count; ++d_idx)
        {
            ai_move_tile_state(
                board,
                current_player,
                turn_phase,
                tile_q[tile_idx],
                tile_r[tile_idx],
                valid_q[d_idx],
                valid_r[d_idx]);

            result = ai_minimax_piece(
                board,
                current_player,
                turn_phase,
                depth - 1,
                !maximizing_player,
                (color + 1) % 2,
                alpha,
                beta,
                max_color,
                params);

            ai_undo_tile_state(
                board,
                current_player,
                turn_phase,
                valid_q[d_idx],
                valid_r[d_idx],
                tile_q[tile_idx],
                tile_r[tile_idx]);

            if (maximizing_player)
            {
                if (result.cost >= value)
                {
                    value = result.cost;
                    best_tile_move.from_q = tile_q[tile_idx];
                    best_tile_move.from_r = tile_r[tile_idx];
                    best_tile_move.to_q = valid_q[d_idx];
                    best_tile_move.to_r = valid_r[d_idx];
                    best_tile_move.is_set = 1;
                }
                if (value > alpha)
                {
                    alpha = value;
                }
            }
            else
            {
                if (result.cost <= value)
                {
                    value = result.cost;
                    best_tile_move.from_q = tile_q[tile_idx];
                    best_tile_move.from_r = tile_r[tile_idx];
                    best_tile_move.to_q = valid_q[d_idx];
                    best_tile_move.to_r = valid_r[d_idx];
                    best_tile_move.is_set = 1;
                }
                if (value < beta)
                {
                    beta = value;
                }
            }

            if (alpha >= beta)
            {
                break;
            }
        }

        if (alpha >= beta)
        {
            break;
        }
    }

    if (!best_tile_move.is_set)
    {
        return ai_new_result(ai_cost_function(board, maximizing_player, max_color, params));
    }

    out = ai_new_result(value);
    out.tile_move = best_tile_move;
    return out;
}
