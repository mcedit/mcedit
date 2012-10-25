
from numpy import zeros
import itertools
from pymclevel import alphaMaterials
from pymclevel.level import extractHeights

am = alphaMaterials

#naturally occuring materials
blocks = [
  am.Grass,
  am.Dirt,
  am.Stone,
  am.Bedrock,
  am.Sand,
  am.Gravel,
  am.GoldOre,
  am.IronOre,
  am.CoalOre,
  am.LapisLazuliOre,
  am.DiamondOre,
  am.RedstoneOre,
  am.RedstoneOreGlowing,
  am.Netherrack,
  am.SoulSand,
  am.Clay,
  am.Glowstone
]
blocktypes = [b.ID for b in blocks]


def naturalBlockmask():
    blockmask = zeros((256,), dtype='bool')
    blockmask[blocktypes] = True
    return blockmask

inputs = (
  ("Depth", (4, -128, 128)),
  ("Pick a block:", alphaMaterials.Grass),
)


def perform(level, box, options):
    depth = options["Depth"]
    blocktype = options["Pick a block:"]

    #compute a truth table that we can index to find out whether a block
    # is naturally occuring and should be considered in a heightmap
    blockmask = naturalBlockmask()

    # always consider the chosen blocktype to be "naturally occuring" to stop
    # it from adding extra layers
    blockmask[blocktype.ID] = True

    #iterate through the slices of each chunk in the selection box
    for chunk, slices, point in level.getChunkSlices(box):
        # slicing the block array is straightforward. blocks will contain only
        # the area of interest in this chunk.
        blocks = chunk.Blocks[slices]
        data = chunk.Data[slices]

        # use indexing to look up whether or not each block in blocks is
        # naturally-occuring. these blocks will "count" for column height.
        maskedBlocks = blockmask[blocks]

        heightmap = extractHeights(maskedBlocks)

        for x, z in itertools.product(*map(xrange, heightmap.shape)):
            h = heightmap[x, z]
            if depth > 0:
                blocks[x, z, max(0, h - depth):h] = blocktype.ID
                data[x, z, max(0, h - depth):h] = blocktype.blockData
            else:
                #negative depth values mean to put a layer above the surface
                blocks[x, z, h:min(blocks.shape[2], h - depth)] = blocktype.ID
                data[x, z, h:min(blocks.shape[2], h - depth)] = blocktype.blockData

        #remember to do this to make sure the chunk is saved
        chunk.chunkChanged()
