#include "nonaga_bitboard.h"

#include <string.h>
#if defined(_MSC_VER)
#include <intrin.h>
#endif

#define RED 0
#define BLACK 1

#define BOARD_OFFSET 10
#define BOARD_WIDTH 21
#define ARRAY_SIZE 7
#define BITS_PER_LONG 64
#define BITS_PER_LONG_SHIFT 6
#define BITS_PER_LONG_MASK (BITS_PER_LONG - 1)
#define BOARD_BITS 448
#define FORBIDDEN_PATTERN_COUNT 5

static const int NEIGHBOR_FLAT_OFFSETS[6] = {-20, 1, 21, 20, -1, -21};
static const int NEIGHBOR_QR_OFFSETS[6][2] = {
    {1, -1},
    {1, 0},
    {0, 1},
    {-1, 1},
    {-1, 0},
    {0, -1},
};
static const int FORBIDDEN_PATTERN_LEN[FORBIDDEN_PATTERN_COUNT] = {3, 3, 4, 4, 4};
static const int FORBIDDEN_PATTERN_DIRS[FORBIDDEN_PATTERN_COUNT][4] = {
    {0, 2, 4, -1}, /* 1+1+1 */
    {1, 3, 5, -1}, /* 1+1+1 (rotated) */
    {0, 1, 3, 4},  /* 2+2 */
    {1, 2, 4, 5},  /* 2+2 (rotated) */
    {0, 2, 3, 5},  /* 2+2 (rotated) */
};

static unsigned long long FORBIDDEN_MASKS[BOARD_BITS][FORBIDDEN_PATTERN_COUNT][ARRAY_SIZE];
static unsigned char FORBIDDEN_VALID[BOARD_BITS][FORBIDDEN_PATTERN_COUNT];
static int FORBIDDEN_READY = 0;
static int NEIGHBOR_FLATS[BOARD_BITS][6];
static unsigned char LEGAL_NEIGHBOR_MASK[64];
static int TOPOLOGY_READY = 0;

static inline int flat_index(int q, int r)
{
    return (q + BOARD_OFFSET) + (r + BOARD_OFFSET) * BOARD_WIDTH;
}

static inline void set_bit(unsigned long long *bitboard, int q, int r)
{
    int flat = flat_index(q, r);
    if ((unsigned int)flat >= BOARD_BITS)
    {
        return;
    }
    bitboard[(unsigned int)flat >> BITS_PER_LONG_SHIFT] |= (1ULL << (flat & BITS_PER_LONG_MASK));
}

static inline void clear_bit(unsigned long long *bitboard, int q, int r)
{
    int flat = flat_index(q, r);
    if ((unsigned int)flat >= BOARD_BITS)
    {
        return;
    }
    bitboard[(unsigned int)flat >> BITS_PER_LONG_SHIFT] &= ~(1ULL << (flat & BITS_PER_LONG_MASK));
}

static inline void set_bit_flat(unsigned long long *bitboard, int flat)
{
    if ((unsigned int)flat >= BOARD_BITS)
    {
        return;
    }
    bitboard[(unsigned int)flat >> BITS_PER_LONG_SHIFT] |= (1ULL << (flat & BITS_PER_LONG_MASK));
}

static inline void clear_bit_flat(unsigned long long *bitboard, int flat)
{
    if ((unsigned int)flat >= BOARD_BITS)
    {
        return;
    }
    bitboard[(unsigned int)flat >> BITS_PER_LONG_SHIFT] &= ~(1ULL << (flat & BITS_PER_LONG_MASK));
}

static inline int check_bit_flat(const unsigned long long *bitboard, int flat)
{
    return (int)((bitboard[(unsigned int)flat >> BITS_PER_LONG_SHIFT] >> (flat & BITS_PER_LONG_MASK)) & 1ULL);
}

static inline int check_bit_flat_safe(const unsigned long long *bitboard, int flat)
{
    if ((unsigned int)flat >= BOARD_BITS)
    {
        return 0;
    }
    return check_bit_flat(bitboard, flat);
}

