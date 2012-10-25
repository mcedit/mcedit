def perform(level, box, options):
    groups = RedstoneGroups(level)
    
    for x in xrange(box.minx, box.maxx):
        for y in xrange(box.miny, box.maxy):
            for z in xrange(box.minz, box.maxz):
                groups.testblock((x, y, z))

    groups.changeBlocks()

    

TransparentBlocks = [0, 6, 8, 9, 10, 11, 18, 20, 26, 27, 28, 29, 30, 31, 32, 33, 34, 36, 37, 38, 39, 40, 44, 46, 50, 51, 52, 53, 54, 55, 59, 60, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 75, 76, 77, 78, 79, 81, 83, 85, 89, 90, 92, 93, 94, 95, 96, 97, 101, 102, 104, 105, 106, 107, 108, 109, 111, 113, 114, 115, 116, 117, 118, 119, 120, 122, 126, 127]

class RedstoneGroups:
    group = {}
    currentgroup = 0

    def __init__(self, level):
        self.level = level

    def isRedstone(self, blockid):
        return blockid == 55 or blockid == 93 or blockid == 94

    def testblock(self, pos):
        (x, y, z) = pos
        blockid = self.level.blockAt(x, y, z)
        if self.isRedstone(blockid):
            if (x, y, z) in self.group:
                return
            self.group[pos] = self.currentgroup
            self.testneighbors(pos)
            self.currentgroup = self.currentgroup + 1

    def testneighbors(self, (x, y, z)):
        for dy in xrange(-1, 2, 1):
            if y + dy >= 0 and y + dy <= 255:
                self.testneighbor((x, y, z), (x-1, y+dy, z))
                self.testneighbor((x, y, z), (x+1, y+dy, z))
                self.testneighbor((x, y, z), (x, y+dy, z-1))
                self.testneighbor((x, y, z), (x, y+dy, z+1))

    def testneighbor(self, pos1, pos2):
        if pos2 in self.group:
            return

        if self.connected(pos1, pos2):
            self.group[pos2] = self.currentgroup
            self.testneighbors(pos2)

    def getBlockAt(self, (x, y, z)):
        return self.level.blockAt(x, y, z)

    def repeaterAlignedWith(self, (x1, y1, z1), (x2, y2, z2)):
        blockid = self.getBlockAt((x1, y1, z1))
        if blockid != 93 and blockid != 94:
            return False

        direction = self.level.blockDataAt(x1, y1, z1) % 4

        if (direction == 0 or direction == 2) and abs(z2 - z1) != 1:
            return False
        elif (direction == 1 or direction == 3) and abs(x2 - x1) != 1:
            return False

        return True

    def repeaterPointingTowards(self, (x1, y1, z1), (x2, y2, z2)):
        blockid = self.getBlockAt((x1, y1, z1))
        if blockid != 93 and blockid != 94:
            return False

        direction = self.level.blockDataAt(x1, y1, z1) % 4

        if direction == 0 and z2 - z1 == -1:
            return True
        if direction == 1 and x2 - x1 == 1:
            return True
        if direction == 2 and z2 - z1 == 1:
            return True
        if direction == 3 and x2 - x1 == -1:
            return True

        return False

    def repeaterPointingAway(self, (x1, y1, z1), (x2, y2, z2)):
        blockid = self.getBlockAt((x1, y1, z1))
        if blockid != 93 and blockid != 94:
            return False

        direction = self.level.blockDataAt(x1, y1, z1) % 4

        if direction == 0 and z2 - z1 == 1:
            return True
        if direction == 1 and x2 - x1 == -1:
            return True
        if direction == 2 and z2 - z1 == -1:
            return True
        if direction == 3 and x2 - x1 == 1:
            return True

        return False
    

    def connected(self, (x1, y1, z1), (x2, y2, z2)):
        blockid1 = self.level.blockAt(x1, y1, z1)
        blockid2 = self.level.blockAt(x2, y2, z2)

        pos1 = (x1, y1, z1)
        pos2 = (x2, y2, z2)
        
        if y1 == y2:
            if blockid1 == 55:
                if blockid2 == 55:
                    return True
                elif self.repeaterAlignedWith(pos2, pos1):
                    return True                    
            elif self.repeaterAlignedWith(pos1, pos2) and blockid2 == 55:
                return True
            elif self.repeaterPointingTowards(pos1, pos2) and self.repeaterPointingAway(pos2, pos1):
                return True
            elif self.repeaterPointingAway(pos1, pos2) and self.repeaterPointingTowards(pos2, pos1):
                return True
        elif y2 == y1 - 1:
            aboveid = self.level.blockAt(x2, y2+1, z2)
            
            if blockid1 == 55:
                if blockid2 == 55 and TransparentBlocks.count(aboveid) == 1:
                    return True
                elif self.repeaterAlignedWith(pos2, pos1):
                    return True
            elif self.repeaterPointingTowards(pos1, pos2):
                if blockid2 == 55 and TransparentBlocks.count(aboveid) == 0:
                    return True
        elif y2 == y1 + 1:
            return self.connected(pos2, pos1)

        return False

    SkipBlocks = [23, 61, 62, 89]

    def changeBlocks(self):
        for ((x, y, z), gr) in self.group.items():
            if y > 0:
                blockid = self.level.blockAt(x, y-1, z)
                if self.SkipBlocks.count(blockid) == 1:
                    continue
                self.level.setBlockAt(x, y-1, z, 35)
                self.level.setBlockDataAt(x, y-1, z, gr % 16)
                self.level.getChunk(x / 16, z / 16).dirty = True
