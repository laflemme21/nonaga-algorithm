# cython: language_level=3, boundscheck=False, wraparound=False
from nonaga_constants import RED, BLACK

# ──────────────────────────────────────────────────────────
# Neighbor offsets as a module-level C-array for speed
# ──────────────────────────────────────────────────────────
cdef int NEIGHBOR_OFFSETS[6][3]
NEIGHBOR_OFFSETS[0] = [1, -1,  0]
NEIGHBOR_OFFSETS[1] = [1,  0, -1]
NEIGHBOR_OFFSETS[2] = [0,  1, -1]
NEIGHBOR_OFFSETS[3] = [-1, 1,  0]
NEIGHBOR_OFFSETS[4] = [-1, 0,  1]
NEIGHBOR_OFFSETS[5] = [0, -1,  1]

# Python-visible tuple version (kept for callers that read _NEIGHBOR_OFFSETS)
_PY_NEIGHBOR_OFFSETS = (
    (1, -1, 0),
    (1, 0, -1),
    (0, 1, -1),
    (-1, 1, 0),
    (-1, 0, 1),
    (0, -1, 1),
)


# ══════════════════════════════════════════════════════════
#  NonagaTilesCoordinates
# ══════════════════════════════════════════════════════════
cdef class NonagaTilesCoordinates:
    """Holds the hexagonal coordinates for all tiles on the Nonaga board."""

    cdef public int q, r, s
    cdef public object island_id          # int or None

    def __init__(self, int q, int r, int s):
        self.q = q
        self.r = r
        self.s = s
        self.island_id = None

    cpdef object get_island_id(self):
        return self.island_id

    cpdef tuple get_position(self):
        return (self.q, self.r, self.s)

    def set_position(self, *args):
        """set_position(q, r, s) or set_position((q, r, s))"""
        if len(args) == 1:
            self.q, self.r, self.s = args[0]
        else:
            self.q = args[0]
            self.r = args[1]
            self.s = args[2]

    cpdef int distance_to(self, NonagaTilesCoordinates other):
        cdef int dq = self.q - other.q
        cdef int dr = self.r - other.r
        cdef int ds = self.s - other.s
        if dq < 0: dq = -dq
        if dr < 0: dr = -dr
        if ds < 0: ds = -ds
        return (dq + dr + ds) // 2

    cpdef NonagaTilesCoordinates clone(self):
        cdef NonagaTilesCoordinates c = NonagaTilesCoordinates.__new__(NonagaTilesCoordinates)
        c.q = self.q
        c.r = self.r
        c.s = self.s
        c.island_id = self.island_id
        return c


# ══════════════════════════════════════════════════════════
#  NonagaTile
# ══════════════════════════════════════════════════════════
cdef class NonagaTile(NonagaTilesCoordinates):
    """Represents a tile on the Nonaga board."""

    def __init__(self, int q, int r, int s):
        NonagaTilesCoordinates.__init__(self, q, r, s)

    def __eq__(self, other):
        if isinstance(other, NonagaTile):
            return self.get_position() == (<NonagaTile>other).get_position()
        elif isinstance(other, tuple) and len(<tuple>other) == 3:
            return self.get_position() == other
        return False

    def __hash__(self):
        return hash((self.q, self.r, self.s))

    def __str__(self):
        return f"Tile({self.q}, {self.r}, {self.s})"

    cpdef NonagaTile clone(self):
        cdef NonagaTile c = NonagaTile.__new__(NonagaTile)
        c.q = self.q
        c.r = self.r
        c.s = self.s
        c.island_id = self.island_id
        return c


