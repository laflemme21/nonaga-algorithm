## nonaga_board assumptions:
### nonaga island
a piece is a tile witha piece on it
we store all tiles and then just check if there is already a piece on the path to the destination tile.

To run game with Profiling
python -m cProfile -o program.prof "NonagaGame/main.py"

To run GA with Profiling
python -m cProfile -o program.prof "ga_framework/main.py" 

To view Profiling, execute after a successful execution:
snakeviz program.prof 