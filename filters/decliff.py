"""
DeCliff filter contributed by Minecraft Forums user "DrRomz"

Originally posted here:
http://www.minecraftforum.net/topic/13807-mcedit-minecraft-world-editor-compatible-with-mc-beta-18/page__st__3940__p__7648793#entry7648793
"""
from numpy import zeros, array
import itertools
from pymclevel import alphaMaterials
am = alphaMaterials

# Consider below materials when determining terrain height
blocks = [
  am.Stone,
  am.Grass,
  am.Dirt,
  am.Bedrock,
  am.Sand,
  am.Sandstone,
  am.Clay,
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
  am.Glowstone
]
terrainBlocktypes = [b.ID for b in blocks]
terrainBlockmask = zeros((256,), dtype='bool')

# Truth table used to calculate terrain height
# trees, leaves, etc. sit on top of terrain
terrainBlockmask[terrainBlocktypes] = True

inputs = (
    # Option to limit change to raise_cliff_floor / lower_cliff_top
    # Default is to adjust both and meet somewhere in the middle
    ("Raise/Lower", ("Both", "Lower Only", "Raise Only")),
)


#
# Calculate the maximum adjustment that can be made from
# cliff_pos in direction dir (-1/1) keeping terain at most
# maxstep blocks away from previous column
def maxadj(heightmap, slice_no, cliff_pos, dir, pushup, maxstep, slice_width):
    ret = 0
    if dir < 0:
        if cliff_pos < 2:
            return 0
        end = 0
    else:
        if cliff_pos > slice_width - 2:
            return 0
        end = slice_width - 1

    for cur_pos in range(cliff_pos, end, dir):
        if pushup:
            ret = ret + \
               max([0, maxstep - dir * heightmap[slice_no, cur_pos] + \
               dir * heightmap[slice_no, cur_pos + dir]])
        else:
            ret = ret + \
               min([0, -maxstep + dir * heightmap[slice_no, cur_pos] - \
               dir * heightmap[slice_no, cur_pos + dir]])

    return ret


#
# Raise/lower column at cliff face by adj and decrement change as we move away
# from the face. Each level will be at most maxstep blocks from those beside it.
#
# This function dosn't actually change anything, but just sets array 'new'
# with the desired height.
def adjheight(orig, new, slice_no, cliff_pos, dir, adj, can_adj, maxstep, slice_width):
    cur_adj = adj
    prev = 0
    done_adj = 0

    if dir < 0:
        end = 1
    else:
        end = slice_width - 1

    if adj == 0 or can_adj == 0:
        for cur_pos in range(cliff_pos, end, dir):
            new[slice_no, cur_pos] = orig[slice_no, cur_pos]
    else:

        for cur_pos in range(cliff_pos, end, dir):
            if adj > 0:
                done_adj = done_adj + \
                           max([0, maxstep - orig[slice_no, cur_pos] + \
                           orig[slice_no, cur_pos + dir]])

                if orig[slice_no, cur_pos] - \
                    orig[slice_no, cur_pos + dir] > 0:
                    cur_adj = max([0, cur_adj - orig[slice_no, cur_pos] + \
                            orig[slice_no, cur_pos + dir]])
                    prev = adj - cur_adj
            else:
                done_adj = done_adj + \
                           min([0, -maxstep + \
                               orig[slice_no, cur_pos] - \
                               orig[slice_no, cur_pos + dir]])
                if orig[slice_no, cur_pos] - \
                   orig[slice_no, cur_pos + dir] > 0:
                    cur_adj = min([0, cur_adj + orig[slice_no, cur_pos] - orig[slice_no, cur_pos + dir]])
                    prev = adj - cur_adj
            new[slice_no, cur_pos] = max([0, orig[slice_no, cur_pos] + cur_adj])
            if cur_adj != 0 and \
               abs(prev) < abs(int(adj * done_adj / can_adj)):
                cur_adj = cur_adj + (prev - int(adj * done_adj / can_adj))
                prev = int(adj * done_adj / can_adj)

    new[slice_no, end] = orig[slice_no, end]