static inline int check_bit(const unsigned long long *bitboard, int q, int r)
{
    int flat = flat_index(q, r);
    return check_bit_flat_safe(bitboard, flat);
}

static inline void recover_coords(int flat, int *q, int *r, int *s)
{
    int r_shifted = flat / BOARD_WIDTH;
    int q_shifted = flat % BOARD_WIDTH;
    *q = q_shifted - BOARD_OFFSET;
    *r = r_shifted - BOARD_OFFSET;
    *s = -(*q) - (*r);
}

static inline int ctz64_nonzero(unsigned long long v)
{
#if defined(_MSC_VER)
    unsigned long idx;
#if defined(_M_X64) || defined(_M_AMD64) || defined(_M_ARM64)
    _BitScanForward64(&idx, v);
    return (int)idx;
#else
    _BitScanForward(&idx, (unsigned long)(v & 0xFFFFFFFFULL));
    if ((v & 0xFFFFFFFFULL) != 0)
    {
        return (int)idx;
    }
    _BitScanForward(&idx, (unsigned long)(v >> 32));
    return (int)(idx + 32);
#endif
#else
    return (int)__builtin_ctzll(v);
#endif
}

static int popcount6(unsigned int v)
{
    int c = 0;
    while (v)
    {
        v &= (v - 1U);
        c += 1;
    }
    return c;
}

static int mask_connected_ring(unsigned int mask)
{
    static const unsigned int DIR_ADJ[6] = {
        (1U << 1) | (1U << 5),
        (1U << 2) | (1U << 0),
        (1U << 3) | (1U << 1),
        (1U << 4) | (1U << 2),
        (1U << 5) | (1U << 3),
        (1U << 0) | (1U << 4),
    };
    unsigned int pending = mask;
    unsigned int visited = 0;
    int start = -1;
    int d;

    if (mask == 0U)
    {
        return 0;
    }

    for (d = 0; d < 6; ++d)
    {
        if (mask & (1U << d))
        {
            start = d;
            break;
        }
    }

    visited |= (1U << start);
    pending &= ~(1U << start);

    while (pending)
    {
        unsigned int frontier = 0U;
        for (d = 0; d < 6; ++d)
        {
            if (visited & (1U << d))
            {
                frontier |= DIR_ADJ[d];
            }
        }
        frontier &= pending;
        if (!frontier)
        {
            return 0;
        }
        visited |= frontier;
        pending &= ~frontier;
    }

    return 1;
}

static void init_topology_tables(void)
{
    int flat;
    int d;

    if (TOPOLOGY_READY)
    {
        return;
    }

    for (flat = 0; flat < BOARD_BITS; ++flat)
    {
        int q;
        int r;
        int s;
        recover_coords(flat, &q, &r, &s);
        for (d = 0; d < 6; ++d)
        {
            int nq = q + NEIGHBOR_QR_OFFSETS[d][0];
            int nr = r + NEIGHBOR_QR_OFFSETS[d][1];
            int nflat = flat_index(nq, nr);
            if ((unsigned int)nflat >= BOARD_BITS)
            {
                NEIGHBOR_FLATS[flat][d] = -1;
            }
            else
            {
                NEIGHBOR_FLATS[flat][d] = nflat;
            }
        }
    }

    for (flat = 0; flat < 64; ++flat)
    {
        int neighbor_count = popcount6((unsigned int)flat);
        if (neighbor_count < 2 || neighbor_count > 4)
        {
            LEGAL_NEIGHBOR_MASK[flat] = 0;
        }
        else if (neighbor_count <= 2)
        {
            LEGAL_NEIGHBOR_MASK[flat] = 1;
        }
        else
        {
            LEGAL_NEIGHBOR_MASK[flat] = (unsigned char)mask_connected_ring((unsigned int)flat);
        }
    }

    TOPOLOGY_READY = 1;
}

