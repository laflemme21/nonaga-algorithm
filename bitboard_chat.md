# Cython Minimax Optimization for a Dynamic Hexagonal Board Game

## User
I coded a minimax in python, but then realised my implementation took too much time to run. I then decided to translate it in cython since it is much faster. Now it runs a lot faster (2 times faster or so) but I though going from python to cython would make it 25 times faster or so

## Assistant
It sounds like you've hit the classic Cython wall! It is completely normal to feel underwhelmed at first. 

What you are experiencing is actually exactly what is expected. If you take standard Python code, paste it into a `.pyx` file, and compile it without changing the syntax, you will typically only see a **1.2x to 2x speedup**. 

To get that massive 25x to 100x performance boost, you have to tell Cython how to bypass the Python interpreter entirely. Right now, your compiled C code is likely still heavily relying on the Python C-API. 

Here is why your code is still bottlenecked and exactly how to fix it.

### Why You Only Got a 2x Speedup
When Cython compiles pure Python code, it doesn't automatically know what types your variables are. Because of this, it has to treat everything as a generic Python object (`PyObject*`). Every time you add two numbers, update a board state, or call your recursive Minimax function, Cython is still doing Python-level type-checking and memory management behind the scenes. 

In a heavy recursive algorithm like Minimax, the overhead of creating and destroying these Python objects millions of times adds up fast.

---

### How to Unlock True C-Level Speeds

To get the performance you are looking for, you need to add static C typing to your code. Here are the most critical steps to optimize your Minimax algorithm:

**1. Generate an HTML Annotation Report (The "Yellow" Test)**
This is the most powerful tool in Cython. Run your compilation with the `-a` flag:
`cython -a your_module.pyx`
This generates an HTML file. Open it in your browser. Lines highlighted in **yellow** indicate interaction with the Python interpreter. The darker the yellow, the heavier the Python overhead. Your goal is to make your main Minimax loop and board evaluation logic completely **white** (pure C).

**2. Use `cdef` for All Variables**
Any variable used inside a loop (like counters, scores, alphas, and betas) must be statically typed.
> **Instead of:** `score = 0`
> **Do this:** `cdef int score = 0`

**3. Change `def` to `cdef` for the Minimax Function**
Python function calls are incredibly slow, and Minimax is heavily recursive. By changing your internal functions to C functions, you eliminate the Python call overhead.
* Use `cdef` for internal functions that are only called by other Cython functions.
* Use `cpdef` if the function needs to be called from both your main Python script and internally in Cython.
* *Make sure to type the return value and arguments.*
> **Example:** `cdef int minimax(int depth, int alpha, int beta, bint maximizing_player):`

**4. Ditch Python Lists for Board State**
If your board is represented as a list of lists, or even a standard dictionary, Cython will choke on it. Python lists are arrays of pointers to objects. 
* **Best option:** Use an integer as a "Bitboard" (if your game is simple enough, like Tic-Tac-Toe, Connect 4, or Chess). Bitwise operations on `cdef int` or `cdef long long` are blazingly fast.
* **Good option:** Use C-arrays (e.g., `cdef int board[8][8]`) or typed Memoryviews if you are passing NumPy arrays.

**5. Disable Cython Checks (Compiler Directives)**
Once you are confident your code doesn't have out-of-bounds errors, you can tell Cython to stop checking for them. Add these decorators right above your Minimax function:
```python
import cython

@cython.boundscheck(False)  # Deactivate bounds checking
@cython.wraparound(False)   # Deactivate negative indexing
```

By applying these changes—specifically typing your variables and using `cdef` for the recursive function—you should easily hit that 25x speedup or more.

## User
Actually i recalculated and realised I hit a 37x speedup, but I need a lot lot more

## Assistant
That 37x speedup is massive! Congratulations—that means you actually hit the ceiling of what standard Cython optimization can do. You successfully stripped away the Python overhead and are now running at near-native C speeds. 

But here is the brutal reality of Minimax: **game trees grow exponentially**. 