def perform(level, box, options):
    if box.volume > 16000000:
        raise ValueError("Volume too big for this filter method!")

    RLOption = options["Raise/Lower"]
    schema = level.extractSchematic(box)
    schema.removeEntitiesInBox(schema.bounds)
    schema.removeTileEntitiesInBox(schema.bounds)

    terrainBlocks = terrainBlockmask[schema.Blocks]

    coords = terrainBlocks.nonzero()

    # Swap values around so long edge of selected rectangle is first
    # - the long edge is assumed to run parallel to the cliff face
    #   and we want to process slices perpendicular to the face
    #  heightmap will have x,z (or z,x) index with highest ground level
    if schema.Width > schema.Length:
        heightmap = zeros((schema.Width, schema.Length), dtype='float32')
        heightmap[coords[0], coords[1]] = coords[2]
        newHeightmap = zeros((schema.Width, schema.Length), dtype='uint16')
        slice_count = schema.Width
        slice_width = schema.Length
    else:
        heightmap = zeros((schema.Length, schema.Width), dtype='float32')
        heightmap[coords[1], coords[0]] = coords[2]
        newHeightmap = zeros((schema.Length, schema.Width), dtype='uint16')
        slice_count = schema.Length
        slice_width = schema.Width

    nonTerrainBlocks = ~terrainBlocks
    nonTerrainBlocks &= schema.Blocks != 0

    for slice_no in range(0, slice_count):

        cliff_height = 0
        # determine pos and height of cliff in this slice
        for cur_pos in range(0, slice_width - 1):
            if abs(heightmap[slice_no, cur_pos] - \
                   heightmap[slice_no, cur_pos + 1]) > abs(cliff_height):
                cliff_height = \
                   heightmap[slice_no, cur_pos] - \
                   heightmap[slice_no, cur_pos + 1]
                cliff_pos = cur_pos

        if abs(cliff_height) < 2:
            # nothing to adjust - just copy heightmap to newHightmap
            adjheight(heightmap, newHeightmap, slice_no, 0, 1, 0, 1, 1, slice_width)
            continue

        # Try to keep adjusted columns within 1 column of their neighbours
        # but ramp up to 4 blocks up/down on each column when needed
        for max_step in range(1, 4):

            can_left = maxadj(heightmap, slice_no, cliff_pos, -1, cliff_height < 0, max_step, slice_width)
            can_right = maxadj(heightmap, slice_no, cliff_pos + 1, 1, cliff_height > 0, max_step, slice_width)

            if can_right < 0 and RLOption == "Raise Only":
                can_right = 0
            if can_right > 0 and RLOption == "Lower Only":
                can_right = 0
            if can_left < 0 and RLOption == "Raise Only":
                can_left = 0
            if can_left > 0 and RLOption == "Lower Only":
                can_left = 0

            if cliff_height < 0 and can_right - can_left < cliff_height:
                if abs(can_left) > abs(can_right):
                    adj_left = -1 * (cliff_height - max([int(cliff_height / 2), can_right]))
                    adj_right = cliff_height + adj_left
                else:
                    adj_right = cliff_height - max([int(cliff_height / 2), -can_left])
                    adj_left = -1 * (cliff_height - adj_right + 1)
            else:
                if cliff_height > 0 and can_right - can_left > cliff_height:
                    if abs(can_left) > abs(can_right):
                        adj_left = -1 * (cliff_height - min([int(cliff_height / 2), can_right]))
                        adj_right = cliff_height + adj_left
                    else:
                        adj_right = cliff_height - min([int(cliff_height / 2), -can_left]) - 1
                        adj_left = -1 * (cliff_height - adj_right)
                else:
                    adj_right = 0
                    adj_left = 0
                    continue
            break

        adjheight(heightmap, newHeightmap, slice_no, cliff_pos, -1, adj_left, can_left, max_step, slice_width)
        adjheight(heightmap, newHeightmap, slice_no, cliff_pos + 1, 1, adj_right, can_right, max_step, slice_width)

    # OK, newHeightMap has new height for each column
    # so it's just a matter of moving everything up/down
    for x, z in itertools.product(xrange(1, schema.Width - 1), xrange(1, schema.Length - 1)):

        if schema.Width > schema.Length:
            oh = heightmap[x, z]
            nh = newHeightmap[x, z]
        else:
            oh = heightmap[z, x]
            nh = newHeightmap[z, x]

        delta = nh - oh

        column = array(schema.Blocks[x, z])
        # Keep bottom 5 blocks, so we don't loose bedrock
        keep = min([5, nh])

        Waterdepth = 0
        # Detect Water on top
        if column[oh + 1:oh + 2] == am.Water.ID or \
           column[oh + 1:oh + 2] == am.Ice.ID:
            for cur_pos in range(oh + 1, schema.Height):
                if column[cur_pos:cur_pos + 1] != am.Water.ID and \
                  column[cur_pos:cur_pos + 1] != am.Ice.ID: break
                Waterdepth = Waterdepth + 1

        if delta == 0:
            column[oh:] = schema.Blocks[x, z, oh:]

        if delta < 0:
            # Moving column down
            column[keep:delta] = schema.Blocks[x, z, keep - delta:]
            column[delta:] = am.Air.ID
            if Waterdepth > 0:
                # Avoid steping small lakes, etc on cliff top
                # replace with dirt 'n grass
                column[nh:nh + 1] = am.Grass.ID
                column[nh + 1:nh + 1 + delta] = am.Air.ID
        if delta > 0:
            # Moving column up
            column[keep + delta:] = schema.Blocks[x, z, keep:-delta]
            # Put stone in gap at the bottom
            column[keep:keep + delta] = am.Stone.ID

            if Waterdepth > 0:
                if Waterdepth > delta:
                    # Retain Ice
                    if column[nh + Waterdepth:nh + Waterdepth + 1] == am.Ice.ID:
                        column[nh + Waterdepth - delta:nh + 1 + Waterdepth - delta] = \
                            am.Ice.ID
                    column[nh + 1 + Waterdepth - delta:nh + 1 + Waterdepth] = am.Air.ID
                else:
                    if Waterdepth < delta - 2:
                        column[nh:nh + 1] = am.Grass.ID
                        column[nh + 1:nh + 1 + Waterdepth] = am.Air.ID
                    else:
                        # Beach at the edge
                        column[nh - 4:nh - 2] = am.Sandstone.ID
                        column[nh - 2:nh + 1] = am.Sand.ID
                        column[nh + 1:nh + 1 + Waterdepth] = am.Air.ID

        schema.Blocks[x, z] = column

    level.copyBlocksFrom(schema, schema.bounds, box.origin)
