#include "nonaga_bitboard.h"

#include <string.h>

#define RED 0
#define BLACK 1

#define BOARD_OFFSET 10
#define BOARD_WIDTH 21
#define ARRAY_SIZE 7
#define BITS_PER_LONG 64
#define BOARD_BITS 448

static const int NEIGHBOR_FLAT_OFFSETS[6] = {-20, 1, 21, 20, -1, -21};

static inline int flat_index(int q, int r) {
    return (q + BOARD_OFFSET) + (r + BOARD_OFFSET) * BOARD_WIDTH;
}

static inline void set_bit(unsigned long long* bitboard, int q, int r) {
    int flat = flat_index(q, r);
    if (flat < 0 || flat >= BOARD_BITS) {
        return;
    }
    bitboard[flat / BITS_PER_LONG] |= (1ULL << (flat % BITS_PER_LONG));
}

static inline void clear_bit(unsigned long long* bitboard, int q, int r) {
    int flat = flat_index(q, r);
    if (flat < 0 || flat >= BOARD_BITS) {
        return;
    }
    bitboard[flat / BITS_PER_LONG] &= ~(1ULL << (flat % BITS_PER_LONG));
}

static inline void set_bit_flat(unsigned long long* bitboard, int flat) {
    if (flat < 0 || flat >= BOARD_BITS) {
        return;
    }
    bitboard[flat / BITS_PER_LONG] |= (1ULL << (flat % BITS_PER_LONG));
}

static inline void clear_bit_flat(unsigned long long* bitboard, int flat) {
    if (flat < 0 || flat >= BOARD_BITS) {
        return;
    }
    bitboard[flat / BITS_PER_LONG] &= ~(1ULL << (flat % BITS_PER_LONG));
}

static inline int check_bit_flat(const unsigned long long* bitboard, int flat) {
    if (flat < 0 || flat >= BOARD_BITS) {
        return 0;
    }
    return (bitboard[flat / BITS_PER_LONG] & (1ULL << (flat % BITS_PER_LONG))) != 0;
}

static inline int check_bit(const unsigned long long* bitboard, int q, int r) {
    return check_bit_flat(bitboard, flat_index(q, r));
}

static inline void recover_coords(int flat, int* q, int* r, int* s) {
    int r_shifted = flat / BOARD_WIDTH;
    int q_shifted = flat % BOARD_WIDTH;
    *q = q_shifted - BOARD_OFFSET;
    *r = r_shifted - BOARD_OFFSET;
    *s = -(*q) - (*r);
}

static int check_neighbor_constraints(int mask, int count) {
    int transitions = 0;
    int prev = (mask >> 5) & 1;
    int curr;
    int k;

    for (k = 0; k < 6; ++k) {
        curr = (mask >> k) & 1;
        if (curr && !prev) {
            ++transitions;
        }
        prev = curr;
    }

    if (transitions == 1) {
        return 1;
    }

    if (count == 3 && transitions == 2) {
        return 1;
    }

    return 0;
}

static inline int has_tile_flat(const NonagaBitBoard* board, int flat) {
    return check_bit_flat(board->movable_tiles, flat) || check_bit_flat(board->unmovable_tiles, flat);
}

static inline void set_tile_class(NonagaBitBoard* board, int flat, int is_movable) {
    clear_bit_flat(board->movable_tiles, flat);
    clear_bit_flat(board->unmovable_tiles, flat);
    if (is_movable) {
        set_bit_flat(board->movable_tiles, flat);
    } else {
        set_bit_flat(board->unmovable_tiles, flat);
    }
}

static void classify_tile(NonagaBitBoard* board, int flat) {
    int k;
    int n_idx;
    int neighbor_count = 0;
    int neighbor_mask = 0;

    if (!has_tile_flat(board, flat)) {
        return;
    }

    if (check_bit_flat(board->red_pieces, flat) || check_bit_flat(board->black_pieces, flat)) {
        set_tile_class(board, flat, 0);
        return;
    }

    for (k = 0; k < 6; ++k) {
        n_idx = flat + NEIGHBOR_FLAT_OFFSETS[k];
        if (has_tile_flat(board, n_idx)) {
            neighbor_mask |= (1 << k);
            ++neighbor_count;
        }
    }

    if (neighbor_count >= 5) {
        set_tile_class(board, flat, 0);
    } else if (neighbor_count <= 2) {
        set_tile_class(board, flat, 1);
    } else if (check_neighbor_constraints(neighbor_mask, neighbor_count)) {
        set_tile_class(board, flat, 1);
    } else {
        set_tile_class(board, flat, 0);
    }
}