If your game has a branching factor of 30 (like Chess) and you want to look one move deeper, your code needs to be 30 times faster. Getting a 37x speedup from Cython essentially only bought you **one extra layer of depth**. 

To get "a lot, lot more" speed (we are talking 1,000x to 1,000,000x faster), you can't just rely on making your code execute faster. You have to evaluate fewer nodes. Here is the roadmap to pushing your Minimax engine to the next level.

### 1. Alpha-Beta Pruning + Move Ordering (The Multipliers)
If you haven't implemented Alpha-Beta pruning yet, do that immediately. It cuts off branches of the tree that mathematically cannot influence the final decision.

However, **Alpha-Beta pruning is only as good as your Move Ordering.** If you evaluate the *worst* moves first, Alpha-Beta doesn't prune anything. If you evaluate the *best* moves first, it prunes almost the entire tree. 
* **How to fix:** Before looping through available moves in a state, sort them. Use a simple, fast heuristic (like capturing pieces in Chess, or playing in the center in Connect 4) to guess which moves are best, and search those first. 

### 2. Transposition Tables (Zobrist Hashing)
In many games, different sequences of moves lead to the exact same board state. Standard Minimax will recalculate that entire board state every single time it sees it.
* **The Fix:** Create a Transposition Table (a hash map) to store the evaluation score of a board once you calculate it. 
* **Cython Trick:** Do *not* use a standard Python dictionary for this; it will ruin your Cython speedup. Implement Zobrist Hashing. It assigns a random 64-bit integer to every piece on every square. As pieces move, you use the Bitwise XOR operator (`^`) to update the hash in `O(1)` time. You then use this hash as an index in a large, pre-allocated C-array (`cdef int table[SIZE]`) to store and look up scores instantly.

### 3. Iterative Deepening
Instead of telling your Minimax to just "search to depth 6," tell it to search depth 1, then depth 2, then depth 3, etc., until you run out of time.
This sounds slower because you are repeating work, but it is actually *much* faster. Why? Because the results from depth 1 give you the perfect **Move Ordering** for depth 2. The results from depth 2 give you perfect ordering for depth 3. Combined with a Transposition Table, this makes Alpha-Beta pruning incredibly efficient.

### 4. Unleash the CPU Cores (`nogil`)
Right now, your Minimax is likely using exactly 100% of a *single* core on your CPU. Cython has a magic trick: it can bypass Python's Global Interpreter Lock (GIL).
If your Minimax function is completely free of Python objects (pure C types), you can tell Cython to release the GIL and run your search on multiple CPU cores simultaneously using `prange` (parallel range).

```cython
from cython.parallel import prange

# Example of evaluating root moves in parallel
cdef int i
for i in prange(num_moves, nogil=True):
    # Search each branch on a different CPU thread
    scores[i] = minimax(states[i], depth-1, alpha, beta)
```

### 5. Bitboards (Ultimate Data Structure)
If your game uses a grid (Chess, Checkers, Connect 4, Othello), throw away your arrays/matrices. Represent the board as a 64-bit integer (`cdef unsigned long long`). 
You can calculate complex moves, captures, and board evaluations using bitwise operations (`&`, `|`, `<<`, `>>`), which execute in a single clock cycle on the CPU. 

---

To get to the next level, you have to transition from purely optimizing code to optimizing the algorithm. 

## User
You are right! My biggest bottleneck is the way I represent the game in cython. I use a complex object (equivalent to defining each piece and each square with coordinates in chess) but it would be sooo much faster if it was represented by a big int. the problem is that I have no idea how to represent it that way or represent a part of it that way because it is significantly different than chess. My game has a board and identical pieces that can be red or black. One hexagone of the board is moved at each player turn, so It’s really hard for me to implement that game similarly to chess.

## Assistant
Ah, a shifting hexagonal board! That explains exactly why standard chess logic breaks down for you. You are dealing with a dynamic state where the "terrain" itself is a variable. That is a notoriously tricky problem in game AI, and it makes total sense why you defaulted to a complex object representation. 

But you are absolutely right: representing this as primitive C-integers will blow the doors off your current performance. 

