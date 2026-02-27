# cython: language_level=3, boundscheck=False, wraparound=False, profile=True
import random
from nonaga_constants import RED, BLACK
import json
import os

# Module-level constants for alpha-beta bounds
cdef double NEG_INF = float('-inf')
cdef double POS_INF = float('inf')


cdef class AI:
    """Minimax AI with alpha-beta pruning for Nonaga."""

    def __init__(self, parameter, int depth=3):
        self.parameter = parameter
        self.depth = depth

    # Inspired from https://papers-100-lines.medium.com/the-minimax-algorithm-and-alpha-beta-pruning-tutorial-in-30-lines-of-python-code-e4a3d97fa144

    cdef tuple minimax_piece(self, object game_state, int depth, bint maximizingPlayer, color,double alpha, double beta):
        """Moves a piece in the minimax algorithm then calls minimax_tile."""

        cdef double value, tmp
        cdef tuple original_position, best_piece_move, best_tile_move, candidate_tile_move
        cdef dict all_possible_piece_moves
        cdef object piece, move, child

        # end of the loop
        if depth == 0: 
            return (self.cost_function(game_state, maximizingPlayer, self.parameter[0], self.parameter[1], self.parameter[2], self.parameter[3], self.parameter[4]), None, None)
        elif game_state.check_win_condition(RED) or game_state.check_win_condition(BLACK):
            # the last player to play won
            if maximizingPlayer:
                return (-999999, None, None)
            else:
                return (999999, None, None)
        # AI's turn
        if maximizingPlayer:
            value = NEG_INF
            all_possible_piece_moves = game_state.get_all_valid_piece_moves_ai()
            for piece in all_possible_piece_moves:
                original_position = piece.get_position()
                for move in all_possible_piece_moves[piece]:
                    child = game_state.move_piece_ai(piece, move)

                    # We don't change the depth and current player because one player moves a piece and tile per turn
                    tmp, candidate_tile_move = self.minimax_tile(
                        child, depth, maximizingPlayer, color, alpha, beta)
                    if tmp > value:
                        value = tmp
                        best_piece_move = (original_position, move)
                        best_tile_move = candidate_tile_move
                    alpha = max(alpha, value)
                    if alpha >= beta:
                        break
                else:
                    continue
                break
        # player's turn
        else:
            value = POS_INF
            all_possible_piece_moves = game_state.get_all_valid_piece_moves_ai()
            for piece in all_possible_piece_moves:
                original_position = piece.get_position()
                for move in all_possible_piece_moves[piece]:
                    child = game_state.move_piece_ai(piece, move)

                    tmp, candidate_tile_move = self.minimax_tile(
                        child, depth, maximizingPlayer, color,alpha, beta)
                    if tmp < value:
                        value = tmp
                        best_piece_move = (original_position, move)
                        best_tile_move = candidate_tile_move
                    beta = min(beta, value)
                    if alpha >= beta:
                        break
                else:
                    continue
                break

        return (value, best_piece_move, best_tile_move)

    cdef tuple minimax_tile(self, object game_state, int depth, bint maximizingPlayer, color, double alpha, double beta):
        """Moves a tile in the minimax algorithm then calls minimax_piece."""
        # We don't evaluate the game state after a piece move because the depth is only decreased after a tile move, which is the end of a turn.
        # So we only evaluate the game state at the end of a turn, which is more efficient.

        cdef double value, tmp
        cdef tuple original_position, best_tile_move, result
        cdef dict all_possible_tile_moves
        cdef object tile, move, child

        # tile moves are independant of the current player
        all_possible_tile_moves = game_state.get_all_valid_tile_moves_ai()

        # AI's turn
        if maximizingPlayer:
            value = NEG_INF
            for tile in all_possible_tile_moves:
                original_position = tile.get_position()
                for move in all_possible_tile_moves[tile]:
                    child = game_state.move_tile_ai(tile, move)

                    result = self.minimax_piece(
                        child, depth - 1, False, (color+1)%2, alpha, beta)
                    tmp = result[0]
                    if tmp > value:
                        value = tmp
                        best_tile_move = (original_position, move)
                    alpha = max(alpha, value)
                    if alpha >= beta:
                        break
                else:
                    continue
                break

        # Player's turn
        else:
            value = POS_INF
            for tile in all_possible_tile_moves:
                original_position = tile.get_position()
                for move in all_possible_tile_moves[tile]:
                    child = game_state.move_tile_ai(tile, move)

                    result = self.minimax_piece(
                        child, depth - 1, True, (color+1)%2, alpha, beta)
                    tmp = result[0]
                    if tmp < value:
                        value = tmp
                        best_tile_move = (original_position, move)
                    beta = min(beta, value)
                    if alpha >= beta:
                        break
                else:
                    continue
                break

        return (value, best_tile_move)

    cdef int cost_function(self, object game_state, bint maximizingPlayer, int color, int param1, int param2, int param3, int param4):
        # for the AI, bigger better for the player llower better
        cost =param1 * self.pieces_aligned(game_state, color)+\
              -param2 * self.pieces_distance(game_state, color)
            #    0*param3 * self.count_missing_tiles(game_state, color) 

        if not maximizingPlayer:
            cost = -cost

        return cost
               

    cdef int pieces_aligned(self, object game_state, int color):
        # Counts the number of pieces of a color aligned
        pieces = game_state.board.get_pieces(color)
        pieces = [piece.get_position() for piece in pieces]
        cdef int aligned_count = 0
        for i in range(3):
            if pieces[0][i]==pieces[1][i]:
                aligned_count+=1
            if pieces[1][i]==pieces[2][i]:
                aligned_count+=1
            if pieces[2][i]==pieces[0][i]:
                aligned_count+=1
        return aligned_count

    cdef int pieces_distance(self, object game_state, int color):
        # Placeholder for a function that calculates the distance between pieces of a color
        pieces = game_state.board.get_pieces(color)
        d1 = pieces[0].distance_to(pieces[1])
        d2 = pieces[1].distance_to(pieces[2])
        d3 = pieces[2].distance_to(pieces[0])
        if d1>d2 and d1>d3:
            return d2+d3
        elif d2>d1 and d2>d3:
            return d3+d1
        else:
            return d1+d2
    
    cdef int count_missing_tiles(self, object game_state, int color):
        # TODO
        # count the missing tiles in parallelogram formed between the pieces
        return random.randint(-5, 5)

    # is there a tile on our dream position? is it movable? is it reachable?

    cpdef tuple get_best_move(self, object game_state):
        """Returns the best move for the AI player.

        Args:
            game_state: current game state
        Returns:
            A tuple containing the best piece move and the best tile move combination.
        """
        cdef tuple result
        cdef object actual_piece, actual_tile
        cdef tuple best_piece_move, best_tile_move
        cdef double score

        result = self.minimax_piece(
            game_state.clone(), self.depth, True, game_state.get_current_player(),NEG_INF, POS_INF)
        score = result[0]
        best_piece_move = result[1]
        best_tile_move = result[2]

        # Find the actual piece object in the current game state
        actual_piece = game_state.board.get_piece(best_piece_move[0])

        # Find the actual tile object in the current game state
        actual_tile = game_state.board.get_tile(best_tile_move[0])

        print(f"Best piece move value: {score}")
        return (actual_piece, best_piece_move[1]), (actual_tile, best_tile_move[1])


def load_parameters():
    os.chdir(os.path.dirname(__file__))
    with open("parameters.json", "r") as f:
        parameters = json.load(f)
    return parameters[0]
