from nonaga_constants import RED, BLACK


class NonagaBoard:
    """Represents the state of the Nonaga game board."""

    def __init__(self):
        """Initialize the board state."""

        """Create the initial board with islands, tiles, and pieces."""

        # Create a list of (q, r) axial coordinates for a hexagonal grid.
        coords = []
        radius = 2  # Default radius for the hexagonal board

        # q is the column-like axis
        for q in range(-radius, radius + 1):
            # r is the row-like axis, constrained to keep the shape hexagonal
            r_start = max(-radius, -q - radius)
            r_end = min(radius, -q + radius)

            for r in range(r_start, r_end + 1):
                coords.append((q, r, -q - r))  # s is derived as -q - r

        tiles = [NonagaTile(q, r, s)
                 for q, r, s in coords]

        pieces_coord = [((-2, 0, 2), RED), ((-2, 2, 0), BLACK), ((0, 2, -2), RED),
                        ((2, 0, -2), BLACK), ((2, -2, 0), RED), ((0, -2, 2), BLACK)]
        pieces = [NonagaPiece(q, r, s, color)
                  for (q, r, s), color in pieces_coord]

        # Create the initial island with id 0
        island = NonagaIsland(island_id=0, tiles=tiles, pieces=pieces)
        self.islands = {0: island}
        self.pieces = pieces
        self.tiles = tiles
        
    def get_piece(self, position: tuple[int, int, int])-> "NonagaPiece":
        """Return the piece at the given position, or None if there is no piece."""
        for piece in self.pieces:
            if piece.get_position() == position:
                return piece
        return None

    def get_tile(self, position: tuple[int, int, int])-> "NonagaTile":
        """Return the tile at the given position, or None if there is no tile."""
        for tile in self.tiles:
            if tile.get_position() == position:
                return tile
        return None

    def get_pieces(self,color=None):
        """Return the list of pieces on the board."""
        if color is None:
            return self.pieces
        else:
            return [piece for piece in self.pieces if piece.color == color]

    def get_state(self):
        """Return the current state of the board for rendering."""
        return {"tiles": self.tiles, "pieces": self.pieces}

    def set_state(self, state):
        """Set the board to a given state."""
        # TODO: Implement board state setter
        pass

    def move_piece(self, piece: "NonagaPiece", position: tuple[int, int, int]):
        """Move a piece from one position to another."""

        island: NonagaIsland = self.islands[piece.get_island_id()]
        island.move_piece(piece, position)

    def move_tile(self, tile: "NonagaTile", position: tuple[int, int, int]):
        """Move a tile in the specified position."""
        island: NonagaIsland = self.islands[tile.get_island_id()]
        island.move_tile(tile, position)
        
    

    def create_island(self):
        """Encapsulate an island on the board."""
        # TODO: Implement island creation
        pass

    def merge_islands(self):
        """Merge adjacent islands."""
        # TODO: Implement island merging
        pass


