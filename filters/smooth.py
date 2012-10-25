from numpy import zeros, array
import itertools
from pymclevel.level import extractHeights

terrainBlocktypes = [1, 2, 3, 7, 12, 13, 14, 15, 16, 56, 73, 74, 87, 88, 89]
terrainBlockmask = zeros((256,), dtype='bool')
terrainBlockmask[terrainBlocktypes] = True

#
inputs = (
    ("Repeat count", (1, 50)),
)


def perform(level, box, options):
    if box.volume > 16000000:
        raise ValueError("Volume too big for this filter method!")

    repeatCount = options["Repeat count"]
    schema = level.extractSchematic(box)
    schema.removeEntitiesInBox(schema.bounds)
    schema.removeTileEntitiesInBox(schema.bounds)

    for i in xrange(repeatCount):

        terrainBlocks = terrainBlockmask[schema.Blocks]

        heightmap = extractHeights(terrainBlocks)

        #terrainBlocks |= schema.Blocks == 0
        nonTerrainBlocks = ~terrainBlocks
        nonTerrainBlocks &= schema.Blocks != 0

        newHeightmap = (heightmap[1:-1, 1:-1] + (heightmap[0:-2, 1:-1] + heightmap[2:, 1:-1] + heightmap[1:-1, 0:-2] + heightmap[1:-1, 2:]) * 0.7) / 3.8
        #heightmap -= 0.5;
        newHeightmap += 0.5
        newHeightmap[newHeightmap < 0] = 0
        newHeightmap[newHeightmap > schema.Height] = schema.Height

        newHeightmap = array(newHeightmap, dtype='uint16')

        for x, z in itertools.product(xrange(1, schema.Width - 1), xrange(1, schema.Length - 1)):
            oh = heightmap[x, z]
            nh = newHeightmap[x - 1, z - 1]
            d = nh - oh

            column = array(schema.Blocks[x, z])
            column[nonTerrainBlocks[x, z]] = 0
            #schema.Blocks[x,z][nonTerrainBlocks[x,z]] = 0

            if nh > oh:

                column[d:] = schema.Blocks[x, z, :-d]
                if d > oh:
                    column[:d] = schema.Blocks[x, z, 0]
            if nh < oh:
                column[:d] = schema.Blocks[x, z, -d:]
                column[d:oh + 1] = schema.Blocks[x, z, min(oh + 1, schema.Height - 1)]

            #preserve non-terrain blocks
            column[~terrainBlockmask[column]] = 0
            column[nonTerrainBlocks[x, z]] = schema.Blocks[x, z][nonTerrainBlocks[x, z]]

            schema.Blocks[x, z] = column

    level.copyBlocksFrom(schema, schema.bounds, box.origin)
