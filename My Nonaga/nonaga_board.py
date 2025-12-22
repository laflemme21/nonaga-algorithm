class NonagaBoard:
    """Represents the state of the Nonaga game board."""

    def __init__(self):
        """Initialize the board state."""
        self.islands: list = self._create_initial_board()  # List of islands on the board
    
        pass

    def get_state(self):
        """Return the current state of the board."""
        pass

    def set_state(self, state):
        """Set the board to a given state."""
        pass
    
    def move_piece(self, from_pos, to_pos):
        """Move a piece from one position to another."""
        pass
    
    def move_tile(self, tile, direction):
        """Move a tile in the specified direction."""
        pass
    
    def create_island(self):
        """Encapsulate an island on the board."""
        pass
    
    def merge_islands(self):
        """Merge adjacent islands."""
        pass
    
class NonagaIsland:
    """Represents an independant group of connected tiles on the Nonaga board."""

    def __init__(self, tiles : "NonagaTile" = None, pieces : "NonagaPiece" = None):
        """Initialize the island with a list of tiles."""
        self.tiles = tiles if tiles is not None else []
        self.pieces = pieces if pieces is not None else []
    
    def add_tile(self, tile):
        """Add a tile to the island."""
        self.tiles.append(tile)
    
    def remove_tile(self, tile):
        """Remove a tile from the island."""
        self.tiles.remove(tile)
    
    def get_tiles(self):
        """Return the list of tiles in the island."""
        return self.tiles
    
    def add_piece(self, piece):
        """Add a piece to the island."""
        self.pieces.append(piece)
    
    def remove_piece(self, piece):
        """Remove a piece from the island."""
        self.pieces.remove(piece)
    
class NonagaTile:
    """Represents a tile on the Nonaga board."""

    def __init__(self, position: "NonagaTilesCoordinates"):
        """Initialize the tile with its position and optional color."""
        self.position = position  # (q, r, s) hexagonal coordinates
    
    def set_color(self, color):
        """Set the color of the tile."""
        self.color = color

    def set_position(self, position: "NonagaTilesCoordinates"):
        """Set the position of the tile."""
        self.position = position
        
    def set_position(self, position: tuple[int, int, int]):
        """Set the position of the tile."""
        self.position.set_coordinates(*position)
        
    def get_color(self):
        """Get the color of the tile."""
        return self.color
    
    def get_position(self):
        """Get the position of the tile."""
        return self.position
    
    

    
class NonagaPiece(NonagaTile):
    """Represents a game piece positioned on a tile on the Nonaga board, inherits from NonagaTile."""

    def __init__(self, position, color):
        """Initialize the piece with its position and color."""
        super().__init__(position)
        self.color = color  # "red" or "black"
        
class NonagaTilesCoordinates:
    """Holds the hexagonal coordinates for all tiles on the Nonaga board."""
    
    def __init__(self, q: int, r: int, s: int):
        """Initialize the tile coordinates."""
        self.q = q  # axial coordinate
        self.r = r  # axial coordinate
        self.s = s  # derived coordinate (s = -q - r)
        
    def get_coordinates(self):
        """Return the (q, r, s) coordinates as a tuple."""
        return (self.q, self.r, self.s)
    
    def set_coordinates(self, q: int, r: int, s: int):
        """Set the (q, r, s) coordinates."""
        self.q = q
        self.r = r
        self.s = s
        
    def distance_to(self, other: "NonagaTilesCoordinates"):
        """Calculate the distance to another tile using hexagonal distance formula."""
        return (abs(self.q - other.q) + abs(self.r - other.r) + abs(self.s - other.s)) // 2
    
    