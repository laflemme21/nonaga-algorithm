# cython: language_level=3, boundscheck=False, wraparound=False, profile=True
from nonaga_constants import RED, BLACK
from nonaga_logic cimport NonagaLogic
from nonaga_board cimport NonagaBoard, NonagaIsland, NonagaPiece, NonagaTile
import json
import os

# Module-level constants for alpha-beta bounds
cdef double NEG_INF = float('-inf')
cdef double POS_INF = float('inf')


cdef class AI:
    """Minimax AI with alpha-beta pruning for Nonaga."""
    #TODO: test that minimax is well implemented
    def __init__(self, parameter, int depth=2, int color=BLACK):
        self.parameter = parameter
        self.depth = depth
        self.max_color = color
        self.min_color = (color + 1) % 2
        self.depth_0_color = (color + depth) % 2

    # Inspired from https://papers-100-lines.medium.com/the-minimax-algorithm-and-alpha-beta-pruning-tutorial-in-30-lines-of-python-code-e4a3d97fa144

    cdef tuple minimax_piece(self, NonagaLogic game_state, int depth, bint maximizingPlayer, int color, double alpha, double beta):
        """Moves a piece in the minimax algorithm then calls minimax_tile."""

        cdef double value, tmp
        cdef tuple original_position, best_piece_move, best_tile_move, candidate_tile_move
        cdef dict all_possible_piece_moves
        cdef NonagaPiece piece
        cdef tuple move
        cdef NonagaLogic child

        # end of the loop
        if depth == 0: 
            return (self.cost_function(game_state, maximizingPlayer, self.parameter[0], self.parameter[1], self.parameter[2], self.parameter[3], self.parameter[4]), None, None)
        elif game_state.check_win_condition(RED) or game_state.check_win_condition(BLACK):
            # the last player to play won
            if maximizingPlayer:
                return (-99999999, None, None)
            else:
                return (99999999, None, None)
         
        cost = self.cost_function(game_state, maximizingPlayer, self.max_color, self.parameter)
        
                
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

    cdef tuple minimax_tile(self, NonagaLogic game_state, int depth, bint maximizingPlayer, int color, double alpha, double beta):
        """Moves a tile in the minimax algorithm then calls minimax_piece."""
        # We don't evaluate the game state after a piece move because the depth is only decreased after a tile move, which is the end of a turn.
        # So we only evaluate the game state at the end of a turn, which is more efficient.

        cdef double value, tmp
        cdef tuple original_position, best_tile_move, result
        cdef dict all_possible_tile_moves
        cdef NonagaTile tile
        cdef tuple move
        cdef NonagaLogic child

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


    cdef int cost_function(self, NonagaLogic game_state, bint maximizingPlayer, int max_color, list params):
        # for the AI, bigger better for the player lower better
        cdef list pieces = game_state.board.get_pieces(max_color)
        cdef NonagaPiece p0 = <NonagaPiece>pieces[0]
        cdef NonagaPiece p1 = <NonagaPiece>pieces[1]
        cdef NonagaPiece p2 = <NonagaPiece>pieces[2]
        cdef list pieces_pos = [(p0.q, p0.r, p0.s), (p1.q, p1.r, p1.s), (p2.q, p2.r, p2.s)]
        cdef tuple mt_ep = self.missing_tiles_and_enemy_pieces(game_state, pieces, pieces_pos, max_color)

        cdef int max_cost = params[0] * self.pieces_aligned(game_state, pieces, pieces_pos, max_color)\
              -params[1] * self.pieces_distance(game_state, pieces, max_color)\
              -params[2] * mt_ep[0]\
              -params[3] * mt_ep[1]

        cdef int min_color = (max_color + 1) % 2
        mt_ep = self.missing_tiles_and_enemy_pieces(game_state, pieces, pieces_pos, min_color)
        cdef int min_cost = -params[4] * self.pieces_aligned(game_state, pieces, pieces_pos, min_color)\
              +params[5] * self.pieces_distance(game_state, pieces, min_color)\
              +params[6] * mt_ep[0]\
              +params[7] * mt_ep[1]

        # if not maximizingPlayer:
        #     max_cost = -max_cost
        #     min_cost = -min_cost

        return max_cost + min_cost
               

    cdef int pieces_aligned(self, NonagaLogic game_state, list pieces, list pieces_pos, int color):
        # Counts the number of pieces of a color aligned
        cdef int aligned_count = 0
        cdef int i
        for i in range(3):
            if pieces_pos[0][i]==pieces_pos[1][i]:
                aligned_count+=1
            if pieces_pos[1][i]==pieces_pos[2][i]:
                aligned_count+=1
            if pieces_pos[2][i]==pieces_pos[0][i]:
                aligned_count+=1
        return aligned_count

    cdef int pieces_distance(self, NonagaLogic game_state, list pieces, int color):
        # Calculates the distance between pieces of a color
        cdef NonagaPiece pc0 = <NonagaPiece>pieces[0]
        cdef NonagaPiece pc1 = <NonagaPiece>pieces[1]
        cdef NonagaPiece pc2 = <NonagaPiece>pieces[2]
        cdef int d1 = pc0.distance_to(pc1)
        cdef int d2 = pc1.distance_to(pc2)
        cdef int d3 = pc2.distance_to(pc0)
        if d1>d2 and d1>d3:
            return d2+d3
        elif d2>d1 and d2>d3:
            return d3+d1
        else:
            return d1+d2
    
    cdef tuple missing_tiles_and_enemy_pieces(self, NonagaLogic game_state, list pieces, list pieces_pos, int color):
        # Count missing tiles and the number of enemy pieces in the cube-coordinate bounding region of the 3 pieces.
        cdef int missing_count = 0
        cdef int enemy_count = 0
        cdef NonagaBoard board = game_state.board

        cdef tuple pp1, pp2, pp3
        pp1 = pieces_pos[0]
        pp2 = pieces_pos[1]
        pp3 = pieces_pos[2]

        cdef int q_min = min(pp1[0], pp2[0], pp3[0])
        cdef int q_max = max(pp1[0], pp2[0], pp3[0])
        cdef int r_min = min(pp1[1], pp2[1], pp3[1])
        cdef int r_max = max(pp1[1], pp2[1], pp3[1])
        cdef int s_min = min(pp1[2], pp2[2], pp3[2])
        cdef int s_max = max(pp1[2], pp2[2], pp3[2])

        cdef int q, r, s
        cdef tuple pos
        cdef NonagaPiece found_piece
        for q in range(q_min, q_max + 1):
            for r in range(r_min, r_max + 1):
                s = -q - r
                if s < s_min or s > s_max:
                    continue
                pos = (q, r, s)
                if board.is_there_tile(pos) is False:
                    missing_count += 1
                else:
                    found_piece = board.get_piece(pos)
                    if found_piece is not None and found_piece.color != color:
                        enemy_count += 1

        return (missing_count, enemy_count)

    # is there a tile on our dream position? is it movable? is it reachable?

    cpdef tuple get_best_move(self, NonagaLogic game_state):
        """Returns the best move for the AI player.

        Args:
            game_state: current game state
        Returns:
            A tuple containing the best piece move and the best tile move combination.
        """
        cdef tuple result
        cdef NonagaPiece actual_piece
        cdef NonagaTile actual_tile
        cdef tuple best_piece_move, best_tile_move
        cdef double score

        result = self.minimax_piece(
            game_state.clone(), self.depth, True, game_state.get_current_player(), NEG_INF, POS_INF)
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
