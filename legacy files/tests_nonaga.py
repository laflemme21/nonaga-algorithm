from nonaga_board import NonagaBoard
from nonaga_logic import NonagaGame, RED, BLACK
from game import Game
import unittest

class TestNonagaGame(unittest.TestCase):
    def setUp(self):
        """Set up a new game before each test."""
        self.game_logic = NonagaGame()
        self.board = NonagaBoard()

    def test_initial_board_state(self):
        """Test that the initial board state is set up correctly."""
        initial_state = self.game_logic.get_board_state()
        expected_state = self.board.get_state()
        self.assertEqual(initial_state, expected_state)

    def test_make_move(self):
        """Test making a valid move."""
        initial_state = self.game_logic.get_board_state()
        valid_moves = self.game_logic.get_valid_moves()
        if valid_moves:
            move = valid_moves[0]
            self.game_logic.make_move(move)
            new_state = self.game_logic.get_board_state()
            self.assertNotEqual(initial_state, new_state)
        else:
            self.skipTest("No valid moves available to test.")

    def test_check_win_condition(self):
        """Test win condition checking."""
        # Simulate a winning condition for RED