To do this, we need to abandon the idea of a single "board object" and instead use a **Bitboard system**. Since your pieces are identical and only have two colors, this is actually the *perfect* candidate for bitboards. You don't need to track piece IDs, health, or types—you just need to know *where* they are.

Here is the exact blueprint for translating your dynamic hexagonal game into blazing-fast C-integers.

### 1. Flattening the Hexagon Grid (Axial Coordinates)
Computers hate hexagons. To use bitboards, we have to map your 2D hexagonal grid into a 1D sequence of bits. 

The industry standard for this is the **Axial Coordinate System**. Instead of an $x$ and $y$ axis at 90 degrees, you use a $q$ axis and an $r$ axis at 60 degrees. 

By assigning a $(q, r)$ coordinate to every possible hexagon position, you can map it to a flat 1D index using a simple formula: 
$index = q + (r \times \text{MAX\_WIDTH})$

If the absolute maximum bounding box your board could ever possibly expand into is $8 \times 8$ (64 total hex spaces), you can map the entire game state into standard 64-bit integers (`cdef unsigned long long`). 

### 2. The Three-Bitboard Solution
Instead of one big integer representing the whole game, you will use **three 64-bit integers**. Each integer represents a layer of truth about the game state. Every `1` means "Yes" and `0` means "No" for that specific grid index.

```cython
cdef struct GameState:
    unsigned long long red_pieces    # Layer 1: Where are the red pieces?
    unsigned long long black_pieces  # Layer 2: Where are the black pieces?
    unsigned long long valid_tiles   # Layer 3: Where are the actual board hexagons?
```

### 3. How to Move Pieces (Bitwise Math)
Let's say a Red piece is at index 12 and wants to move to index 13. You do not create or destroy objects. You use bitwise operations, which process in a fraction of a nanosecond on the CPU.

* **To remove the piece from index 12:** Use Bitwise AND (`&`) with the inverse (`~`).
* **To place the piece at index 13:** Use Bitwise OR (`|`).

```cython
# Cython pseudo-code for moving a red piece
cdef unsigned long long mask_from = 1ULL << 12
cdef unsigned long long mask_to = 1ULL << 13

# Remove from old spot, add to new spot
state.red_pieces = (state.red_pieces & ~mask_from) | mask_to
```

### 4. How to Handle the "Moving Hexagon" Turn
This is the unique mechanic of your game, but with the `valid_tiles` bitboard, it becomes trivially fast. 

When a player chooses to pick up a hexagon and move it, you are simply turning off a bit in the `valid_tiles` integer and turning it back on somewhere else. If there is a piece sitting on that tile, you move its bit in the exact same way.

```cython
# Moving a tile from index 5 to index 20
cdef unsigned long long old_tile = 1ULL << 5
cdef unsigned long long new_tile = 1ULL << 20

# 1. Update the board's physical layout
state.valid_tiles = (state.valid_tiles & ~old_tile) | new_tile

# 2. Check if a Red piece is riding on that tile
if (state.red_pieces & old_tile):
    # Move the piece with the tile
    state.red_pieces = (state.red_pieces & ~old_tile) | new_tile
```

### 5. Validating Legal Moves INSTANTLY
In your old object model, finding legal moves probably involved looping through lists, checking coordinates, and checking neighbors. 

With bitboards, you can check if a move is legal using purely logical ANDs. For example, a tile is only a valid landing spot if it exists AND it is empty:
```cython
cdef unsigned long long empty_tiles = ~(state.red_pieces | state.black_pieces)
cdef unsigned long long legal_destinations = state.valid_tiles & empty_tiles
```

By completely decoupling your "board" from your "pieces" and turning them both into layers of bits, your Cython Minimax will evaluate millions of states per second because it is just doing basic math, completely skipping memory allocation.

## User
It has 19 hexagones originally disposed in a hexagone shape but it could take any shape. The coordinates of the tiles are not bounded but realistically they will never go over 19 length per side hexagone. Usual games dont go over 10 length per side hexagone

## Assistant
This is exactly the kind of constraint where we have to balance theoretical purity with practical engineering. 