# ══════════════════════════════════════════════════════════
#  NonagaPiece
# ══════════════════════════════════════════════════════════
cdef class NonagaPiece(NonagaTile):
    """Represents a game piece positioned on a tile."""

    cdef public int color

    def __init__(self, int q, int r, int s, int color):
        NonagaTile.__init__(self, q, r, s)
        self.color = color

    cpdef int get_color(self):
        return self.color

    cpdef void set_color(self, int color):
        self.color = color

    cpdef NonagaPiece clone(self):
        cdef NonagaPiece c = NonagaPiece.__new__(NonagaPiece)
        c.q = self.q
        c.r = self.r
        c.s = self.s
        c.island_id = self.island_id
        c.color = self.color
        return c

    def __str__(self):
        return f"Piece({self.q}, {self.r}, {self.s}, {self.color})"


# ══════════════════════════════════════════════════════════
#  NonagaIsland
# ══════════════════════════════════════════════════════════
cdef class NonagaIsland:
    """Represents an independent group of connected tiles on the Nonaga board."""

    cdef public int id
    cdef public set movable_tiles, unmovable_tiles, all_tiles, border_tiles, pieces

    # Expose the offsets for external readers (e.g. nonaga_logic.py)
    _NEIGHBOR_OFFSETS = _PY_NEIGHBOR_OFFSETS

    def __init__(self, int island_id, list tiles=None, list pieces=None):
        self.id = island_id
        self.movable_tiles = set()
        self.unmovable_tiles = set()
        self.all_tiles = set()
        self.border_tiles = set()
        self.pieces = set()

        if tiles is not None and pieces is not None:
            self.add_tiles(tiles)
            self.add_pieces(pieces)

    # ── clone ────────────────────────────────────────────
    cpdef NonagaIsland clone(self):
        cdef NonagaIsland c = NonagaIsland.__new__(NonagaIsland)
        c.id = self.id
        c.all_tiles = {(<NonagaTile>t).clone() for t in self.all_tiles}
        c.movable_tiles = {(<NonagaTile>t).clone() for t in self.movable_tiles}
        c.unmovable_tiles = {(<NonagaTile>t).clone() for t in self.unmovable_tiles}
        c.border_tiles = {(<NonagaTile>t).clone() for t in self.border_tiles}
        c.pieces = {(<NonagaPiece>p).clone() for p in self.pieces}
        return c

    # ── move operations ─────────────────────────────────
    def move_tile(self, NonagaTile tile, tuple position):
        cdef tuple prev = tile.get_position()
        self.all_tiles.discard(tile)
        tile.set_position(position)
        self.all_tiles.add(tile)
        self.update_tiles([prev, position])

    def move_piece(self, NonagaPiece piece, tuple position):
        cdef tuple prev = piece.get_position()
        self.pieces.discard(piece)
        piece.set_position(position)
        self.pieces.add(piece)
        self.update_tiles([prev, position])

    # ── accessors ────────────────────────────────────────
    cpdef int get_id(self):
        return self.id

    cpdef int get_number_of_tiles(self):
        return len(self.all_tiles)

    cpdef set get_all_tiles(self):
        return self.all_tiles

    cpdef set get_movable_tiles(self):
        return self.movable_tiles

    cpdef set get_pieces(self):
        return self.pieces

    # ── add / remove ─────────────────────────────────────
    cdef void _add_tile(self, NonagaTile tile):
        tile.island_id = self.id
        self.movable_tiles.add(tile)
        self.all_tiles.add(tile)

    def add_tile(self, NonagaTile tile):
        self._add_tile(tile)
        self.update_tiles([tile.get_position()])
        self.border_tiles = self.movable_tiles | self.unmovable_tiles

    def add_tiles(self, list tiles):
        cdef NonagaTile t
        for t in tiles:
            self._add_tile(t)
        self.update_tiles([t.get_position() for t in tiles])
        self.border_tiles = self.movable_tiles | self.unmovable_tiles

    def add_piece(self, NonagaPiece piece):
        piece.island_id = self.id
        self.pieces.add(piece)
        self.unmovable_tiles.add(piece)
        self.update_tiles([piece.get_position()])

    def add_pieces(self, list pieces):
        cdef NonagaPiece p
        for p in pieces:
            self.add_piece(p)

    def merge_with(self, NonagaIsland other):
        self.add_tiles(list(other.all_tiles))
        self.add_pieces(list(other.pieces))

    def remove_tile(self, NonagaTile tile):
        self.movable_tiles.discard(tile)
        self.unmovable_tiles.discard(tile)
        self.update_tiles([tile.get_position()])

    def remove_piece(self, NonagaPiece piece):
        self.pieces.discard(piece)

    # ── neighbor helpers ─────────────────────────────────
    cpdef set _get_tile_coords_set(self, tiles=None):
        if tiles is None:
            tiles = self.all_tiles
        return {(<NonagaTile>t).get_position() for t in tiles}

    cpdef list _get_neighbors(self, NonagaTile tile, set tile_coords_set=None):
        if tile_coords_set is None:
            tile_coords_set = self._get_tile_coords_set()

        cdef int q = tile.q, r = tile.r, s = tile.s
        cdef int i
        cdef tuple pos
        cdef list neighbors = []

        for i in range(6):
            pos = (q + NEIGHBOR_OFFSETS[i][0],
                   r + NEIGHBOR_OFFSETS[i][1],
                   s + NEIGHBOR_OFFSETS[i][2])
            if pos in tile_coords_set:
                neighbors.append(pos)
        return neighbors

    cpdef bint _neighbors_restrain_piece(self, list neighbors):
        if not neighbors:
            return True

        cdef set neighbor_set = set(neighbors)
        cdef tuple start = <tuple>neighbors[0]
        cdef set visited = {start}
        cdef list queue = [start]
        cdef tuple curr, adj_pos
        cdef int cq, cr, cs, i
        cdef int n_neighbors = len(neighbors)

        while queue:
            curr = <tuple>queue.pop(0)
            cq = curr[0]; cr = curr[1]; cs = curr[2]
            for i in range(6):
                adj_pos = (cq + NEIGHBOR_OFFSETS[i][0],
                           cr + NEIGHBOR_OFFSETS[i][1],
                           cs + NEIGHBOR_OFFSETS[i][2])
                if adj_pos in neighbor_set and adj_pos not in visited:
                    visited.add(adj_pos)
                    queue.append(adj_pos)

        cdef int diff = len(visited) - n_neighbors
        if diff < 0:
            diff = -diff
        return len(visited) == n_neighbors or (diff == 1 and n_neighbors == 3)

    # ── update_tiles ─────────────────────────────────────
    def update_tiles(self, list coordinates=None):
        """Update movable / unmovable tiles.

        If *coordinates* is given only those positions and their
        neighbors are re-evaluated (incremental update).
        """
        cdef set all_tiles = self.all_tiles
        cdef set tile_coords_set = self._get_tile_coords_set(all_tiles)
        cdef set tiles_to_update
        cdef set new_movable = set()
        cdef set new_unmovable = set()
        cdef list neighbors
        cdef int neighbor_count
        cdef int q, r, s, i
        cdef tuple coord
        cdef dict tile_by_position

        if coordinates is None:
            tiles_to_update = all_tiles
        else:
            tile_by_position = {(<NonagaTile>t).get_position(): t for t in all_tiles}
            tiles_to_update = set()

            for coord in coordinates:
                q = coord[0]; r = coord[1]; s = coord[2]
                t = tile_by_position.get((q, r, s))
                if t is not None:
                    tiles_to_update.add(t)
                for i in range(6):
                    t = tile_by_position.get((q + NEIGHBOR_OFFSETS[i][0],
                                              r + NEIGHBOR_OFFSETS[i][1],
                                              s + NEIGHBOR_OFFSETS[i][2]))
                    if t is not None:
                        tiles_to_update.add(t)

            if not tiles_to_update:
                return

        for tile in tiles_to_update:
            neighbors = self._get_neighbors(<NonagaTile>tile, tile_coords_set)
            neighbor_count = len(neighbors)

            if tile in self.pieces:
                new_unmovable.add(tile)
            elif neighbor_count >= 5:
                new_unmovable.add(tile)
            elif neighbor_count <= 2:
                new_movable.add(tile)
            else:
                if self._neighbors_restrain_piece(neighbors):
                    new_movable.add(tile)
                else:
                    new_unmovable.add(tile)

        if coordinates is None:
            self.movable_tiles = new_movable
            self.unmovable_tiles = new_unmovable
        else:
            self.movable_tiles.difference_update(tiles_to_update)
            self.unmovable_tiles.difference_update(tiles_to_update)
            self.movable_tiles.update(new_movable)
            self.unmovable_tiles.update(new_unmovable)

        self.border_tiles = self.movable_tiles | self.unmovable_tiles

    # ── dunder ───────────────────────────────────────────
    def __eq__(self, other):
        if isinstance(other, NonagaIsland):
            return self.id == (<NonagaIsland>other).id
        return False

    def __hash__(self):
        return hash(self.id)


