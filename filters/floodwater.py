from numpy import *
from pymclevel import alphaMaterials, faceDirections, FaceYIncreasing
from collections import deque
import datetime

displayName = "Classic Water Flood"
inputs = (
  ("Makes water in the region flood outwards and downwards, becoming full source blocks in the process. This is similar to Minecraft Classic water.", "label"),
  ("Flood Water", True),
  ("Flood Lava", False),
)


def perform(level, box, options):

    def floodFluid(waterIDs, waterID):
        waterTable = zeros(256, dtype='bool')
        waterTable[waterIDs] = True

        coords = []
        for chunk, slices, point in level.getChunkSlices(box):
            water = waterTable[chunk.Blocks[slices]]
            chunk.Data[slices][water] = 0  # source block

            x, z, y = water.nonzero()
            x = x + (point[0] + box.minx)
            z = z + (point[2] + box.minz)
            y = y + (point[1] + box.miny)
            coords.append(transpose((x, y, z)))

        print "Stacking coords..."
        coords = vstack(tuple(coords))

        def processCoords(coords):
            newcoords = deque()

            for (x, y, z) in coords:
                for _dir, offsets in faceDirections:
                    if _dir == FaceYIncreasing:
                        continue

                    dx, dy, dz = offsets
                    p = (x + dx, y + dy, z + dz)
                    if p not in box:
                        continue

                    nx, ny, nz = p
                    if level.blockAt(nx, ny, nz) == 0:
                        level.setBlockAt(nx, ny, nz, waterID)
                        newcoords.append(p)

            return newcoords

        def spread(coords):
            while len(coords):
                start = datetime.datetime.now()

                num = len(coords)
                print "Did {0} coords in ".format(num),
                coords = processCoords(coords)
                d = datetime.datetime.now() - start
                print d
                yield "Did {0} coords in {1}".format(num, d)

        level.showProgress("Spreading water...", spread(coords), cancel=True)

    if options["Flood Water"]:
        waterIDs = [alphaMaterials.WaterActive.ID, alphaMaterials.Water.ID]
        waterID = alphaMaterials.Water.ID
        floodFluid(waterIDs, waterID)
    if options["Flood Lava"]:
        lavaIDs = [alphaMaterials.LavaActive.ID, alphaMaterials.Lava.ID]
        lavaID = alphaMaterials.Lava.ID
        floodFluid(lavaIDs, lavaID)