static void recompute_all_tiles(NonagaBitBoard* board) {
    int i;
    int j;
    int k;
    int flat;
    int neighbor_mask;
    int neighbor_count;
    int n_idx;
    int has_piece;
    unsigned long long all_tiles_mask;

    unsigned long long new_movable[ARRAY_SIZE];
    unsigned long long new_unmovable[ARRAY_SIZE];
    memset(new_movable, 0, sizeof(new_movable));
    memset(new_unmovable, 0, sizeof(new_unmovable));

    for (i = 0; i < ARRAY_SIZE; ++i) {
        all_tiles_mask = board->movable_tiles[i] | board->unmovable_tiles[i];
        if (all_tiles_mask == 0) {
            continue;
        }

        for (j = 0; j < BITS_PER_LONG; ++j) {
            if ((all_tiles_mask & (1ULL << j)) == 0) {
                continue;
            }

            flat = i * BITS_PER_LONG + j;
            has_piece = check_bit_flat(board->red_pieces, flat) || check_bit_flat(board->black_pieces, flat);
            if (has_piece) {
                set_bit_flat(new_unmovable, flat);
                continue;
            }

            neighbor_count = 0;
            neighbor_mask = 0;
            for (k = 0; k < 6; ++k) {
                n_idx = flat + NEIGHBOR_FLAT_OFFSETS[k];
                if (check_bit_flat(board->movable_tiles, n_idx) || check_bit_flat(board->unmovable_tiles, n_idx)) {
                    neighbor_mask |= (1 << k);
                    ++neighbor_count;
                }
            }

            if (neighbor_count >= 5) {
                set_bit_flat(new_unmovable, flat);
            } else if (neighbor_count <= 2) {
                set_bit_flat(new_movable, flat);
            } else if (check_neighbor_constraints(neighbor_mask, neighbor_count)) {
                set_bit_flat(new_movable, flat);
            } else {
                set_bit_flat(new_unmovable, flat);
            }
        }
    }

    for (i = 0; i < ARRAY_SIZE; ++i) {
        board->movable_tiles[i] = new_movable[i];
        board->unmovable_tiles[i] = new_unmovable[i];
    }
}

static void update_tiles_around_move(NonagaBitBoard* board, int from_flat, int to_flat) {
    int k;
    int i;
    int j;
    int flat;
    unsigned long long dirty[ARRAY_SIZE];
    memset(dirty, 0, sizeof(dirty));

    set_bit_flat(dirty, from_flat);
    set_bit_flat(dirty, to_flat);

    for (k = 0; k < 6; ++k) {
        set_bit_flat(dirty, from_flat + NEIGHBOR_FLAT_OFFSETS[k]);
        set_bit_flat(dirty, to_flat + NEIGHBOR_FLAT_OFFSETS[k]);
    }

    for (i = 0; i < ARRAY_SIZE; ++i) {
        if (dirty[i] == 0) {
            continue;
        }
        for (j = 0; j < BITS_PER_LONG; ++j) {
            if ((dirty[i] & (1ULL << j)) == 0) {
                continue;
            }
            flat = i * BITS_PER_LONG + j;
            classify_tile(board, flat);
        }
    }
}

static void update_tiles_for_piece_move(NonagaBitBoard* board, int from_flat, int to_flat) {
    if (has_tile_flat(board, from_flat)) {
        classify_tile(board, from_flat);
    }

    if (has_tile_flat(board, to_flat)) {
        set_tile_class(board, to_flat, 0);
    }
}