static void init_forbidden_masks(void)
{
    int flat;
    int p;
    int d;
    int i;

    if (FORBIDDEN_READY)
    {
        return;
    }

    memset(FORBIDDEN_MASKS, 0, sizeof(FORBIDDEN_MASKS));
    memset(FORBIDDEN_VALID, 0, sizeof(FORBIDDEN_VALID));

    for (flat = 0; flat < BOARD_BITS; ++flat)
    {
        for (p = 0; p < FORBIDDEN_PATTERN_COUNT; ++p)
        {
            int valid = 1;

            for (d = 0; d < FORBIDDEN_PATTERN_LEN[p]; ++d)
            {
                int n_flat = flat + NEIGHBOR_FLAT_OFFSETS[FORBIDDEN_PATTERN_DIRS[p][d]];
                if ((unsigned int)n_flat >= BOARD_BITS)
                {
                    valid = 0;
                    break;
                }
            }

            if (!valid)
            {
                continue;
            }

            FORBIDDEN_VALID[flat][p] = 1;
            for (d = 0; d < FORBIDDEN_PATTERN_LEN[p]; ++d)
            {
                int n_flat = flat + NEIGHBOR_FLAT_OFFSETS[FORBIDDEN_PATTERN_DIRS[p][d]];
                i = (unsigned int)n_flat >> BITS_PER_LONG_SHIFT;
                FORBIDDEN_MASKS[flat][p][i] |= (1ULL << (n_flat & BITS_PER_LONG_MASK));
            }
        }
    }

    FORBIDDEN_READY = 1;
    init_topology_tables();
}

static inline int has_forbidden_subset(const unsigned long long *all_tiles, int flat)
{
    int p;
    int i;

    for (p = 0; p < FORBIDDEN_PATTERN_COUNT; ++p)
    {
        if (!FORBIDDEN_VALID[flat][p])
        {
            continue;
        }

        for (i = 0; i < ARRAY_SIZE; ++i)
        {
            if ((all_tiles[i] & FORBIDDEN_MASKS[flat][p][i]) != FORBIDDEN_MASKS[flat][p][i])
            {
                break;
            }
        }

        if (i == ARRAY_SIZE)
        {
            return 1;
        }
    }

    return 0;
}

static int candidate_is_legal_for_tiles(const unsigned long long *all_tiles, int cflat)
{
    unsigned int mask = 0U;
    int d;

    if (!TOPOLOGY_READY)
    {
        init_topology_tables();
    }

    for (d = 0; d < 6; ++d)
    {
        int nflat = NEIGHBOR_FLATS[cflat][d];
        if (nflat >= 0 && check_bit_flat(all_tiles, nflat))
        {
            mask |= (1U << d);
        }
    }

    return LEGAL_NEIGHBOR_MASK[mask] != 0;
}

static void rebuild_tile_destination_cache(NonagaBitBoard *board)
{
    unsigned long long candidate_bits[ARRAY_SIZE];
    int i;

    memset(candidate_bits, 0, sizeof(candidate_bits));
    memset(board->tile_dest_candidates, 0, sizeof(board->tile_dest_candidates));

    for (i = 0; i < ARRAY_SIZE; ++i)
    {
        unsigned long long v = board->all_tiles[i];
        while (v)
        {
            int bit = ctz64_nonzero(v);
            int flat = i * BITS_PER_LONG + bit;
            int q;
            int r;
            int s;
            int d;

            v &= (v - 1ULL);
            recover_coords(flat, &q, &r, &s);

            for (d = 0; d < 6; ++d)
            {
                int cq = q + NEIGHBOR_QR_OFFSETS[d][0];
                int cr = r + NEIGHBOR_QR_OFFSETS[d][1];
                int cflat = flat_index(cq, cr);
                if ((unsigned int)cflat >= BOARD_BITS)
                {
                    continue;
                }
                if (check_bit_flat(board->all_tiles, cflat))
                {
                    continue;
                }
                set_bit_flat(candidate_bits, cflat);
            }
        }
    }

    for (i = 0; i < ARRAY_SIZE; ++i)
    {
        unsigned long long v = candidate_bits[i];
        while (v)
        {
            int bit = ctz64_nonzero(v);
            int cflat = i * BITS_PER_LONG + bit;
            v &= (v - 1ULL);

            if (candidate_is_legal_for_tiles(board->all_tiles, cflat))
            {
                set_bit_flat(board->tile_dest_candidates, cflat);
            }
        }
    }
}

