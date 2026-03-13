# cython: language_level=3, boundscheck=False, wraparound=False, profile=True
from nonaga_constants import RED, BLACK
from nonaga_logic cimport NonagaLogic
from nonaga_board cimport NonagaBoard, NonagaIsland, NonagaPiece, NonagaTile
import json
import os

import faulthandler
faulthandler.enable()

# Module-level constants for alpha-beta bounds
cdef double NEG_INF = float('-inf')
cdef double POS_INF = float('inf')


cdef class AI:
    """Minimax AI with alpha-beta pruning for Nonaga."""
    def __init__(self, parameter, int depth=2, int color=BLACK):
        self.parameter = parameter
        self.depth = depth
        self.max_color = color
        self.min_color = (color + 1) % 2
        self.depth_0_color = (color + depth) % 2

    # Inspired from https://papers-100-lines.medium.com/the-minimax-algorithm-and-alpha-beta-pruning-tutorial-in-30-lines-of-python-code-e4a3d97fa144

    cdef tuple minimax_piece(self, NonagaLogic game_state, int depth, bint maximizingPlayer, int color, double alpha, double beta):
        """Moves a piece in the minimax algorithm then calls minimax_tile."""

        cdef double value = 0
        cdef double tmp = 0
        cdef tuple original_position = None
        cdef tuple best_piece_move = None
        cdef tuple best_tile_move = None
        cdef tuple candidate_tile_move = None
        cdef dict all_possible_piece_moves = {}
        cdef NonagaPiece piece
        cdef tuple move = None

        # end of the loop
        if depth == 0: 
            return (self.cost_function(game_state, maximizingPlayer, self.max_color, self.parameter), None, None)
        elif game_state.check_win_condition(RED) or game_state.check_win_condition(BLACK):
            # the last player to play won
            if maximizingPlayer:
                return (-99999999, None, None)
            else:
                return (99999999, None, None)
         
        
        # AI's turn
        if maximizingPlayer:
            value = NEG_INF
            all_possible_piece_moves = game_state.get_all_valid_piece_moves_ai()
            if not all_possible_piece_moves:
                return (self.cost_function(game_state, maximizingPlayer, self.max_color, self.parameter), None, None)
            for piece in all_possible_piece_moves:
                original_position = piece.get_position()
                for move in all_possible_piece_moves[piece]:
                    game_state.move_piece(piece, move)

                    # We don't change the depth and current player because one player moves a piece and tile per turn
                    tmp, candidate_tile_move = self.minimax_tile(
                        game_state, depth, maximizingPlayer, color, alpha, beta)
                    game_state.undo_piece_move(piece, original_position)
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
            if not all_possible_piece_moves:
                return (self.cost_function(game_state, maximizingPlayer, self.max_color, self.parameter), None, None)
            for piece in all_possible_piece_moves:
                original_position = piece.get_position()
                for move in all_possible_piece_moves[piece]:
                    game_state.move_piece(piece, move)

                    tmp, candidate_tile_move = self.minimax_tile(
                        game_state, depth, maximizingPlayer, color,alpha, beta)
                    game_state.undo_piece_move(piece, original_position)
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

        if best_piece_move is None or best_tile_move is None:
            return (self.cost_function(game_state, maximizingPlayer, self.max_color, self.parameter), None, None)

        return (value, best_piece_move, best_tile_move)

    cdef tuple minimax_tile(self, NonagaLogic game_state, int depth, bint maximizingPlayer, int color, double alpha, double beta):
        """Moves a tile in the minimax algorithm then calls minimax_piece."""
        # We don't evaluate the game state after a piece move because the depth is only decreased after a tile move, which is the end of a turn.
        # So we only evaluate the game state at the end of a turn, which is more efficient.

        cdef double value = 0
        cdef double tmp = 0
        cdef tuple original_position = None
        cdef tuple best_tile_move = None
        cdef tuple result = None
        cdef dict all_possible_tile_moves = {}
        cdef NonagaTile tile
        cdef tuple move = None

        # tile moves are independant of the current player
        all_possible_tile_moves = game_state.get_all_valid_tile_moves_ai()
        if not all_possible_tile_moves:
            return (self.cost_function(game_state, maximizingPlayer, self.max_color, self.parameter), None)

        # AI's turn
        if maximizingPlayer:
            value = NEG_INF
            for tile in all_possible_tile_moves:
                original_position = tile.get_position()
                for move in all_possible_tile_moves[tile]:
                    game_state.move_tile(tile, move)

                    result = self.minimax_piece(
                        game_state, depth - 1, False, (color+1)%2, alpha, beta)
                    game_state.undo_tile_move(tile, original_position) # undo the tile move
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
                    game_state.move_tile(tile, move)

                    result = self.minimax_piece(
                        game_state, depth - 1, True, (color+1)%2, alpha, beta)
                    game_state.undo_tile_move(tile, original_position) # undo the tile move
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

        if best_tile_move is None:
            return (self.cost_function(game_state, maximizingPlayer, self.max_color, self.parameter), None)

        return (value, best_tile_move)


    cdef int cost_function(self, NonagaLogic game_state, bint maximizingPlayer, int max_color, list params):
        # for the AI, bigger better for the player lower better
        cdef int min_color = (max_color + 1) % 2
        cdef NonagaBoard board = game_state.board
        
        # Get both piece sets at once to reduce board access
        cdef list max_pieces = board.get_pieces(max_color)
        cdef list min_pieces = board.get_pieces(min_color)
        
        # Extract pieces and positions for max_color (AI)
        cdef NonagaPiece p0 = <NonagaPiece>max_pieces[0]
        cdef NonagaPiece p1 = <NonagaPiece>max_pieces[1]
        cdef NonagaPiece p2 = <NonagaPiece>max_pieces[2]
        
        # Extract pieces and positions for min_color (opponent)  
        cdef NonagaPiece mp0 = <NonagaPiece>min_pieces[0]
        cdef NonagaPiece mp1 = <NonagaPiece>min_pieces[1]
        cdef NonagaPiece mp2 = <NonagaPiece>min_pieces[2]
        
        # Calculate costs inline to avoid function call overhead and temporary list creation
        # Max cost (AI pieces)
        cdef int max_aligned = 0
        cdef int i
        # Inline pieces_aligned calculation for max pieces
        for i in range(3):
            if (p0.q if i == 0 else (p0.r if i == 1 else p0.s)) == (p1.q if i == 0 else (p1.r if i == 1 else p1.s)):
                max_aligned += 1
            if (p1.q if i == 0 else (p1.r if i == 1 else p1.s)) == (p2.q if i == 0 else (p2.r if i == 1 else p2.s)):
                max_aligned += 1
            if (p2.q if i == 0 else (p2.r if i == 1 else p2.s)) == (p0.q if i == 0 else (p0.r if i == 1 else p0.s)):
                max_aligned += 1
        
        # Inline pieces_distance calculation for max pieces
        cdef int d1 = p0.distance_to(p1)
        cdef int d2 = p1.distance_to(p2)  
        cdef int d3 = p2.distance_to(p0)
        cdef int max_distance = d2 + d3 if d1 > d2 and d1 > d3 else (d3 + d1 if d2 > d1 and d2 > d3 else d1 + d2)
        
        # Calculate missing tiles and enemy pieces for max pieces
        cdef int max_missing, max_enemies
        max_missing, max_enemies = self.missing_tiles_and_enemy_pieces(board, p0, p1, p2, max_color)
        
        cdef int max_cost = params[0] * max_aligned - params[1] * max_distance - params[2] * max_missing - params[3] * max_enemies

        # Min cost (opponent pieces)
        cdef int min_aligned = 0
        # Inline pieces_aligned calculation for min pieces
        for i in range(3):
            if (mp0.q if i == 0 else (mp0.r if i == 1 else mp0.s)) == (mp1.q if i == 0 else (mp1.r if i == 1 else mp1.s)):
                min_aligned += 1
            if (mp1.q if i == 0 else (mp1.r if i == 1 else mp1.s)) == (mp2.q if i == 0 else (mp2.r if i == 1 else mp2.s)):
                min_aligned += 1
            if (mp2.q if i == 0 else (mp2.r if i == 1 else mp2.s)) == (mp0.q if i == 0 else (mp0.r if i == 1 else mp0.s)):
                min_aligned += 1
        
        # Inline pieces_distance calculation for min pieces
        d1 = mp0.distance_to(mp1)
        d2 = mp1.distance_to(mp2)
        d3 = mp2.distance_to(mp0)
        cdef int min_distance = d2 + d3 if d1 > d2 and d1 > d3 else (d3 + d1 if d2 > d1 and d2 > d3 else d1 + d2)
        
        # Calculate missing tiles and enemy pieces for min pieces
        cdef int min_missing, min_enemies
        min_missing, min_enemies = self.missing_tiles_and_enemy_pieces(board, mp0, mp1, mp2, min_color)
        
        cdef int min_cost = -params[4] * min_aligned + params[5] * min_distance + params[6] * min_missing + params[7] * min_enemies

        # if not maximizingPlayer:
        #     max_cost = -max_cost
        #     min_cost = -min_cost
        
        return max_cost + min_cost
    
    cdef tuple missing_tiles_and_enemy_pieces(self, NonagaBoard board, NonagaPiece p0, NonagaPiece p1, NonagaPiece p2, int color):
        
        cdef int missing_count = 0
        cdef int enemy_count = 0

        cdef int q_min = min(p0.q, p1.q, p2.q)
        cdef int q_max = max(p0.q, p1.q, p2.q)
        cdef int r_min = min(p0.r, p1.r, p2.r)
        cdef int r_max = max(p0.r, p1.r, p2.r)
        cdef int s_min = min(p0.s, p1.s, p2.s)
        cdef int s_max = max(p0.s, p1.s, p2.s)

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
            game_state, self.depth, True, game_state.get_current_player(), NEG_INF, POS_INF)
      
        score = result[0]
        best_piece_move = result[1]
        best_tile_move = result[2]

        # Find the actual piece object in the current game state
        actual_piece = game_state.board.get_piece(best_piece_move[0])

        # Find the actual tile object in the current game state
        actual_tile = game_state.board.get_tile(best_tile_move[0])

        return (actual_piece, best_piece_move[1]), (actual_tile, best_tile_move[1])

def execute_best_move(self, game_state: NonagaLogic):
        """Executes the best move for the AI player.
        Args:
            game_state: current game state
        """
        best_piece_move, best_tile_move = self.get_best_move(game_state)
        game_state.undo_piece_move(best_piece_move[0], best_piece_move[1])
        game_state.undo_tile_move(best_tile_move[0], best_tile_move[1])
