#ifndef NONAGA_BITBOARD_H
#define NONAGA_BITBOARD_H

#ifdef __cplusplus
extern "C"
{
#endif

    typedef struct NonagaBitBoard
    {
        unsigned long long red_pieces[7];
        unsigned long long black_pieces[7];
        unsigned long long movable_tiles[7];
        unsigned long long unmovable_tiles[7];
    } NonagaBitBoard;

    void bitboard_initialize(NonagaBitBoard *board);
    int bitboard_get_number_of_tiles(NonagaBitBoard *board);
    int bitboard_get_all_tiles(NonagaBitBoard *board, int *out_q, int *out_r, int *out_s, int max_count);
    int bitboard_get_movable_tiles(NonagaBitBoard *board, int *out_q, int *out_r, int *out_s, int max_count);
    int bitboard_is_there_tile(NonagaBitBoard *board, int q, int r);
    int bitboard_has_tile(NonagaBitBoard *board, int q, int r);
    int bitboard_is_there_piece(NonagaBitBoard *board, int q, int r);
    int bitboard_get_color(NonagaBitBoard *board, int q, int r);
    int bitboard_get_pieces(NonagaBitBoard *board, int color, int *out_q, int *out_r, int *out_s);
    void bitboard_move_tile(NonagaBitBoard *board, int current_q, int current_r, int new_q, int new_r);
    void bitboard_move_piece(NonagaBitBoard *board, int current_q, int current_r, int new_q, int new_r);

#ifdef __cplusplus
}
#endif

#endif