# ══════════════════════════════════════════════════════════
#  NonagaBoard
# ══════════════════════════════════════════════════════════
cdef class NonagaBoard:
    """Represents the state of the Nonaga game board."""

    cdef public dict islands
    cdef public list pieces, tiles

    def __init__(self, bint new_game=True):
        cdef list tiles, pieces
        if new_game:
            tiles, pieces = self._initialize_board()
        else:
            tiles = []
            pieces = []

        cdef NonagaIsland island = NonagaIsland(island_id=0, tiles=tiles, pieces=pieces)
        self.islands = {0: island}
        self.pieces = pieces
        self.tiles = tiles

    cdef tuple _initialize_board(self):
        cdef list coords = []
        cdef int radius = 2
        cdef int q, r, r_start, r_end

        for q in range(-radius, radius + 1):
            r_start = -radius if -q - radius < -radius else -q - radius
            r_end = radius if -q + radius > radius else -q + radius
            for r in range(r_start, r_end + 1):
                coords.append((q, r, -q - r))

        cdef list tiles = [NonagaTile(q, r, s) for q, r, s in coords]

        cdef list pieces_coord = [
            ((-2,  0,  2), RED),
            ((-2,  2,  0), BLACK),
            (( 0,  2, -2), RED),
            (( 2,  0, -2), BLACK),
            (( 2, -2,  0), RED),
            (( 0, -2,  2), BLACK),
        ]
        cdef list pieces = [NonagaPiece(q, r, s, color)
                            for (q, r, s), color in pieces_coord]
        return tiles, pieces

    # Keep the public name expected by the rest of the codebase
    def initialize_board(self):
        return self._initialize_board()

    cpdef NonagaBoard clone(self):
        cdef NonagaBoard c = NonagaBoard.__new__(NonagaBoard, False)
        c.islands = {iid: (<NonagaIsland>isl).clone() for iid, isl in self.islands.items()}
        c.pieces = [(<NonagaPiece>p).clone() for p in self.pieces]
        c.tiles = [(<NonagaTile>t).clone() for t in self.tiles]
        return c

    cpdef NonagaPiece get_piece(self, tuple position):
        cdef NonagaPiece p
        for p in self.pieces:
            if p.get_position() == position:
                return p
        return None

    cpdef NonagaTile get_tile(self, tuple position):
        cdef NonagaTile t
        for t in self.tiles:
            if t.get_position() == position:
                return t
        return None

    def get_pieces(self, color=None):
        if color is None:
            return self.pieces
        return [p for p in self.pieces if (<NonagaPiece>p).color == color]

    def get_state(self):
        return {"tiles": self.tiles, "pieces": self.pieces}

    def set_state(self, state):
        pass

    def move_piece(self, NonagaPiece piece, tuple position):
        cdef NonagaIsland island = <NonagaIsland>self.islands[piece.island_id]
        island.move_piece(piece, position)

    def move_tile(self, NonagaTile tile, tuple position):
        cdef NonagaIsland island = <NonagaIsland>self.islands[tile.island_id]
        island.move_tile(tile, position)

    def create_island(self):
        pass

    def merge_islands(self):
        pass
