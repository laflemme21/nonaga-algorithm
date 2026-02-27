# cython: language_level=3

cdef class NonagaTilesCoordinates:
    cdef public int q, r, s
    cdef public object island_id

    cpdef object get_island_id(self)
    cpdef tuple get_position(self)
    cpdef int distance_to(self, NonagaTilesCoordinates other)
    cpdef NonagaTilesCoordinates clone(self)


cdef class NonagaTile(NonagaTilesCoordinates):
    cpdef NonagaTile clone(self)


cdef class NonagaPiece(NonagaTile):
    cdef public int color

    cpdef int get_color(self)
    cpdef void set_color(self, int color)
    cpdef NonagaPiece clone(self)


cdef class NonagaIsland:
    cdef public int id
    cdef public set movable_tiles, unmovable_tiles, all_tiles, border_tiles, pieces

    cpdef NonagaIsland clone(self)
    cpdef int get_id(self)
    cpdef int get_number_of_tiles(self)
    cpdef set get_all_tiles(self)
    cpdef set get_movable_tiles(self)
    cpdef set get_pieces(self)
    cdef void _add_tile(self, NonagaTile tile)
    cpdef set _get_tile_coords_set(self, tiles=*)
    cpdef list _get_neighbors(self, NonagaTile tile, set tile_coords_set=*)
    cpdef bint _neighbors_restrain_piece(self, list neighbors)


cdef class NonagaBoard:
    cdef public dict islands
    cdef public list pieces, tiles

    cdef tuple _initialize_board(self)
    cpdef NonagaBoard clone(self)
    cpdef NonagaPiece get_piece(self, tuple position)
    cpdef NonagaTile get_tile(self, tuple position)
    cpdef get_pieces(self, color=*)
