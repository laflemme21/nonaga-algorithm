from nonaga_logic import NonagaLogic
from nonaga_constants import RED, BLACK
import json
import os
import copy

class AI:
    def __init__(self, parameter, depth=1):
        self.parameter = parameter
        self.depth = depth

    # Inspired from https://papers-100-lines.medium.com/the-minimax-algorithm-and-alpha-beta-pruning-tutorial-in-30-lines-of-python-code-e4a3d97fa144
    """Moves a piece in the minimax algorithm then calls minimax_tile"""
    def minimax_piece(self, game_state: NonagaLogic, depth: int, maximizingPlayer: bool):

        # end of the loop
        if depth==0 or game_state.check_win_condition(RED) or game_state.check_win_condition(BLACK):
            return self.cost_function(game_state), None

        # AI's turn
        if maximizingPlayer:
            value = float('-inf')
            all_possible_piece_moves = game_state.get_all_valid_piece_moves_ai()
            for piece in all_possible_piece_moves:
                original_position = piece.get_position()
                for move in all_possible_piece_moves[piece]:
                    child = game_state.move_piece_ai(piece, move)

                    # We don't change the depth and current player because one player moves a piece and tile per turn
                    tmp, candidate_tile_move = self.minimax_tile(child, depth, maximizingPlayer)
                    if tmp > value:
                        value = tmp
                        best_piece_move = (original_position, move)
                        best_tile_move = candidate_tile_move
        # player's turn
        else:
            value = float('inf')
            all_possible_piece_moves = game_state.get_all_valid_piece_moves_ai()
            for piece in all_possible_piece_moves:
                original_position = piece.get_position()
                for move in all_possible_piece_moves[piece]:
                    child = game_state.move_piece_ai(piece,move)
                    
                    tmp, candidate_tile_move = self.minimax_tile(child, depth, maximizingPlayer)
                    if tmp < value:
                        value = tmp
                        best_piece_move = (original_position, move)
                        best_tile_move = candidate_tile_move

        return value, best_piece_move, best_tile_move

    """Moves a tile in the minimax algorithm then calls minimax_piece"""
    def minimax_tile(self, game_state: NonagaLogic, depth: int, maximizingPlayer: bool):
        # We don't evaluate the game state after a piece move because the depth is only decreased after a tile move, which is the end of a turn. 
        # So we only evaluate the game state at the end of a turn, which is more efficient.

        # tile moves are independant of the current player
        all_possible_tile_moves = game_state.get_all_valid_tile_moves_ai()
        
        # AI's turn
        if maximizingPlayer:
            value = float('-inf')
            for tile in all_possible_tile_moves:
                original_position = tile.get_position()
                for move in all_possible_tile_moves[tile]:
                    child = game_state.move_tile_ai(tile, move)

                    tmp = self.minimax_piece(child, depth-1, False)[0]
                    if tmp > value:
                        value = tmp
                        best_tile_move = (original_position, move)

        # Player's turn
        else:
            value = float('inf')
            for tile in all_possible_tile_moves:
                original_position = tile.get_position()
                for move in all_possible_tile_moves[tile]:
                    child = game_state.move_tile_ai(tile, move)

                    tmp = self.minimax_piece(child, depth-1, True)[0]
                    if tmp < value:
                        value = tmp
                        best_tile_move = (original_position, move)

        return value, best_tile_move
    
    def cost_function(self, game_state: NonagaLogic) -> int:
        return 1

    def get_best_move(self, game_state: NonagaLogic) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        """Returns the best move for the AI player.

        Args:
            game_state: current game state
        Returns:
            A tuple containing the best piece move and the best tile move combination.
            
        """
        _, best_piece_move, best_tile_move = self.minimax_piece(copy.deepcopy(game_state), self.depth, True)
        
        # Find the actual piece object in the current game state
        actual_piece = game_state.board.get_piece(best_piece_move[0])

        # Find the actual tile object in the current game state
        actual_tile = game_state.board.get_tile(best_tile_move[0])
    
        print(f"Best piece move value: {_}")
        return (actual_piece, best_piece_move[1]), (actual_tile, best_tile_move[1])
    
def load_parameters():
    os.chdir(os.path.dirname(__file__))
    with open("parameters.json", "r") as f:
        parameters = json.load(f)
    return parameters[0]