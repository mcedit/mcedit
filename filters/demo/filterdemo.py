
# the inputs list tells MCEdit what kind of options to present to the user.
# each item is a (name, value) pair.  name is a text string acting
# both as a text label for the input on-screen and a key for the 'options'
# parameter to perform(). value and its type indicate allowable and
# default values for the option:

#    True or False:  creates a checkbox with the given value as default
#    int or float value: creates a value input with the given value as default
#        int values create fields that only accept integers.
#    tuple of numbers: a tuple of ints or floats creates a value input with minimum and
#        maximum values. a 2-tuple specifies (min, max) with min as default.
#        a 3-tuple specifies (default, min, max)
#    tuple of strings: a tuple of strings creates a popup menu whose entries are
#        labeled with the given strings. the first item in the tuple is selected
#        by default. returns one of the strings in the tuple.
#    "blocktype" as a string: creates a button the user can click to choose
#        a block type in a list. returns a Block object. the object has 'ID'
#        and 'blockData' attributes.

# this dictionary creates an integer input with range (-128, 128) and default 4,
# a blocktype picker, a floating-point input with no limits and default 15.0,
# a checkbox initially checked, and a menu of choices

inputs = (
  ("Depth", (4, -128, 128)),
  ("Pick a block:", "blocktype"),
  ("Fractal complexity", 15.0),
  ("Enable thrusters", True),
  ("Access method", ("Use blockAt", "Use temp schematic", "Use chunk slices")),
)

# perform() is the main entry point of a filter. Its parameters are
# a MCLevel instance, a BoundingBox, and an options dictionary.
# The options dictionary will have keys corresponding to the keys specified above,
# and values reflecting the user's input.

# you get undo for free: everything within 'box' is copied to a temporary buffer
# before perform is called, and then copied back when the user asks to undo


def perform(level, box, options):
    blockType = options["Pick a block:"].ID
    complexity = options["Fractal complexity"]
    if options["Enable thrusters"]:
        # Errors will alert the user and print a traceback to the console.
        raise NotImplementedError("Thrusters not attached!")

    method = options["Access method"]

    # There are a few general ways of accessing a level's blocks
    # The first is using level.blockAt and level.setBlockAt
    # These are slower than the other two methods, but easier to start using
    if method == "Use blockAt":
        for x in xrange(box.minx, box.maxx):
            for z in xrange(box.minz, box.maxz):
                for y in xrange(box.miny, box.maxy):  # nested loops can be slow

                    # replaces gold with TNT. straightforward.
                    if level.blockAt(x, y, z) == 14:
                        level.setBlockAt(x, y, z, 46)


    # The second is to extract the segment of interest into a contiguous array
    # using level.extractSchematic. this simplifies using numpy but at the cost
    # of the temporary buffer and the risk of a memory error on 32-bit systems.

    if method == "Use temp schematic":
        temp = level.extractSchematic(box)

        # remove any entities in the temp.  this is an ugly move
        # because copyBlocksFrom actually copies blocks, entities, everything
        temp.removeEntitiesInBox(temp.bounds)
        temp.removeTileEntitiesInBox(temp.bounds)

        # replaces gold with TNT.
        # the expression in [] creates a temporary the same size, using more memory
        temp.Blocks[temp.Blocks == 14] = 46

        level.copyBlocksFrom(temp, temp.bounds, box.origin)

    # The third method iterates over each subslice of every chunk in the area
    # using level.getChunkSlices. this method is a bit arcane, but lets you
    # visit the affected area chunk by chunk without using too much memory.

    if method == "Use chunk slices":
        for (chunk, slices, point) in level.getChunkSlices(box):
            # chunk is an AnvilChunk object with attributes:
            # Blocks, Data, Entities, and TileEntities
            # Blocks and Data can be indexed using slices:
            blocks = chunk.Blocks[slices]

            # blocks now contains a "view" on the part of the chunk's blocks
            # that lie in the selection. This "view" is a numpy object that
            # accesses only a subsection of the original array, without copying

            # once again, gold into TNT
            blocks[blocks == 14] = 46

            # notify the world that the chunk changed
            # this gives finer control over which chunks are dirtied
            # you can call chunk.chunkChanged(False) if you want to dirty it
            # but not run the lighting calc later.

            chunk.chunkChanged()

    # You can also access the level any way you want
    # Beware though, you only get to undo the area within the specified box

    pos = level.getPlayerPosition()
    cpos = pos[0] >> 4, pos[2] >> 4
    chunk = level.getChunk(*cpos)
    chunk.Blocks[::4, ::4, :64] = 46  # replace every 4x4th column of land with TNT
