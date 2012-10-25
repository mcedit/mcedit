
from numpy import zeros, array
import itertools

#naturally occuring materials
from pymclevel.level import extractHeights

blocktypes = [1, 2, 3, 7, 12, 13, 14, 15, 16, 56, 73, 74, 87, 88, 89]
blockmask = zeros((256,), dtype='bool')

#compute a truth table that we can index to find out whether a block
# is naturally occuring and should be considered in a heightmap
blockmask[blocktypes] = True

displayName = "Chunk Surface Repair"

inputs = (
  ("Repairs the backwards surfaces made by old versions of Minecraft.", "label"),
)


def perform(level, box, options):

    #iterate through the slices of each chunk in the selection box
    for chunk, slices, point in level.getChunkSlices(box):
        # slicing the block array is straightforward. blocks will contain only
        # the area of interest in this chunk.
        blocks = chunk.Blocks
        data = chunk.Data

        # use indexing to look up whether or not each block in blocks is
        # naturally-occuring. these blocks will "count" for column height.
        maskedBlocks = blockmask[blocks]

        heightmap = extractHeights(maskedBlocks)

        for x in range(heightmap.shape[0]):
            for z in range(x + 1, heightmap.shape[1]):

                h = heightmap[x, z]
                h2 = heightmap[z, x]

                b2 = blocks[z, x, h2]

                if blocks[x, z, h] == 1:
                    h += 2  # rock surface - top 4 layers become 2 air and 2 rock
                if blocks[z, x, h2] == 1:
                    h2 += 2  # rock surface - top 4 layers become 2 air and 2 rock

                # topsoil is 4 layers deep
                def swap(s1, s2):
                    a2 = array(s2)
                    s2[:] = s1[:]
                    s1[:] = a2[:]

                swap(blocks[x, z, h - 3:h + 1], blocks[z, x, h2 - 3:h2 + 1])
                swap(data[x, z, h - 3:h + 1], data[z, x, h2 - 3:h2 + 1])

        # remember to do this to make sure the chunk is saved
        chunk.chunkChanged()