class NonagaIsland:
    """Represents an independant group of connected tiles on the Nonaga board."""

    def __init__(self, island_id: int, tiles: list["NonagaTile"] = None, pieces: list["NonagaPiece"] = None):
        """Initialize the island with a list of tiles."""

        self.id = island_id
        self.movable_tiles = set([])
        self.unmovable_tiles = set([])
        self.all_tiles = set([])
        self.border_tiles = set([])
        self.pieces = set([])

        if tiles is not None and pieces is not None:
            self.add_tiles(tiles)
            self.add_pieces(pieces)

    def move_tile(self, tile: "NonagaTile", position: tuple[int, int, int]):
        """Move a tile to a new position."""
        self.all_tiles.remove(tile)
        tile.set_position(position)
        self.all_tiles.add(tile)
        self.update_tiles()

    def move_piece(self, piece: "NonagaPiece", position: tuple[int, int, int]):
        """Move a piece to a new position."""
        self.pieces.remove(piece)
        piece.set_position(position)
        self.pieces.add(piece)
        self.update_tiles()  # can be optimised to only update affected tiles

    def get_id(self):
        """Return the island's unique identifier."""
        return self.id

    def get_number_of_tiles(self):
        """Return the number of tiles in the island."""
        return len(self.all_tiles)

    def get_all_tiles(self):
        """Return the list of all tiles in the island."""
        return self.all_tiles

    def _add_tile(self, tile: "NonagaTile"):
        """Add a tile to the island."""
        tile.island_id = self.id
        self.movable_tiles.add(tile)
        self.all_tiles.add(tile)

    def add_tile(self, tile: "NonagaTile"):
        """Add a tile to the island."""
        self._add_tile(tile)
        self.update_tiles()
        self.border_tiles = self.movable_tiles.union(self.unmovable_tiles)

    def add_tiles(self, tiles: list["NonagaTile"]):
        """Add multiple tiles to the island."""
        for i in tiles:
            self._add_tile(i)
        self.update_tiles()
        self.border_tiles = self.movable_tiles.union(self.unmovable_tiles)

    def add_piece(self, piece: "NonagaPiece"):
        """Add a piece to the island."""
        piece.island_id = self.id
        self.pieces.add(piece)
        self.unmovable_tiles.add(piece)
        self.update_tiles()

    def add_pieces(self, pieces: list["NonagaPiece"]):
        """Add multiple pieces to the island."""
        for p in pieces:
            self.add_piece(p)

    def merge_with(self, other_island):
        """Merge another island into this one."""
        self.add_tiles(other_island.all_tiles)
        self.add_pieces(other_island.pieces)

    def get_movable_tiles(self):
        """Return the list of tiles in the island."""
        return self.movable_tiles

    def remove_tile(self, tile):
        """Remove a tile from the island."""
        self.movable_tiles.remove(tile)
        self.unmovable_tiles.remove(tile)
        self.update_tiles()

    def remove_piece(self, piece):
        """Remove a piece from the island."""
        self.pieces.remove(piece)

    def get_pieces(self):
        """Return the list of pieces in the island."""
        return self.pieces

    def _get_neighbor_offsets(self):
        """Return the 6 neighbor offsets in cube coordinates (q, r, s)."""
        return [
            (1, -1, 0),
            (1, 0, -1),
            (0, 1, -1),
            (-1, 1, 0),
            (-1, 0, 1),
            (0, -1, 1)
        ]

    def _get_tile_coords_set(self, tiles: list["NonagaTile"] = None):
        """Return a set of coordinate tuples for all tiles in the island or the given tiles."""
        if tiles is None:
            tiles = self.all_tiles
        return {tile.get_position() for tile in tiles}

    def _get_neighbors(self, tile: "NonagaTile", tile_coords_set: set = None):
        """Return a list of coordinates of neighboring tiles."""
        if tile_coords_set is None:
            tile_coords_set = self._get_tile_coords_set()

        tile_coords = tile.get_position()
        neighbor_offsets = self._get_neighbor_offsets()

        neighbors = []
        for offset in neighbor_offsets:
            neighbor_pos = (
                tile_coords[0] + offset[0],
                tile_coords[1] + offset[1],
                tile_coords[2] + offset[2]
            )
            if neighbor_pos in tile_coords_set:
                neighbors.append(neighbor_pos)

        return neighbors

    def _neighbors_restrain_piece(self, neighbors: list):
        """Check if the set of neighbors forms blocks the piece from moving"""
        if not neighbors:
            return True

        neighbor_set = set(neighbors)
        start = neighbors[0]
        visited = {start}
        queue = [start]

        neighbor_offsets = self._get_neighbor_offsets()

        while queue:
            curr = queue.pop(0)
            for offset in neighbor_offsets:
                adj_pos = (
                    curr[0] + offset[0],
                    curr[1] + offset[1],
                    curr[2] + offset[2]
                )
                if adj_pos in neighbor_set and adj_pos not in visited:
                    visited.add(adj_pos)
                    queue.append(adj_pos)

        # Special case for 3 neighbors where one can be removed without disconnecting
        return len(visited) == len(neighbors) or (abs(len(visited)-len(neighbors)) == 1 and neighbors.__len__() == 3)

    def update_tiles(self):
        """Update the list of movable and unmovable tiles based on neighbor count.

        Rules:
        - 5 or 6 neighbors -> unmovable
        - 1 or 2 neighbors -> movable
        - 3 or 4 neighbors -> check if neighbors are connected
        """
        all_tiles = self.all_tiles
        tile_coords_set = self._get_tile_coords_set(all_tiles)
        new_movable = set([])
        new_unmovable = set([])

        for tile in all_tiles:
            neighbors = self._get_neighbors(tile, tile_coords_set)
            neighbor_count = len(neighbors)

            if tile in self.pieces:
                new_unmovable.add(tile)
            elif neighbor_count >= 5:
                # 5 or 6 neighbors -> unmovable
                new_unmovable.add(tile)
            elif neighbor_count <= 2:
                # 1 or 2 neighbors -> movable
                new_movable.add(tile)
            else:
                # 3 or 4 neighbors -> check connectivity
                if self._neighbors_restrain_piece(neighbors):
                    new_movable.add(tile)
                else:
                    new_unmovable.add(tile)

        self.movable_tiles = new_movable
        self.unmovable_tiles = new_unmovable
        self.border_tiles = self.movable_tiles.union(self.unmovable_tiles)

    def __eq__(self, other):
        """Check equality based on position."""
        if isinstance(other, NonagaIsland):
            return self.get_id() == other.get_id()
        return False

    def __hash__(self):
        """Hash based on position."""
        return hash(self.id)