static void update_tile_destination_cache_around_move(NonagaBitBoard *board, int from_flat, int to_flat)
{
    unsigned long long dirty[ARRAY_SIZE];
    int k;
    int i;

    memset(dirty, 0, sizeof(dirty));

    set_bit_flat(dirty, from_flat);
    set_bit_flat(dirty, to_flat);
    for (k = 0; k < 6; ++k)
    {
        set_bit_flat(dirty, from_flat + NEIGHBOR_FLAT_OFFSETS[k]);
        set_bit_flat(dirty, to_flat + NEIGHBOR_FLAT_OFFSETS[k]);
    }

    for (i = 0; i < ARRAY_SIZE; ++i)
    {
        unsigned long long v = dirty[i];
        while (v)
        {
            int bit = ctz64_nonzero(v);
            int cflat = i * BITS_PER_LONG + bit;
            v &= (v - 1ULL);

            clear_bit_flat(board->tile_dest_candidates, cflat);
            if (check_bit_flat(board->all_tiles, cflat))
            {
                continue;
            }
            if (candidate_is_legal_for_tiles(board->all_tiles, cflat))
            {
                set_bit_flat(board->tile_dest_candidates, cflat);
            }
        }
    }
}

static void refresh_all_tiles_cache(NonagaBitBoard *board)
{
    int i;

    for (i = 0; i < ARRAY_SIZE; ++i)
    {
        board->all_tiles[i] = board->movable_tiles[i] | board->unmovable_tiles[i];
    }
}

static inline void set_tile_class(NonagaBitBoard *board, int flat, int is_movable)
{
    clear_bit_flat(board->movable_tiles, flat);
    clear_bit_flat(board->unmovable_tiles, flat);
    if (is_movable)
    {
        set_bit_flat(board->movable_tiles, flat);
    }
    else
    {
        set_bit_flat(board->unmovable_tiles, flat);
    }
}

static void classify_tile(NonagaBitBoard *board, int flat)
{
    if (!check_bit_flat(board->all_tiles, flat))
    {
        return;
    }

    if (check_bit_flat(board->red_pieces, flat) || check_bit_flat(board->black_pieces, flat))
    {
        set_tile_class(board, flat, 0);
        return;
    }

    set_tile_class(board, flat, !has_forbidden_subset(board->all_tiles, flat));
}

static void recompute_all_tiles(NonagaBitBoard *board)
{
    int i;
    int flat;
    int bit;
    int has_piece;
    unsigned long long all_tiles_mask;

    unsigned long long new_movable[ARRAY_SIZE];
    unsigned long long new_unmovable[ARRAY_SIZE];
    memset(new_movable, 0, sizeof(new_movable));
    memset(new_unmovable, 0, sizeof(new_unmovable));

    refresh_all_tiles_cache(board);

    for (i = 0; i < ARRAY_SIZE; ++i)
    {
        all_tiles_mask = board->movable_tiles[i] | board->unmovable_tiles[i];
        if (all_tiles_mask == 0)
        {
            continue;
        }

        while (all_tiles_mask)
        {
            bit = ctz64_nonzero(all_tiles_mask);
            all_tiles_mask &= (all_tiles_mask - 1ULL);

            flat = i * BITS_PER_LONG + bit;
            has_piece = check_bit_flat(board->red_pieces, flat) || check_bit_flat(board->black_pieces, flat);
            if (has_piece)
            {
                set_bit_flat(new_unmovable, flat);
                continue;
            }

            if (has_forbidden_subset(board->all_tiles, flat))
            {
                set_bit_flat(new_unmovable, flat);
            }
            else
            {
                set_bit_flat(new_movable, flat);
            }
        }
    }

    for (i = 0; i < ARRAY_SIZE; ++i)
    {
        board->movable_tiles[i] = new_movable[i];
        board->unmovable_tiles[i] = new_unmovable[i];
    }

    refresh_all_tiles_cache(board);
    rebuild_tile_destination_cache(board);
}

