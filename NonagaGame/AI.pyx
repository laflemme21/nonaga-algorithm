# cython: language_level=3, boundscheck=False, wraparound=False, profile=True
from nonaga_constants import RED, BLACK

from nonaga_bitboard cimport NonagaBitBoard
import json
import os

import faulthandler
faulthandler.enable()

# Module-level constants for alpha-beta bounds
cdef double NEG_INF = float('-inf')
cdef double POS_INF = float('inf')


cdef class AI:
    """Minimax AI with alpha-beta pruning for Nonaga."""
    def __init__(self, parameter, int depth=1, int color=BLACK):
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
        cdef tuple piece
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
                original_position = piece
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
                original_position = piece
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
        cdef tuple tile
        cdef tuple move = None

        # tile moves are independant of the current player
        all_possible_tile_moves = game_state.get_all_valid_tile_moves_ai()
        if not all_possible_tile_moves:
            return (self.cost_function(game_state, maximizingPlayer, self.max_color, self.parameter), None)

        # AI's turn
        if maximizingPlayer:
            value = NEG_INF
            for tile in all_possible_tile_moves:
                original_position = tile
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
                original_position = tile
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
        cdef NonagaBitBoard board = game_state.board
        
        # Get both piece sets at once to reduce board access
        cdef list max_pieces = list(board.get_pieces(max_color))
        cdef list min_pieces = list(board.get_pieces(min_color))
        
        # Extract pieces and positions for max_color (AI)
        cdef tuple p0 = <tuple>max_pieces[0]
        cdef tuple p1 = <tuple>max_pieces[1]
        cdef tuple p2 = <tuple>max_pieces[2]
        
        # Extract pieces and positions for min_color (opponent)  
        cdef tuple mp0 = <tuple>min_pieces[0]
        cdef tuple mp1 = <tuple>min_pieces[1]
        cdef tuple mp2 = <tuple>min_pieces[2]
        
        # Calculate costs inline to avoid function call overhead and temporary list creation
        # Max cost (AI pieces)
        cdef int max_aligned = 0
        cdef int i
        # Inline pieces_aligned calculation for max pieces
        for i in range(3):
            if p0[i] == p1[i]:
                max_aligned += 1
            if p1[i] == p2[i]:
                max_aligned += 1
            if p2[i] == p0[i]:
                max_aligned += 1
        
        # Inline pieces_distance calculation for max pieces
        cdef int d1 = self.distance_to(p0, p1)
        cdef int d2 = self.distance_to(p1, p2)  
        cdef int d3 = self.distance_to(p2, p0)
        cdef int max_distance = d2 + d3 if d1 > d2 and d1 > d3 else (d3 + d1 if d2 > d1 and d2 > d3 else d1 + d2)
        
        # Calculate missing tiles and enemy pieces for max pieces
        cdef int max_missing, max_enemies
        max_missing, max_enemies = self.missing_tiles_and_enemy_pieces(board, p0, p1, p2, max_color)
        
        cdef int max_cost = params[0] * max_aligned - params[1] * max_distance - params[2] * max_missing - params[3] * max_enemies

        # Min cost (opponent pieces)
        cdef int min_aligned = 0
        # Inline pieces_aligned calculation for min pieces
        for i in range(3):
            if mp0[i] == mp1[i]:
                min_aligned += 1
            if mp1[i] == mp2[i]:
                min_aligned += 1
            if mp2[i] == mp0[i]:
                min_aligned += 1
        
        # Inline pieces_distance calculation for min pieces
        d1 = self.distance_to(mp0, mp1)
        d2 = self.distance_to(mp1, mp2)
        d3 = self.distance_to(mp2, mp0)
        cdef int min_distance = d2 + d3 if d1 > d2 and d1 > d3 else (d3 + d1 if d2 > d1 and d2 > d3 else d1 + d2)
        
        # Calculate missing tiles and enemy pieces for min pieces
        cdef int min_missing, min_enemies
        min_missing, min_enemies = self.missing_tiles_and_enemy_pieces(board, mp0, mp1, mp2, min_color)
        
        cdef int min_cost = -params[4] * min_aligned + params[5] * min_distance + params[6] * min_missing + params[7] * min_enemies

        # if not maximizingPlayer:
        #     max_cost = -max_cost
        #     min_cost = -min_cost
        
        return max_cost + min_cost

    cdef int distance_to(self, tuple c1, tuple c2):
        cdef int dq = c1[0] - c2[0]
        cdef int dr = c1[1] - c2[1]
        cdef int ds = c1[2] - c2[2]
        if dq < 0: dq = -dq
        if dr < 0: dr = -dr
        if ds < 0: ds = -ds
        return (dq + dr + ds) // 2
    
    cdef tuple missing_tiles_and_enemy_pieces(self, NonagaBitBoard board, tuple p0, tuple p1, tuple p2, int color):
        
        cdef int missing_count = 0
        cdef int enemy_count = 0

        cdef int q_min = min(p0[0], p1[0], p2[0])
        cdef int q_max = max(p0[0], p1[0], p2[0])
        cdef int r_min = min(p0[1], p1[1], p2[1])
        cdef int r_max = max(p0[1], p1[1], p2[1])
        cdef int s_min = min(p0[2], p1[2], p2[2])
        cdef int s_max = max(p0[2], p1[2], p2[2])

        cdef int q, r, s
        cdef int found_piece_color
        for q in range(q_min, q_max + 1):
            for r in range(r_min, r_max + 1):
                s = -q - r
                if s < s_min or s > s_max:
                    continue
                
                if not board.has_tile(q, r):
                    missing_count += 1
                else:
                    found_piece_color = board.get_color(q, r)
                    if found_piece_color != -1 and found_piece_color != color:
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
        cdef tuple best_piece_move, best_tile_move
        cdef double score
        result = self.minimax_piece(
            game_state, self.depth, True, game_state.get_current_player(), NEG_INF, POS_INF)
      
        score = result[0]
        best_piece_move = result[1]
        best_tile_move = result[2]

        return (best_piece_move, best_tile_move)
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
