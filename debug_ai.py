"""Debug - test at depth 1, 2, 3 only."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'NonagaGame'))

import json
from nonaga_constants import RED, BLACK, PIECE_TO_MOVE, TILE_TO_MOVE, AI_PARAM
from nonaga_logic import NonagaLogic
from AI import AI


def make_logic(tiles, red_pieces, black_pieces, player, phase):
    logic = NonagaLogic(None, None)
    logic.load_board_state(tiles, red_pieces, black_pieces, player, phase)
    return logic


def snapshot(logic):
    state = logic.get_board_state()
    tiles = [(t[0], t[1]) for t in state['tiles']]
    rp = [(p[0], p[1]) for p in state['pieces'] if p[3] == RED]
    bp = [(p[0], p[1]) for p in state['pieces'] if p[3] == BLACK]
    return tiles, rp, bp


def can_win_after(logic, player):
    tiles, rp, bp = snapshot(logic)
    logic2 = make_logic(tiles, rp, bp, player, PIECE_TO_MOVE)
    piece_moves = logic2.get_all_valid_piece_moves()
    for piece_pos, destinations in piece_moves.items():
        for dest in destinations:
            t2, rp2, bp2 = snapshot(logic2)
            l3 = make_logic(t2, rp2, bp2, player, PIECE_TO_MOVE)
            l3.move_piece_py(piece_pos, dest)
            tile_moves = l3.get_all_valid_tile_moves()
            for tile_pos, tile_dests in tile_moves.items():
                for tile_dest in tile_dests:
                    t3, rp3, bp3 = snapshot(l3)
                    l4 = make_logic(t3, rp3, bp3, player, TILE_TO_MOVE)
                    l4.move_tile_py(tile_pos, tile_dest)
                    if l4.check_win_condition_py(player):
                        return True, (piece_pos, dest), (tile_pos, tile_dest)
    return False, None, None


def load_state(path):
    with open(path, 'r') as f:
        data = json.load(f)
    tiles = [(t[0], t[1]) for t in data["board"]["tiles"]]
    rp = [(p[0], p[1]) for p in data["board"]["pieces"] if p[3] == RED]
    bp = [(p[0], p[1]) for p in data["board"]["pieces"] if p[3] == BLACK]
    cp = data["current_player"]
    return make_logic(tiles, rp, bp, cp, PIECE_TO_MOVE)


if __name__ == '__main__':
    logic = load_state('saved_board.json')

    print("Testing AI at depths 1-3:")
    for d in range(1, 4):
        ai2 = AI(AI_PARAM, depth=d, color=BLACK)
        tiles, rp, bp = snapshot(logic)
        l = make_logic(tiles, rp, bp, BLACK, PIECE_TO_MOVE)
        pm, tm = ai2.get_best_move(l)
        
        if pm and tm:
            tiles, rp, bp = snapshot(l)
            l2 = make_logic(tiles, rp, bp, BLACK, PIECE_TO_MOVE)
            l2.move_piece_py(pm[0], pm[1])
            t2, rp2, bp2 = snapshot(l2)
            l3 = make_logic(t2, rp2, bp2, BLACK, TILE_TO_MOVE)
            l3.move_tile_py(tm[0], tm[1])
            red_wins, rpm, rtm = can_win_after(l3, RED)
            status = "BAD (RED wins)" if red_wins else "GOOD (blocked)"
            print(f"  depth={d}: piece={pm}, tile={tm} => {status}" + (f" | RED: {rpm}, {rtm}" if red_wins else ""))
        else:
            print(f"  depth={d}: no move found")