class NonagaTilesCoordinates:
    """Holds the hexagonal coordinates for all tiles on the Nonaga board."""

    def __init__(self, q: int, r: int, s: int):
        """Initialize the tile coordinates."""
        self.q = q  # axial coordinate
        self.r = r  # axial coordinate
        self.s = s  # derived coordinate (s = -q - r)
        self.island_id = None  # Will be set when added to an island

    def get_island_id(self):
        """Return the island ID that this tile belongs to."""
        return self.island_id

    def get_position(self):
        """Return the (q, r, s) coordinates as a tuple."""
        return (self.q, self.r, self.s)

    def set_position(self, q: int, r: int, s: int):
        """Set the (q, r, s) coordinates."""
        self.q = q
        self.r = r
        self.s = s

    def set_position(self, position: tuple[int, int, int]):
        """Set the (q, r, s) coordinates from a tuple."""
        self.q, self.r, self.s = position

    def distance_to(self, other: "NonagaTilesCoordinates"):
        """Calculate the distance to another tile using hexagonal distance formula."""
        return (abs(self.q - other.q) + abs(self.r - other.r) + abs(self.s - other.s)) // 2


class NonagaTile(NonagaTilesCoordinates):
    """Represents a tile on the Nonaga board."""

    def __init__(self, q: int, r: int, s: int):
        """Initialize the tile with its position."""
        super().__init__(q, r, s)

    def __eq__(self, other):
        """Check equality based on position."""
        if isinstance(other, NonagaTile):
            return self.get_position() == other.get_position()
        elif isinstance(other, tuple) and len(other) == 3:
            return self.get_position() == other
        return False

    def __hash__(self):
        """Hash based on position."""
        return hash(self.get_position())

    def __str__(self):
        """String representation of the tile."""
        return f"Tile({self.q}, {self.r}, {self.s})"


class NonagaPiece(NonagaTile):
    """Represents a game piece positioned on a tile on the Nonaga board, inherits from NonagaTile."""

    def __init__(self, q, r, s, color):
        """Initialize the piece with its position and color."""
        super().__init__(q, r, s)
        self.color = color  # "red" or "black"

    def get_color(self):
        """Return the color of the piece."""
        return self.color

    def set_color(self, color):
        """Set the color of the piece."""
        self.color = color

    def __str__(self):
        """String representation of the piece."""
        return f"Piece({self.q}, {self.r}, {self.s}, {self.color})"
