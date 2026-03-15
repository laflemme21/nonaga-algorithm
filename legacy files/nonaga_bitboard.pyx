# cython: language_level=3, boundscheck=False, wraparound=False, cdivision=True, profile=True
from libc.string cimport memset

cdef int RED = 0
cdef int BLACK = 1

cdef int BOARD_OFFSET = 10
cdef int BOARD_WIDTH = 21
cdef int ARRAY_SIZE = 7
cdef int BITS_PER_LONG = 64
cdef int BOARD_BITS = 448

cdef int[6] NEIGHBOR_FLAT_OFFSETS = [-20, 1, 21, 20, -1, -21]


cdef inline int _flat_index(int q, int r):
    return (q + BOARD_OFFSET) + (r + BOARD_OFFSET) * BOARD_WIDTH


cdef inline void _set_bit(unsigned long long* bitboard, int q, int r):
    cdef int flat = _flat_index(q, r)
    if flat < 0 or flat >= BOARD_BITS:
        return
    bitboard[flat // BITS_PER_LONG] |= (1ULL << (flat % BITS_PER_LONG))


cdef inline void _clear_bit(unsigned long long* bitboard, int q, int r):
    cdef int flat = _flat_index(q, r)
    if flat < 0 or flat >= BOARD_BITS:
        return
    bitboard[flat // BITS_PER_LONG] &= ~(1ULL << (flat % BITS_PER_LONG))


cdef inline void _set_bit_flat(unsigned long long* bitboard, int flat):
    if flat < 0 or flat >= BOARD_BITS:
        return
    bitboard[flat // BITS_PER_LONG] |= (1ULL << (flat % BITS_PER_LONG))


cdef inline void _clear_bit_flat(unsigned long long* bitboard, int flat):
    if flat < 0 or flat >= BOARD_BITS:
        return
    bitboard[flat // BITS_PER_LONG] &= ~(1ULL << (flat % BITS_PER_LONG))


cdef inline bint _check_bit_flat(unsigned long long* bitboard, int flat):
    if flat < 0 or flat >= BOARD_BITS:
        return False
    return (bitboard[flat // BITS_PER_LONG] & (1ULL << (flat % BITS_PER_LONG))) != 0


cdef inline bint _check_bit(unsigned long long* bitboard, int q, int r):
    return _check_bit_flat(bitboard, _flat_index(q, r))


cdef inline void _recover_coords(int flat, int* q, int* r, int* s):
    cdef int r_shifted = flat // BOARD_WIDTH
    cdef int q_shifted = flat % BOARD_WIDTH
    q[0] = q_shifted - BOARD_OFFSET
    r[0] = r_shifted - BOARD_OFFSET
    s[0] = -q[0] - r[0]


cdef bint _check_neighbor_constraints(int mask, int count):
    cdef int transitions = 0
    cdef int k
    cdef int prev = (mask >> 5) & 1
    cdef int curr

    for k in range(6):
        curr = (mask >> k) & 1
        if curr and not prev:
            transitions += 1
        prev = curr

    if transitions == 1:
        return True

    if count == 3 and transitions == 2:
        return True

    return False


cdef inline bint _has_tile_flat(NonagaBitBoard* board, int flat):
    return _check_bit_flat(board.movable_tiles, flat) or _check_bit_flat(board.unmovable_tiles, flat)


cdef inline void _set_tile_class(NonagaBitBoard* board, int flat, bint is_movable):
    _clear_bit_flat(board.movable_tiles, flat)
    _clear_bit_flat(board.unmovable_tiles, flat)
    if is_movable:
        _set_bit_flat(board.movable_tiles, flat)
    else:
        _set_bit_flat(board.unmovable_tiles, flat)


cdef void _classify_tile(NonagaBitBoard* board, int flat):
    cdef int k
    cdef int n_idx
    cdef int neighbor_count = 0
    cdef int neighbor_mask = 0

    if not _has_tile_flat(board, flat):
        return

    if _check_bit_flat(board.red_pieces, flat) or _check_bit_flat(board.black_pieces, flat):
        _set_tile_class(board, flat, False)
        return

    for k in range(6):
        n_idx = flat + NEIGHBOR_FLAT_OFFSETS[k]
        if _has_tile_flat(board, n_idx):
            neighbor_mask |= (1 << k)
            neighbor_count += 1

    if neighbor_count >= 5:
        _set_tile_class(board, flat, False)
    elif neighbor_count <= 2:
        _set_tile_class(board, flat, True)
    elif _check_neighbor_constraints(neighbor_mask, neighbor_count):
        _set_tile_class(board, flat, True)
    else:
        _set_tile_class(board, flat, False)


cdef void _recompute_all_tiles(NonagaBitBoard* board):
    cdef int i
    cdef int j
    cdef int k
    cdef int flat
    cdef int neighbor_mask
    cdef int neighbor_count
    cdef int n_idx
    cdef bint has_piece
    cdef unsigned long long all_tiles_mask

    cdef unsigned long long new_movable[7]
    cdef unsigned long long new_unmovable[7]
    memset(new_movable, 0, sizeof(new_movable))
    memset(new_unmovable, 0, sizeof(new_unmovable))

    for i in range(ARRAY_SIZE):
        all_tiles_mask = board.movable_tiles[i] | board.unmovable_tiles[i]
        if all_tiles_mask == 0:
            continue

        for j in range(BITS_PER_LONG):
            if (all_tiles_mask & (1ULL << j)) == 0:
                continue

            flat = i * 64 + j
            has_piece = _check_bit_flat(board.red_pieces, flat) or _check_bit_flat(board.black_pieces, flat)
            if has_piece:
                _set_bit_flat(new_unmovable, flat)
                continue

            neighbor_count = 0
            neighbor_mask = 0
            for k in range(6):
                n_idx = flat + NEIGHBOR_FLAT_OFFSETS[k]
                if _check_bit_flat(board.movable_tiles, n_idx) or _check_bit_flat(board.unmovable_tiles, n_idx):
                    neighbor_mask |= (1 << k)
                    neighbor_count += 1

            if neighbor_count >= 5:
                _set_bit_flat(new_unmovable, flat)
            elif neighbor_count <= 2:
                _set_bit_flat(new_movable, flat)
            elif _check_neighbor_constraints(neighbor_mask, neighbor_count):
                _set_bit_flat(new_movable, flat)
            else:
                _set_bit_flat(new_unmovable, flat)

    for i in range(ARRAY_SIZE):
        board.movable_tiles[i] = new_movable[i]
        board.unmovable_tiles[i] = new_unmovable[i]


cdef void bitboard_initialize(NonagaBitBoard* board):
    cdef int q
    cdef int r
    cdef int r_start
    cdef int r_end
    cdef int radius = 2

    memset(board.red_pieces, 0, sizeof(board.red_pieces))
    memset(board.black_pieces, 0, sizeof(board.black_pieces))
    memset(board.movable_tiles, 0, sizeof(board.movable_tiles))
    memset(board.unmovable_tiles, 0, sizeof(board.unmovable_tiles))

    for q in range(-radius, radius + 1):
        r_start = -radius if -q - radius < -radius else -q - radius
        r_end = radius if -q + radius > radius else -q + radius
        for r in range(r_start, r_end + 1):
            _set_bit(board.movable_tiles, q, r)

    _set_bit(board.red_pieces, -2, 0)
    _set_bit(board.black_pieces, -2, 2)
    _set_bit(board.red_pieces, 0, 2)
    _set_bit(board.black_pieces, 2, 0)
    _set_bit(board.red_pieces, 2, -2)
    _set_bit(board.black_pieces, 0, -2)

    _recompute_all_tiles(board)


cdef void _update_tiles_around_move(NonagaBitBoard* board, int from_flat, int to_flat):
    cdef int k
    cdef int i
    cdef int j
    cdef int flat
    cdef unsigned long long dirty[7]
    memset(dirty, 0, sizeof(dirty))

    _set_bit_flat(dirty, from_flat)
    _set_bit_flat(dirty, to_flat)

    for k in range(6):
        _set_bit_flat(dirty, from_flat + NEIGHBOR_FLAT_OFFSETS[k])
        _set_bit_flat(dirty, to_flat + NEIGHBOR_FLAT_OFFSETS[k])

    for i in range(ARRAY_SIZE):
        if dirty[i] == 0:
            continue
        for j in range(BITS_PER_LONG):
            if (dirty[i] & (1ULL << j)) == 0:
                continue
            flat = i * 64 + j
            _classify_tile(board, flat)


cdef void _update_tiles_for_piece_move(NonagaBitBoard* board, int from_flat, int to_flat):
    if _has_tile_flat(board, from_flat):
        _classify_tile(board, from_flat)

    if _has_tile_flat(board, to_flat):
        _set_tile_class(board, to_flat, False)


cdef int bitboard_get_number_of_tiles(NonagaBitBoard* board):
    cdef int i
    cdef int count = 0
    cdef unsigned long long v

    for i in range(ARRAY_SIZE):
        v = board.movable_tiles[i] | board.unmovable_tiles[i]
        while v:
            v &= (v - 1)
            count += 1
    return count


cdef int bitboard_get_all_tiles(NonagaBitBoard* board, int* out_q, int* out_r, int* out_s, int max_count):
    cdef int i
    cdef int j
    cdef int q
    cdef int r
    cdef int s
    cdef int count = 0
    cdef unsigned long long v

    for i in range(ARRAY_SIZE):
        v = board.movable_tiles[i] | board.unmovable_tiles[i]
        if v == 0:
            continue
        for j in range(BITS_PER_LONG):
            if (v & (1ULL << j)) == 0:
                continue
            if count >= max_count:
                return count
            _recover_coords(i * 64 + j, &q, &r, &s)
            out_q[count] = q
            out_r[count] = r
            out_s[count] = s
            count += 1

    return count


cdef int bitboard_get_movable_tiles(NonagaBitBoard* board, int* out_q, int* out_r, int* out_s, int max_count):
    cdef int i
    cdef int j
    cdef int q
    cdef int r
    cdef int s
    cdef int count = 0
    cdef unsigned long long v

    for i in range(ARRAY_SIZE):
        v = board.movable_tiles[i]
        if v == 0:
            continue
        for j in range(BITS_PER_LONG):
            if (v & (1ULL << j)) == 0:
                continue
            if count >= max_count:
                return count
            _recover_coords(i * 64 + j, &q, &r, &s)
            out_q[count] = q
            out_r[count] = r
            out_s[count] = s
            count += 1

    return count


cdef bint bitboard_is_there_tile(NonagaBitBoard* board, int q, int r):
    cdef int flat = _flat_index(q, r)
    return _check_bit_flat(board.movable_tiles, flat) or _check_bit_flat(board.unmovable_tiles, flat)


cdef bint bitboard_has_tile(NonagaBitBoard* board, int q, int r):
    cdef int flat = _flat_index(q, r)
    return _check_bit_flat(board.movable_tiles, flat) or _check_bit_flat(board.unmovable_tiles, flat)


cdef bint bitboard_is_there_piece(NonagaBitBoard* board, int q, int r):
    cdef int flat = _flat_index(q, r)
    return _check_bit_flat(board.red_pieces, flat) or _check_bit_flat(board.black_pieces, flat)


cdef int bitboard_get_color(NonagaBitBoard* board, int q, int r):
    cdef int flat = _flat_index(q, r)
    if _check_bit_flat(board.red_pieces, flat):
        return RED
    if _check_bit_flat(board.black_pieces, flat):
        return BLACK
    return -1


cdef int bitboard_get_pieces(NonagaBitBoard* board, int color, int* out_q, int* out_r, int* out_s):
    cdef int i
    cdef int j
    cdef int q
    cdef int r
    cdef int s
    cdef int count = 0
    cdef unsigned long long v
    cdef bint get_red = (color == RED or color < 0)
    cdef bint get_black = (color == BLACK or color < 0)

    for i in range(ARRAY_SIZE):
        v = 0
        if get_red:
            v |= board.red_pieces[i]
        if get_black:
            v |= board.black_pieces[i]

        if v == 0:
            continue

        for j in range(BITS_PER_LONG):
            if (v & (1ULL << j)) == 0:
                continue
            _recover_coords(i * 64 + j, &q, &r, &s)
            out_q[count] = q
            out_r[count] = r
            out_s[count] = s
            count += 1

    return count


cdef void bitboard_move_tile(NonagaBitBoard* board, int current_q, int current_r, int new_q, int new_r):
    cdef int from_flat = _flat_index(current_q, current_r)
    cdef int to_flat = _flat_index(new_q, new_r)

    _clear_bit(board.movable_tiles, current_q, current_r)
    _clear_bit(board.unmovable_tiles, current_q, current_r)
    _set_bit(board.movable_tiles, new_q, new_r)

    if _check_bit(board.red_pieces, current_q, current_r):
        _clear_bit(board.red_pieces, current_q, current_r)
        _set_bit(board.red_pieces, new_q, new_r)
    elif _check_bit(board.black_pieces, current_q, current_r):
        _clear_bit(board.black_pieces, current_q, current_r)
        _set_bit(board.black_pieces, new_q, new_r)

    _update_tiles_around_move(board, from_flat, to_flat)


cdef void bitboard_move_piece(NonagaBitBoard* board, int current_q, int current_r, int new_q, int new_r):
    cdef int from_flat = _flat_index(current_q, current_r)
    cdef int to_flat = _flat_index(new_q, new_r)

    if _check_bit(board.red_pieces, current_q, current_r):
        _clear_bit(board.red_pieces, current_q, current_r)
        _set_bit(board.red_pieces, new_q, new_r)
    elif _check_bit(board.black_pieces, current_q, current_r):
        _clear_bit(board.black_pieces, current_q, current_r)
        _set_bit(board.black_pieces, new_q, new_r)

    _update_tiles_for_piece_move(board, from_flat, to_flat)