void bitboard_initialize(NonagaBitBoard* board) {
    int q;
    int r;
    int r_start;
    int r_end;
    int radius = 2;

    memset(board->red_pieces, 0, sizeof(board->red_pieces));
    memset(board->black_pieces, 0, sizeof(board->black_pieces));
    memset(board->movable_tiles, 0, sizeof(board->movable_tiles));
    memset(board->unmovable_tiles, 0, sizeof(board->unmovable_tiles));

    for (q = -radius; q <= radius; ++q) {
        r_start = (-q - radius < -radius) ? -radius : (-q - radius);
        r_end = (-q + radius > radius) ? radius : (-q + radius);
        for (r = r_start; r <= r_end; ++r) {
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

int bitboard_get_number_of_tiles(NonagaBitBoard* board) {
    int i;
    int count = 0;
    unsigned long long v;

    for (i = 0; i < ARRAY_SIZE; ++i) {
        v = board->movable_tiles[i] | board->unmovable_tiles[i];
        while (v) {
            v &= (v - 1ULL);
            ++count;
        }
    }
    return count;
}

int bitboard_get_all_tiles(NonagaBitBoard* board, int* out_q, int* out_r, int* out_s, int max_count) {
    int i;
    int j;
    int q;
    int r;
    int s;
    int count = 0;
    unsigned long long v;

    for (i = 0; i < ARRAY_SIZE; ++i) {
        v = board->movable_tiles[i] | board->unmovable_tiles[i];
        if (v == 0) {
            continue;
        }
        for (j = 0; j < BITS_PER_LONG; ++j) {
            if ((v & (1ULL << j)) == 0) {
                continue;
            }
            if (count >= max_count) {
                return count;
            }
            recover_coords(i * BITS_PER_LONG + j, &q, &r, &s);
            out_q[count] = q;
            out_r[count] = r;
            out_s[count] = s;
            ++count;
        }
    }

    return count;
}

int bitboard_get_movable_tiles(NonagaBitBoard* board, int* out_q, int* out_r, int* out_s, int max_count) {
    int i;
    int j;
    int q;
    int r;
    int s;
    int count = 0;
    unsigned long long v;

    for (i = 0; i < ARRAY_SIZE; ++i) {
        v = board->movable_tiles[i];
        if (v == 0) {
            continue;
        }
        for (j = 0; j < BITS_PER_LONG; ++j) {
            if ((v & (1ULL << j)) == 0) {
                continue;
            }
            if (count >= max_count) {
                return count;
            }
            recover_coords(i * BITS_PER_LONG + j, &q, &r, &s);
            out_q[count] = q;
            out_r[count] = r;
            out_s[count] = s;
            ++count;
        }
    }

    return count;
}

int bitboard_is_there_tile(NonagaBitBoard* board, int q, int r) {
    int flat = flat_index(q, r);
    return check_bit_flat(board->movable_tiles, flat) || check_bit_flat(board->unmovable_tiles, flat);
}

int bitboard_has_tile(NonagaBitBoard* board, int q, int r) {
    int flat = flat_index(q, r);
    return check_bit_flat(board->movable_tiles, flat) || check_bit_flat(board->unmovable_tiles, flat);
}

int bitboard_is_there_piece(NonagaBitBoard* board, int q, int r) {
    int flat = flat_index(q, r);
    return check_bit_flat(board->red_pieces, flat) || check_bit_flat(board->black_pieces, flat);
}

int bitboard_get_color(NonagaBitBoard* board, int q, int r) {
    int flat = flat_index(q, r);
    if (check_bit_flat(board->red_pieces, flat)) {
        return RED;
    }
    if (check_bit_flat(board->black_pieces, flat)) {
        return BLACK;
    }
    return -1;
}

int bitboard_get_pieces(NonagaBitBoard* board, int color, int* out_q, int* out_r, int* out_s) {
    int i;
    int j;
    int q;
    int r;
    int s;
    int count = 0;
    unsigned long long v;
    int get_red = (color == RED || color < 0);
    int get_black = (color == BLACK || color < 0);

    for (i = 0; i < ARRAY_SIZE; ++i) {
        v = 0;
        if (get_red) {
            v |= board->red_pieces[i];
        }
        if (get_black) {
            v |= board->black_pieces[i];
        }

        if (v == 0) {
            continue;
        }

        for (j = 0; j < BITS_PER_LONG; ++j) {
            if ((v & (1ULL << j)) == 0) {
                continue;
            }
            recover_coords(i * BITS_PER_LONG + j, &q, &r, &s);
            out_q[count] = q;
            out_r[count] = r;
            out_s[count] = s;
            ++count;
        }
    }

    return count;
}

void bitboard_move_tile(NonagaBitBoard* board, int current_q, int current_r, int new_q, int new_r) {
    int from_flat = flat_index(current_q, current_r);
    int to_flat = flat_index(new_q, new_r);

    clear_bit(board->movable_tiles, current_q, current_r);
    clear_bit(board->unmovable_tiles, current_q, current_r);
    set_bit(board->movable_tiles, new_q, new_r);

    if (check_bit(board->red_pieces, current_q, current_r)) {
        clear_bit(board->red_pieces, current_q, current_r);
        set_bit(board->red_pieces, new_q, new_r);
    } else if (check_bit(board->black_pieces, current_q, current_r)) {
        clear_bit(board->black_pieces, current_q, current_r);
        set_bit(board->black_pieces, new_q, new_r);
    }

    update_tiles_around_move(board, from_flat, to_flat);
}

void bitboard_move_piece(NonagaBitBoard* board, int current_q, int current_r, int new_q, int new_r) {
    int from_flat = flat_index(current_q, current_r);
    int to_flat = flat_index(new_q, new_r);

    if (check_bit(board->red_pieces, current_q, current_r)) {
        clear_bit(board->red_pieces, current_q, current_r);
        set_bit(board->red_pieces, new_q, new_r);
    } else if (check_bit(board->black_pieces, current_q, current_r)) {
        clear_bit(board->black_pieces, current_q, current_r);
        set_bit(board->black_pieces, new_q, new_r);
    }

    update_tiles_for_piece_move(board, from_flat, to_flat);
}