static void update_tiles_around_move(NonagaBitBoard *board, int from_flat, int to_flat)
{
    int k;
    int i;
    int flat;
    int bit;
    unsigned long long dirty[ARRAY_SIZE];
    memset(dirty, 0, sizeof(dirty));

    set_bit_flat(dirty, from_flat);
    set_bit_flat(dirty, to_flat);

    for (k = 0; k < 6; ++k)
    {
        set_bit_flat(dirty, from_flat + NEIGHBOR_FLAT_OFFSETS[k]);
        set_bit_flat(dirty, to_flat + NEIGHBOR_FLAT_OFFSETS[k]);
    }

    for (i = 0; i < ARRAY_SIZE; ++i)
    {
        unsigned long long v = dirty[i];
        if (v == 0)
        {
            continue;
        }
        while (v)
        {
            bit = ctz64_nonzero(v);
            v &= (v - 1ULL);
            flat = i * BITS_PER_LONG + bit;
            classify_tile(board, flat);
        }
    }

    refresh_all_tiles_cache(board);
}

static void update_tiles_for_piece_move(NonagaBitBoard *board, int from_flat, int to_flat)
{
    if (check_bit_flat_safe(board->all_tiles, from_flat))
    {
        classify_tile(board, from_flat);
    }

    if (check_bit_flat_safe(board->all_tiles, to_flat))
    {
        set_tile_class(board, to_flat, 0);
    }

    refresh_all_tiles_cache(board);
}

void bitboard_initialize(NonagaBitBoard *board)
{
    int q;
    int r;
    int r_start;
    int r_end;
    int radius = 2;

    init_forbidden_masks();

    memset(board->red_pieces, 0, sizeof(board->red_pieces));
    memset(board->black_pieces, 0, sizeof(board->black_pieces));
    memset(board->movable_tiles, 0, sizeof(board->movable_tiles));
    memset(board->unmovable_tiles, 0, sizeof(board->unmovable_tiles));
    memset(board->all_tiles, 0, sizeof(board->all_tiles));
    memset(board->tile_dest_candidates, 0, sizeof(board->tile_dest_candidates));

    for (q = -radius; q <= radius; ++q)
    {
        r_start = (-q - radius < -radius) ? -radius : (-q - radius);
        r_end = (-q + radius > radius) ? radius : (-q + radius);
        for (r = r_start; r <= r_end; ++r)
        {
            set_bit(board->movable_tiles, q, r);
        }
    }

    set_bit(board->red_pieces, -2, 0);
    set_bit(board->black_pieces, -2, 2);
    set_bit(board->red_pieces, 0, 2);
    set_bit(board->black_pieces, 2, 0);
    set_bit(board->red_pieces, 2, -2);
    set_bit(board->black_pieces, 0, -2);

    recompute_all_tiles(board);
}

int bitboard_get_number_of_tiles(NonagaBitBoard *board)
{
    int i;
    int count = 0;
    unsigned long long v;

    for (i = 0; i < ARRAY_SIZE; ++i)
    {
        v = board->movable_tiles[i] | board->unmovable_tiles[i];
        while (v)
        {
            v &= (v - 1ULL);
            ++count;
        }
    }
    return count;
}

