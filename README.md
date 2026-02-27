## nonaga_board assumptions:
### nonaga island
a piece is a tile witha piece on it
we store all tiles and then just check if there is already a piece on the path to the destination tile.

To run with Profiling
python -m cProfile -o program.prof "My Nonaga/main.py"

To view Profiling, execute after a successful execution:
snakeviz program.prof 