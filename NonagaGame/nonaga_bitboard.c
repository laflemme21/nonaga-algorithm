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

static inline int popcount6(int mask)
{
#if defined(_MSC_VER)
    return (int)__popcnt((unsigned int)mask) & 0x7;
#else
    return __builtin_popcount((unsigned int)mask) & 0x7;
#endif
}

static inline int check_neighbor_constraints(int mask, int count)
{
    int transitions = 0;
    int prev = (mask >> 5) & 1;
    int curr;
    int k;

    for (k = 0; k < 6; ++k)
    {
        curr = (mask >> k) & 1;
        if (curr && !prev)
        {
            ++transitions;
        }
        prev = curr;
    }

    if (transitions == 1)
    {
        return 1;
    }

    if (count == 3 && transitions == 2)
    {
        return 1;
    }

    return 0;
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
    int flat;
    int p;
    int d;
    int i;

    if (!check_bit_flat(board->all_tiles, flat))
    {
        return;
    }

    if (check_bit_flat(board->red_pieces, flat) || check_bit_flat(board->black_pieces, flat))
    {
        set_tile_class(board, flat, 0);
        return;
    }

    for (k = 0; k < 6; ++k)
    {
        set_tile_class(board, flat, !has_forbidden_subset(board->all_tiles, flat));
    }

    static void recompute_all_tiles(NonagaBitBoard * board)
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
