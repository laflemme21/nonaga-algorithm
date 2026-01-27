from nonaga_constants import RED,BLACK

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

        pieces_coord = [((-2, 0, 2),RED), ((-2, 2, 0),BLACK), ((0, 2, -2),RED),
                        ((2, 0, -2),BLACK), ((2, -2, 0),RED), ((0, -2, 2),BLACK)] 
        pieces = [NonagaPiece(q, r, s, color) for (q, r, s), color in pieces_coord]

        # Create the initial island
        self.islands = [NonagaIsland(tiles,pieces)]
        self.pieces = [[0,piece] for piece in pieces]
        self.tiles = [[0,tile] for tile in tiles]
        
        

    def get_state(self):
        """Return the current state of the board for rendering."""
        tiles = [tile for _, tile in self.tiles]
        pieces = [piece for _, piece in self.pieces]
        return {"tiles": tiles, "pieces": pieces}

    def set_state(self, state):
        """Set the board to a given state."""
        # TODO: Implement board state setter
        pass

    def move_piece(self, from_pos, to_pos):
        """Move a piece from one position to another."""
        # TODO: Implement piece movement
        pass

    def move_tile(self, tile, direction):
        """Move a tile in the specified direction."""
        # TODO: Implement tile movement
        pass

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

    def __init__(self, tiles: list["NonagaTile"] = None, pieces: "NonagaPiece" = None):
        """Initialize the island with a list of tiles."""

        self.movable_tiles = []
        self.unmovable_tiles = []
        self.pieces = []

        if tiles is not None:
            self.add_tiles(tiles)
            self.add_pieces(pieces)

    def _add_tile(self, tile: "NonagaTile"):
        """Add a tile to the island."""
        self.movable_tiles.append(tile)

    def add_tile(self, tile: "NonagaTile"):
        """Add a tile to the island."""
        self._add_tile(tile)
        self.update_tiles()
        self.border_tiles = self.movable_tiles + self.unmovable_tiles

    def add_tiles(self, tiles: list["NonagaTile"]):
        """Add multiple tiles to the island."""
        for i in tiles:
            self._add_tile(i)
        self.update_tiles()
        self.border_tiles = self.movable_tiles + self.unmovable_tiles

    def add_piece(self, piece):
        """Add a piece to the island."""
        self.pieces.append(piece)
        self.unmovable_tiles.append(piece)
        self.update_tiles()

    def add_pieces(self, pieces):
        """Add multiple pieces to the island."""
        for p in pieces:
            self.add_piece(p)

    def merge_with(self, other_island):
        """Merge another island into this one."""
        self.add_tiles(other_island.tiles)
        self.add_piece(other_island.pieces)

    def get_tiles(self):
        """Return the list of tiles in the island."""
        return self.tiles

    def remove_tile(self, tile):
        """Remove a tile from the island."""
        self.movable_tiles.remove(tile)
        self.unmovable_tiles.remove(tile)
        self.update_tiles()

    def remove_piece(self, piece):
        """Remove a piece from the island."""
        self.pieces.remove(piece)

    def _get_all_tiles(self):
        """Return all tiles in the island (both movable and unmovable)."""
        return self.movable_tiles + self.unmovable_tiles

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
            tiles = self._get_all_tiles()
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

    def _neighbors_are_connected(self, neighbors: list):
        """Check if the set of neighbors forms a single connected component."""
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

        return len(visited) == len(neighbors)

    def update_tiles(self):
        """Update the list of movable and unmovable tiles based on neighbor count.

        Rules:
        - 5 or 6 neighbors -> unmovable
        - 1 or 2 neighbors -> movable
        - 3 or 4 neighbors -> check if neighbors are connected
        """
        all_tiles = self._get_all_tiles()
        tile_coords_set = self._get_tile_coords_set(all_tiles)
        new_movable = []
        new_unmovable = []

        for tile in all_tiles:
            neighbors = self._get_neighbors(tile, tile_coords_set)
            neighbor_count = len(neighbors)

            if tile in self.pieces:
                new_unmovable.append(tile)
            elif neighbor_count >= 5:
                # 5 or 6 neighbors -> unmovable
                new_unmovable.append(tile)
            elif neighbor_count <= 2:
                # 1 or 2 neighbors -> movable
                new_movable.append(tile)
            else:
                # 3 or 4 neighbors -> check connectivity
                if self._neighbors_are_connected(neighbors):
                    new_movable.append(tile)
                else:
                    new_unmovable.append(tile)

        self.movable_tiles = new_movable
        self.unmovable_tiles = new_unmovable
        self.border_tiles = self.movable_tiles + self.unmovable_tiles


class NonagaTilesCoordinates:
    """Holds the hexagonal coordinates for all tiles on the Nonaga board."""

    def __init__(self, q: int, r: int, s: int):
        """Initialize the tile coordinates."""
        self.q = q  # axial coordinate
        self.r = r  # axial coordinate
        self.s = s  # derived coordinate (s = -q - r)

    def get_position(self):
        """Return the (q, r, s) coordinates as a tuple."""
        return (self.q, self.r, self.s)

    def set_position(self, q: int, r: int, s: int):
        """Set the (q, r, s) coordinates."""
        self.q = q
        self.r = r
        self.s = s

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
        if not isinstance(other, NonagaTile):
            return False
        return self.get_position() == other.get_position()
    
    def __hash__(self):
        """Hash based on position."""
        return hash(self.get_position())
    


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



