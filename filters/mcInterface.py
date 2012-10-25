#dummy mcInterface to adapt dudecon's interface to MCEdit's


class MCLevelAdapter(object):
    def __init__(self, level, box):
        self.level = level
        self.box = box

    def check_box_2d(self, x, z):
        box = self.box
        if x < box.minx or x >= box.maxx:
            return False
        if z < box.minz or z >= box.maxz:
            return False
        return True

    def check_box_3d(self, x, y, z):
        '''If the coordinates are within the box, return True, else return False'''
        box = self.box
        if not self.check_box_2d(x, z):
            return False
        if y < box.miny or y >= box.maxy:
            return False
        return True

    def block(self, x, y, z):
        if not self.check_box_3d(x, y, z):
            return None
        d = {}
        d['B'] = self.level.blockAt(x, y, z)
        d['D'] = self.level.blockDataAt(x, y, z)
        return d

    def set_block(self, x, y, z, d):
        if not self.check_box_3d(x, y, z):
            return None
        if 'B' in d:
            self.level.setBlockAt(x, y, z, d['B'])
        if 'D' in d:
            self.level.setBlockDataAt(x, y, z, d['D'])

    def surface_block(self, x, z):
        if not self.check_box_2d(x, z):
            return None
        y = self.level.heightMapAt(x, z)
        y = max(0, y - 1)

        d = self.block(x, y, z)
        if d:
            d['y'] = y

        return d

SaveFile = MCLevelAdapter

        #dict['L'] = self.level.blockLightAt(x,y,z)
        #dict['S'] = self.level.skyLightAt(x,y,z)