Because your game pieces can technically drift infinitely, but realistically won't pass a 19-length side, we have our boundaries. 

Here is the mathematical reality: a single 64-bit integer can only hold 64 tiles. A hexagonal board with a side length (or radius, $R$) of 19 contains $3R(R+1) + 1$ tiles. 
For $R=19$, that is **1,141 possible hex tiles**. 

So, we can't use *one* 64-bit integer. But we can use an incredibly fast, fixed-size **C-Array of 64-bit integers**. A CPU can process an array of 20 integers almost as fast as a single integer because it fits perfectly into the lowest level of the CPU cache (L1 cache).

Here is how you map your drifting, 19-radius hex board into a blistering-fast Cython structure.

### 1. The 40x40 Bounding Box
To handle axial coordinates ($q$ and $r$) that can drift into negative numbers, we need to create a fixed grid and start your initial 19-tile board right in the dead center. 

If the max radius is 19, then $q$ and $r$ will only ever range from $-19$ to $+19$. This means a $40 \times 40$ grid is perfectly large enough to contain any realistic game. 
$40 \times 40 = 1600$ total possible positions.

To hold 1600 bits, we need exactly **25** 64-bit integers ($1600 / 64 = 25$).

### 2. The Multi-Word Bitboard Struct
Instead of a single integer, your Game State now holds three arrays of 25 integers. 

```cython
cdef struct GameState:
    unsigned long long red_pieces[25]
    unsigned long long black_pieces[25]
    unsigned long long valid_tiles[25]
```
This entirely replaces your complex Python objects. The memory footprint of this struct is practically zero (just 600 bytes), meaning you can copy and pass it around your Minimax tree millions of times per second without the garbage collector ever getting involved.

### 3. Translating (Q, R) to Array Indexes

When you want to move a piece or a tile at coordinate $(q, r)$, you have to translate that 2D coordinate into a specific bit inside one of those 25 integers. 

Because we are centering the board, we add an offset of 20 to $q$ and $r$ so they are never negative.

```cython
cdef inline void set_bit(unsigned long long board[25], int q, int r):
    # 1. Shift the coordinates so (0,0) is at the center (20, 20)
    cdef int q_shift = q + 20
    cdef int r_shift = r + 20
    
    # 2. Flatten the 2D coordinate into a 1D index (from 0 to 1599)
    cdef int flat_index = q_shift + (r_shift * 40)
    
    # 3. Find which of the 25 integers holds this bit
    # (Dividing by 64 is automatically optimized to a bit-shift by the C compiler)
    cdef int array_idx = flat_index / 64
    
    # 4. Find the specific bit within that 64-bit integer
    cdef int bit_idx = flat_index % 64
    
    # 5. Flip the bit to 1 using Bitwise OR
    board[array_idx] |= (1ULL << bit_idx)
```

### 4. Moving the "Drifting" Hexagon
When a player picks up a tile at $(q_{old}, r_{old})$ and moves it to $(q_{new}, r_{new})$, you simply calculate the `array_idx` and `bit_idx` for both coordinates. 

You turn the old bit to `0` (using Bitwise AND and NOT) and the new bit to `1` (using Bitwise OR), just like in the previous example, but now applying it to the specific index of the `valid_tiles` array.

```cython
# Turning a bit OFF
board[old_array_idx] &= ~(1ULL << old_bit_idx)

# Turning a bit ON
board[new_array_idx] |= (1ULL << new_bit_idx)
```

### Why This Will Skyrocket Your Speed
1. **No Memory Allocation:** You allocate this struct once. When Minimax branches, you just do a fast C-level memory copy (`memcpy`) of the 600 bytes. 
2. **Instant Evaluation:** To check who is winning, or to count pieces, C compilers have a built-in function to count the number of `1`s in an integer (called "popcount"). You can tally the entire board state in nanoseconds.
3. **Cache Locality:** Because your entire game state is just a contiguous block of primitive numbers, the CPU never has to look up references in RAM. It all lives in the CPU's ultra-fast cache.