int bitboard_get_all_tiles(NonagaBitBoard *board, int *out_q, int *out_r, int *out_s, int max_count)
{
    int i;
    int bit;
    int q;
    int r;
    int s;
    int count = 0;
    unsigned long long v;

    for (i = 0; i < ARRAY_SIZE; ++i)
    {
        v = board->movable_tiles[i] | board->unmovable_tiles[i];
        while (v)
        {
            bit = ctz64_nonzero(v);
            v &= (v - 1ULL);
            if (count >= max_count)
            {
                return count;
            }
            recover_coords(i * BITS_PER_LONG + bit, &q, &r, &s);
            out_q[count] = q;
            out_r[count] = r;
            out_s[count] = s;
            ++count;
        }
    }

    return count;
}

int bitboard_get_movable_tiles(NonagaBitBoard *board, int *out_q, int *out_r, int *out_s, int max_count)
{
    int i;
    int bit;
    int q;
    int r;
    int s;
    int count = 0;
    unsigned long long v;

    for (i = 0; i < ARRAY_SIZE; ++i)
    {
        v = board->movable_tiles[i];
        while (v)
        {
            bit = ctz64_nonzero(v);
            v &= (v - 1ULL);
            if (count >= max_count)
            {
                return count;
            }
            recover_coords(i * BITS_PER_LONG + bit, &q, &r, &s);
            out_q[count] = q;
            out_r[count] = r;
            out_s[count] = s;
            ++count;
        }
    }

    return count;
}

int bitboard_get_valid_tile_positions_for_tile(
    NonagaBitBoard *board,
    int tile_q,
    int tile_r,
    int tile_s,
    int *out_q,
    int *out_r,
    int *out_s,
    int max_count)
{
    int tile_flat = flat_index(tile_q, tile_r);
    unsigned long long base_tiles[ARRAY_SIZE];
    unsigned long long affected_candidates[ARRAY_SIZE];
    unsigned long long emitted[ARRAY_SIZE];
    int i;
    int valid_count = 0;
    int d;

    (void)tile_s;

    if ((unsigned int)tile_flat >= BOARD_BITS)
    {
        return 0;
    }

    if (!check_bit_flat(board->all_tiles, tile_flat))
    {
        return 0;
    }

    for (i = 0; i < ARRAY_SIZE; ++i)
    {
        base_tiles[i] = board->all_tiles[i];
        affected_candidates[i] = 0ULL;
        emitted[i] = 0ULL;
    }
    clear_bit_flat(base_tiles, tile_flat);

    for (d = 0; d < 6; ++d)
    {
        set_bit_flat(affected_candidates, tile_flat + NEIGHBOR_FLAT_OFFSETS[d]);
    }

    for (i = 0; i < ARRAY_SIZE; ++i)
    {
        unsigned long long v = board->tile_dest_candidates[i] & ~affected_candidates[i];
        while (v)
        {
            int bit = ctz64_nonzero(v);
            int cflat = i * BITS_PER_LONG + bit;
            int cq;
            int cr;
            int cs;

            v &= (v - 1ULL);

            if (check_bit_flat(base_tiles, cflat))
            {
                continue;
            }
            if (cflat == tile_flat)
            {
                continue;
            }

            recover_coords(cflat, &cq, &cr, &cs);

            if (valid_count < max_count)
            {
                out_q[valid_count] = cq;
                out_r[valid_count] = cr;
                out_s[valid_count] = cs;
                valid_count += 1;
            }
            set_bit_flat(emitted, cflat);
        }
    }

    for (i = 0; i < ARRAY_SIZE; ++i)
    {
        unsigned long long v = affected_candidates[i];
        while (v)
        {
            int bit = ctz64_nonzero(v);
            int cflat = i * BITS_PER_LONG + bit;
            int cq;
            int cr;
            int cs;

            v &= (v - 1ULL);

            if (check_bit_flat(emitted, cflat))
            {
                continue;
            }
            if (check_bit_flat(base_tiles, cflat))
            {
                continue;
            }

            if (cflat == tile_flat)
            {
                continue;
            }
            if (!candidate_is_legal_for_tiles(base_tiles, cflat))
            {
                continue;
            }

            recover_coords(cflat, &cq, &cr, &cs);

            if (valid_count < max_count)
            {
                out_q[valid_count] = cq;
                out_r[valid_count] = cr;
                out_s[valid_count] = cs;
                valid_count += 1;
            }
        }
    }

    return valid_count;
}

int bitboard_is_there_tile(NonagaBitBoard *board, int q, int r)
{
    int flat = flat_index(q, r);
    return check_bit_flat_safe(board->all_tiles, flat);
}

int bitboard_has_tile(NonagaBitBoard *board, int q, int r)
{
    int flat = flat_index(q, r);
    return check_bit_flat_safe(board->all_tiles, flat);
}

int bitboard_is_there_piece(NonagaBitBoard *board, int q, int r)
{
    int flat = flat_index(q, r);
    return check_bit_flat_safe(board->red_pieces, flat) || check_bit_flat_safe(board->black_pieces, flat);
}

int bitboard_get_color(NonagaBitBoard *board, int q, int r)
{
    int flat = flat_index(q, r);
    if (check_bit_flat_safe(board->red_pieces, flat))
    {
        return RED;
    }
    if (check_bit_flat_safe(board->black_pieces, flat))
    {
        return BLACK;
    }
    return -1;
}

int bitboard_get_pieces(NonagaBitBoard *board, int color, int *out_q, int *out_r, int *out_s)
{
    int i;
    int bit;
    int q;
    int r;
    int s;
    int count = 0;
    unsigned long long v;
    int get_red = (color == RED || color < 0);
    int get_black = (color == BLACK || color < 0);

    for (i = 0; i < ARRAY_SIZE; ++i)
    {
        v = 0;
        if (get_red)
        {
            v |= board->red_pieces[i];
        }
        if (get_black)
        {
            v |= board->black_pieces[i];
        }

        while (v)
        {
            bit = ctz64_nonzero(v);
            v &= (v - 1ULL);
            recover_coords(i * BITS_PER_LONG + bit, &q, &r, &s);
            out_q[count] = q;
            out_r[count] = r;
            out_s[count] = s;
            ++count;
        }
    }

    return count;
}

void bitboard_move_tile(NonagaBitBoard *board, int current_q, int current_r, int new_q, int new_r)
{
    int from_flat = flat_index(current_q, current_r);
    int to_flat = flat_index(new_q, new_r);

    clear_bit(board->movable_tiles, current_q, current_r);
    clear_bit(board->unmovable_tiles, current_q, current_r);
    set_bit(board->movable_tiles, new_q, new_r);

    clear_bit_flat(board->all_tiles, from_flat);
    set_bit_flat(board->all_tiles, to_flat);

    if (check_bit(board->red_pieces, current_q, current_r))
    {
        clear_bit(board->red_pieces, current_q, current_r);
        set_bit(board->red_pieces, new_q, new_r);
    }
    else if (check_bit(board->black_pieces, current_q, current_r))
    {
        clear_bit(board->black_pieces, current_q, current_r);
        set_bit(board->black_pieces, new_q, new_r);
    }

    update_tiles_around_move(board, from_flat, to_flat);
    update_tile_destination_cache_around_move(board, from_flat, to_flat);
}

void bitboard_move_piece(NonagaBitBoard *board, int current_q, int current_r, int new_q, int new_r)
{
    int from_flat = flat_index(current_q, current_r);
    int to_flat = flat_index(new_q, new_r);

    if (check_bit(board->red_pieces, current_q, current_r))
    {
        clear_bit(board->red_pieces, current_q, current_r);
        set_bit(board->red_pieces, new_q, new_r);
    }
    else if (check_bit(board->black_pieces, current_q, current_r))
    {
        clear_bit(board->black_pieces, current_q, current_r);
        set_bit(board->black_pieces, new_q, new_r);
    }

    update_tiles_for_piece_move(board, from_flat, to_flat);
}
