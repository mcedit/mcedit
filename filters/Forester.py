# Version 5
'''This takes a base MineCraft level and adds or edits trees.
Place it in the folder where the save files are (usually .../.minecraft/saves)
Requires mcInterface.py in the same folder.'''

# Here are the variables you can edit.

# This is the name of the map to edit.
# Make a backup if you are experimenting!
LOADNAME = "LevelSave"

# How many trees do you want to add?
TREECOUNT = 12

# Where do you want the new trees?
# X, and Z are the map coordinates
X = 66
Z = -315
# How large an area do you want the trees to be in?
# for example, RADIUS = 10 will make place trees randomly in
# a circular area 20 blocks wide.
RADIUS = 80
# NOTE: tree density will be higher in the center than at the edges.

# Which shapes would you like the trees to be?
# these first three are best suited for small heights, from 5 - 10
# "normal" is the normal minecraft shape, it only gets taller and shorter
# "bamboo" a trunk with foliage, it only gets taller and shorter
# "palm" a trunk with a fan at the top, only gets taller and shorter
# "stickly" selects randomly from "normal", "bamboo" and "palm"
# these last five are best suited for very large trees, heights greater than 8
# "round" procedural spherical shaped tree, can scale up to immense size
# "cone" procedural, like a pine tree, also can scale up to immense size
# "procedural" selects randomly from "round" and "conical"
# "rainforest" many slender trees, most at the lower range of the height,
# with a few at the upper end.
# "mangrove" makes mangrove trees (see PLANTON below).
SHAPE = "procedural"

# What height should the trees be?
# Specifies the average height of the tree
# Examples:
# 5 is normal minecraft tree
# 3 is minecraft tree with foliage flush with the ground
# 10 is very tall trees, they will be hard to chop down
# NOTE: for round and conical, this affects the foliage size as well.

# CENTERHEIGHT is the height of the trees at the center of the area
# ie, when radius = 0
CENTERHEIGHT = 55

# EDGEHEIGHT is the height at the trees at the edge of the area.
# ie, when radius = RADIUS
EDGEHEIGHT = 25

# What should the variation in HEIGHT be?
# actual value +- variation
# default is 1
# Example:
# HEIGHT = 8 and HEIGHTVARIATION = 3 will result in
# trunk heights from 5 to 11
# value is clipped to a max of HEIGHT
# for a good rainforest, set this value not more than 1/2 of HEIGHT
HEIGHTVARIATION = 12

# Do you want branches, trunk, and roots?
# True makes all of that
# False does not create the trunk and branches, or the roots (even if they are
# enabled further down)
WOOD = True

# Trunk thickness multiplyer
# from zero (super thin trunk) to whatever huge number you can think of.
# Only works if SHAPE is not a "stickly" subtype
# Example:
# 1.0 is the default, it makes decently normal sized trunks
# 0.3 makes very thin trunks
# 4.0 makes a thick trunk (good for HOLLOWTRUNK).
# 10.5 will make a huge thick trunk.  Not even kidding. Makes spacious
# hollow trunks though!
TRUNKTHICKNESS = 1.0

# Trunk height, as a fraction of the tree
# Only works on "round" shaped trees
# Sets the height of the crown, where the trunk ends and splits
# Examples:
# 0.7 the default value, a bit more than half of the height
# 0.3 good for a fan-like tree
# 1.0 the trunk will extend to the top of the tree, and there will be no crown
# 2.0 the trunk will extend out the top of the foliage, making the tree appear
# like a cluster of green grapes impaled on a spike.
TRUNKHEIGHT = 0.7

# Do you want the trunk and tree broken off at the top?
# removes about half of the top of the trunk, and any foliage
# and branches that would attach above it.
# Only works if SHAPE is not a "stickly" subtype
# This results in trees that are shorter than the height settings
# True does that stuff
# False makes a normal tree (default)
BROKENTRUNK = False
# Note, this works well with HOLLOWTRUNK (below) turned on as well.

# Do you want the trunk to be hollow (or filled) inside?
# Only works with larger sized trunks.
# Only works if SHAPE is not a "stickly" subtype
# True makes the trunk hollow (or filled with other stuff)
# False makes a solid trunk (default)
HOLLOWTRUNK = False
# Note, this works well with BROKENTRUNK set to true (above)
# Further note, you may want to use a large value for TRUNKTHICKNESS

# How many branches should there be?
# General multiplyer for the number of branches
# However, it will not make more branches than foliage clusters
# so to garuntee a branch to every foliage cluster, set it very high, like 10000
# this also affects the number of roots, if they are enabled.
# Examples:
# 1.0 is normal
# 0.5 will make half as many branches
# 2.0 will make twice as mnay branches
# 10000 will make a branch to every foliage cluster (I'm pretty sure)
BRANCHDENSITY = 1.0

# do you want roots from the bottom of the tree?
# Only works if SHAPE is "round" or "cone" or "procedural"
# "yes" roots will penetrate anything, and may enter underground caves.
# "tostone" roots will be stopped by stone (default see STOPSROOTS below).
#    There may be some penetration.
# "hanging" will hang downward in air.  Good for "floating" type maps
#    (I really miss "floating" terrain as a default option)
# "no" roots will not be generated
ROOTS = "tostone"

# Do you want root buttresses?
# These make the trunk not-round at the base, seen in tropical or old trees.
# This option generally makes the trunk larger.
# Only works if SHAPE is "round" or "cone" or "procedural"
# Options:
# True makes root butresses
# False leaves them out
ROOTBUTTRESSES = True

# Do you want leaves on the trees?
# True there will be leaves
# False there will be no leaves
FOLIAGE = True

# How thick should the foliage be
# General multiplyer for the number of foliage clusters
# Examples:
# 1.0 is normal
# 0.3 will make very sparse spotty trees, half as many foliage clusters
# 2.0 will make dense foliage, better for the "rainforests" SHAPE
FOLIAGEDENSITY = 1.0

# Limit the tree height to the top of the map?
# True the trees will not grow any higher than the top of the map
# False the trees may be cut off by the top of the map
MAPHEIGHTLIMIT = True

# add lights in the middle of foliage clusters
# for those huge trees that get so dark underneath
# or for enchanted forests that should glow and stuff
# Only works if SHAPE is "round" or "cone" or "procedural"
# 0 makes just normal trees
# 1 adds one light inside the foliage clusters for a bit of light
# 2 adds two lights around the base of each cluster, for more light
# 4 adds lights all around the base of each cluster for lots of light
LIGHTTREE = 0

# Do you want to only place trees near existing trees?
# True will only plant new trees near existing trees.
# False will not check for existing trees before planting.
# NOTE: the taller the tree, the larger the forest needs to be to qualify
# OTHER NOTE: this feature has not been extensively tested.
# IF YOU HAVE PROBLEMS: SET TO False
ONLYINFORESTS = False

#####################
# Advanced options! #
#####################

# What kind of material should the "wood" be made of?
# defaults to 17
WOODMAT = 17

# What data value should the wood blocks have?
# Some blocks, like wood, leaves, and cloth change
# apperance with different data values
# defaults to 0
WOODDATA = 0

# What kind of material should the "leaves" be made of?
# defaults to 18
LEAFMAT = 18

# What data value should the leaf blocks have?
# Some blocks, like wood, leaves, and cloth change
# apperance with different data values
# defaults to 0
LEAFDATA = 0

# What kind of material should the "lights" be made of?
# defaults to 89 (glowstone)
LIGHTMAT = 89

# What data value should the light blocks have?
# defaults to 0
LIGHTDATA = 0

# What kind of material would you like the "hollow" trunk filled with?
# defaults to 0 (air)
TRUNKFILLMAT = 0

# What data value would you like the "hollow" trunk filled with?
# defaults to 0
TRUNKFILLDATA = 0

# What kind of blocks should the trees be planted on?
# Use the Minecraft index.
# Examples
# 2 is grass (the default)
# 3 is dirt
# 1 is stone (an odd choice)
# 12 is sand (for beach or desert)
# 9 is water (if you want an aquatic forest)
# this is a list, and comma seperated.
# example: [2, 3]
# will plant trees on grass or dirt
PLANTON = [2]

# What kind of blocks should stop the roots?
# a list of block id numbers like PLANTON
# Only works if ROOTS = "tostone"
# default, [1] (stone)
# if you want it to be stopped by other block types, add it to the list
STOPSROOTS = [1]

# What kind of blocks should stop branches?
# same as STOPSROOTS above, but is always turned on
# defaults to stone, cobblestone, and glass
# set it to [] if you want branches to go through everything
STOPSBRANCHES = [1, 4, 20]

# How do you want to interpolate from center to edge?
# "linear" makes a cone-shaped forest
# This is the only option at present
INTERPOLATION = "linear"

# Do a rough recalculation of the lighting?
# Slows it down to do a very rough and incomplete re-light.
# If you want to really fix the lighting, use a seperate re-lighting tool.
# True  do the rough fix
# False don't bother
LIGHTINGFIX = True

# How many times do you want to try to find a location?
# it will stop planing after MAXTRIES has been exceeded.
# Set to smaller numbers to abort quicker, or larger numbers
# if you want to keep trying for a while.
# NOTE: the number of trees will not exceed this number
# Default: 1000
MAXTRIES = 1000

# Do you want lots of text telling you waht is going on?
# True lots of text (default). Good for debugging.
# False no text
VERBOSE = True

##############################################################
#  Don't edit below here unless you know what you are doing  #
##############################################################

# input filtering
TREECOUNT = int(TREECOUNT)
if TREECOUNT < 0:
    TREECOUNT = 0
if SHAPE not in ["normal", "bamboo", "palm", "stickly",
                 "round", "cone", "procedural",
                 "rainforest", "mangrove"]:
    if VERBOSE:
        print("SHAPE not set correctly, using 'procedural'.")
    SHAPE = "procedural"
if CENTERHEIGHT < 1:
    CENTERHEIGHT = 1
if EDGEHEIGHT < 1:
    EDGEHEIGHT = 1
minheight = min(CENTERHEIGHT, EDGEHEIGHT)
if HEIGHTVARIATION > minheight:
    HEIGHTVARIATION = minheight
if INTERPOLATION not in ["linear"]:
    if VERBOSE:
        print("INTERPOLATION not set correctly, using 'linear'.")
    INTERPOLATION = "linear"
if WOOD not in [True, False]:
    if VERBOSE:
        print("WOOD not set correctly, using True")
    WOOD = True
if TRUNKTHICKNESS < 0.0:
    TRUNKTHICKNESS = 0.0
if TRUNKHEIGHT < 0.0:
    TRUNKHEIGHT = 0.0
if ROOTS not in ["yes", "tostone", "hanging", "no"]:
    if VERBOSE:
        print("ROOTS not set correctly, using 'no' and creating no roots")
    ROOTS = "no"
if ROOTBUTTRESSES not in [True, False]:
    if VERBOSE:
        print("ROOTBUTTRESSES not set correctly, using False")
    ROOTBUTTRESSES = False
if FOLIAGE not in [True, False]:
    if VERBOSE:
        print("FOLIAGE not set correctly, using True")
    ROOTBUTTRESSES = True
if FOLIAGEDENSITY < 0.0:
    FOLIAGEDENSITY = 0.0
if BRANCHDENSITY < 0.0:
    BRANCHDENSITY = 0.0
if MAPHEIGHTLIMIT not in [True, False]:
    if VERBOSE:
        print("MAPHEIGHTLIMIT not set correctly, using False")
    MAPHEIGHTLIMIT = False
if LIGHTTREE not in [0, 1, 2, 4]:
    if VERBOSE:
        print("LIGHTTREE not set correctly, using 0 for no torches")
    LIGHTTREE = 0
# assemble the material dictionaries
WOODINFO = {'B': WOODMAT, 'D': WOODDATA}
LEAFINFO = {'B': LEAFMAT, 'D': LEAFDATA}
LIGHTINFO = {'B': LIGHTMAT, 'D': LIGHTDATA}
TRUNKFILLINFO = {'B': TRUNKFILLMAT, 'D': TRUNKFILLDATA}

# The following is an interface class for .mclevel data for minecraft savefiles.
# The following also includes a useful coordinate to index convertor and several
# other useful functions.

import mcInterface

#some handy functions


def dist_to_mat(cord, vec, matidxlist, mcmap, invert=False, limit=False):
    '''travel from cord along vec and return how far it was to a point of matidx

    the distance is returned in number of iterations.  If the edge of the map
    is reached, then return the number of iterations as well.
    if invert == True, search for anything other than those in matidxlist
    '''
    assert isinstance(mcmap, mcInterface.SaveFile)
    block = mcmap.block
    curcord = [i + .5 for i in cord]
    iterations = 0
    on_map = True
    while on_map:
        x = int(curcord[0])
        y = int(curcord[1])
        z = int(curcord[2])
        return_dict = block(x, y, z)
        if return_dict is None:
            break
        else:
            block_value = return_dict['B']
        if (block_value in matidxlist) and (invert == False):
            break
        elif (block_value not in matidxlist) and invert:
            break
        else:
            curcord = [curcord[i] + vec[i] for i in range(3)]
            iterations += 1
        if limit and iterations > limit:
            break
    return iterations

# This is the end of the MCLevel interface.

# Now, on to the actual code.

from random import random, choice, sample
from math import sqrt, sin, cos, pi


def calc_column_lighting(x, z, mclevel):
    '''Recalculate the sky lighting of the column.'''

    # Begin at the top with sky light level 15.
    cur_light = 15
    # traverse the column until cur_light == 0
    # and the existing light values are also zero.
    y = 127
    get_block = mclevel.block
    set_block = mclevel.set_block
    get_height = mclevel.retrieve_heightmap
    set_height = mclevel.set_heightmap
    #get the current heightmap
    cur_height = get_height(x, z)
    # set a flag that the highest point has been updated
    height_updated = False
    # if this doesn't exist, the block doesn't exist either, abort.
    if cur_height is None:
        return None
    light_reduction_lookup = {0: 0, 20: 0, 18: 1, 8: 2, 79: 2}
    while True:
        #get the block sky light and type
        block_info = get_block(x, y, z, 'BS')
        block_light = block_info['S']
        block_type = block_info['B']
        # update the height map if it hasn't been updated yet,
        # and the current block reduces light
        if (not height_updated) and (block_type not in (0, 20)):
            new_height = y + 1
            if new_height == 128:
                new_height = 127
            set_height(x, new_height, z)
            height_updated = True
        #compare block with cur_light, escape if both 0
        if block_light == 0 and cur_light == 0:
            break
        #set the block light if necessary
        if block_light != cur_light:
            set_block(x, y, z, {'S': cur_light})
        #set the new cur_light
        if block_type in light_reduction_lookup:
            # partial light reduction
            light_reduction = light_reduction_lookup[block_type]
        else:
            # full light reduction
            light_reduction = 16
        cur_light += -light_reduction
        if cur_light < 0:
            cur_light = 0
        #increment and check y
        y += -1
        if y < 0:
            break


class ReLight(object):
    '''keep track of which squares need to be relit, and then relight them'''
    def add(self, x, z):
        coords = (x, z)
        self.all_columns.add(coords)

    def calc_lighting(self):
        mclevel = self.save_file
        for column_coords in self.all_columns:
            # recalculate the lighting
            x = column_coords[0]
            z = column_coords[1]
            calc_column_lighting(x, z, mclevel)

    def __init__(self):
        self.all_columns = set()
        self.save_file = None

relight_master = ReLight()


def assign_value(x, y, z, values, save_file):
    '''Assign an index value to a location in mcmap.

    If the index is outside the bounds of the map, return None.  If the
    assignment succeeds, return True.
    '''
    if y > 127:
        return None
    result = save_file.set_block(x, y, z, values)
    if LIGHTINGFIX:
        relight_master.add(x, z)
    return result


class Tree(object):
    '''Set up the interface for tree objects.  Designed for subclassing.
    '''
    def prepare(self, mcmap):
        '''initialize the internal values for the Tree object.
        '''
        return None

    def maketrunk(self, mcmap):
        '''Generate the trunk and enter it in mcmap.
        '''
        return None

    def makefoliage(self, mcmap):
        """Generate the foliage and enter it in mcmap.

        Note, foliage will disintegrate if there is no log nearby"""
        return None

    def copy(self, other):
        '''Copy the essential values of the other tree object into self.
        '''
        self.pos = other.pos
        self.height = other.height

    def __init__(self, pos=[0, 0, 0], height=1):
        '''Accept values for the position and height of a tree.

        Store them in self.
        '''
        self.pos = pos
        self.height = height


class StickTree(Tree):
    '''Set up the trunk for trees with a trunk width of 1 and simple geometry.

    Designed for sublcassing.  Only makes the trunk.
    '''
    def maketrunk(self, mcmap):
        x = self.pos[0]
        y = self.pos[1]
        z = self.pos[2]
        for i in range(self.height):
            assign_value(x, y, z, WOODINFO, mcmap)
            y += 1


class NormalTree(StickTree):
    '''Set up the foliage for a 'normal' tree.

    This tree will be a single bulb of foliage above a single width trunk.
    This shape is very similar to the default Minecraft tree.
    '''
    def makefoliage(self, mcmap):
        """note, foliage will disintegrate if there is no foliage below, or
        if there is no "log" block within range 2 (square) at the same level or
        one level below"""
        topy = self.pos[1] + self.height - 1
        start = topy - 2
        end = topy + 2
        for y in range(start, end):
            if y > start + 1:
                rad = 1
            else:
                rad = 2
            for xoff in range(-rad, rad + 1):
                for zoff in range(-rad, rad + 1):
                    if (random() > 0.618
                        and abs(xoff) == abs(zoff)
                        and abs(xoff) == rad
                        ):
                        continue

                    x = self.pos[0] + xoff
                    z = self.pos[2] + zoff

                    assign_value(x, y, z, LEAFINFO, mcmap)


class BambooTree(StickTree):
    '''Set up the foliage for a bamboo tree.

    Make foliage sparse and adjacent to the trunk.
    '''
    def makefoliage(self, mcmap):
        start = self.pos[1]
        end = self.pos[1] + self.height + 1
        for y in range(start, end):
            for i in [0, 1]:
                xoff = choice([-1, 1])
                zoff = choice([-1, 1])
                x = self.pos[0] + xoff
                z = self.pos[2] + zoff
                assign_value(x, y, z, LEAFINFO, mcmap)


class PalmTree(StickTree):
    '''Set up the foliage for a palm tree.

    Make foliage stick out in four directions from the top of the trunk.
    '''
    def makefoliage(self, mcmap):
        y = self.pos[1] + self.height
        for xoff in range(-2, 3):
            for zoff in range(-2, 3):
                if abs(xoff) == abs(zoff):
                    x = self.pos[0] + xoff
                    z = self.pos[2] + zoff
                    assign_value(x, y, z, LEAFINFO, mcmap)


class ProceduralTree(Tree):
    '''Set up the methods for a larger more complicated tree.

    This tree type has roots, a trunk, and branches all of varying width,
    and many foliage clusters.
    MUST BE SUBCLASSED.  Specifically, self.foliage_shape must be set.
    Subclass 'prepare' and 'shapefunc' to make different shaped trees.
    '''

    def crossection(self, center, radius, diraxis, matidx, mcmap):
        '''Create a round section of type matidx in mcmap.

        Passed values:
        center = [x, y, z] for the coordinates of the center block
        radius = <number> as the radius of the section.  May be a float or int.
        diraxis: The list index for the axis to make the section
        perpendicular to.  0 indicates the x axis, 1 the y, 2 the z.  The
        section will extend along the other two axies.
        matidx = <int> the integer value to make the section out of.
        mcmap = the array generated by make_mcmap
        matdata = <int> the integer value to make the block data value.
        '''
        rad = int(radius + .618)
        if rad <= 0:
            return None
        secidx1 = (diraxis - 1) % 3
        secidx2 = (1 + diraxis) % 3
        coord = [0, 0, 0]
        for off1 in range(-rad, rad + 1):
            for off2 in range(-rad, rad + 1):
                thisdist = sqrt((abs(off1) + .5) ** 2 + (abs(off2) + .5) ** 2)
                if thisdist > radius:
                    continue
                pri = center[diraxis]
                sec1 = center[secidx1] + off1
                sec2 = center[secidx2] + off2
                coord[diraxis] = pri
                coord[secidx1] = sec1
                coord[secidx2] = sec2
                assign_value(coord[0], coord[1], coord[2], matidx, mcmap)

    def shapefunc(self, y):
        '''Take y and return a radius for the location of the foliage cluster.

        If no foliage cluster is to be created, return None
        Designed for sublcassing.  Only makes clusters close to the trunk.
        '''
        if random() < 100. / (self.height ** 2) and y < self.trunkheight:
            return self.height * .12
        return None

    def foliagecluster(self, center, mcmap):
        '''generate a round cluster of foliage at the location center.

        The shape of the cluster is defined by the list self.foliage_shape.
        This list must be set in a subclass of ProceduralTree.
        '''
        level_radius = self.foliage_shape
        x = center[0]
        y = center[1]
        z = center[2]
        for i in level_radius:
            self.crossection([x, y, z], i, 1, LEAFINFO, mcmap)
            y += 1

    def taperedcylinder(self, start, end, startsize, endsize, mcmap, blockdata):
        '''Create a tapered cylinder in mcmap.

        start and end are the beginning and ending coordinates of form [x, y, z].
        startsize and endsize are the beginning and ending radius.
        The material of the cylinder is WOODMAT.
        '''

        # delta is the coordinate vector for the difference between
        # start and end.
        delta = [int(end[i] - start[i]) for i in range(3)]
        # primidx is the index (0, 1, or 2 for x, y, z) for the coordinate
        # which has the largest overall delta.
        maxdist = max(delta, key=abs)
        if maxdist == 0:
            return None
        primidx = delta.index(maxdist)
        # secidx1 and secidx2 are the remaining indicies out of [0, 1, 2].
        secidx1 = (primidx - 1) % 3
        secidx2 = (1 + primidx) % 3
        # primsign is the digit 1 or -1 depending on whether the limb is headed
        # along the positive or negative primidx axis.
        primsign = int(delta[primidx] / abs(delta[primidx]))
        # secdelta1 and ...2 are the amount the associated values change
        # for every step along the prime axis.
        secdelta1 = delta[secidx1]
        secfac1 = float(secdelta1) / delta[primidx]
        secdelta2 = delta[secidx2]
        secfac2 = float(secdelta2) / delta[primidx]
        # Initialize coord.  These values could be anything, since
        # they are overwritten.
        coord = [0, 0, 0]
        # Loop through each crossection along the primary axis,
        # from start to end.
        endoffset = delta[primidx] + primsign
        for primoffset in range(0, endoffset, primsign):
            primloc = start[primidx] + primoffset
            secloc1 = int(start[secidx1] + primoffset * secfac1)
            secloc2 = int(start[secidx2] + primoffset * secfac2)
            coord[primidx] = primloc
            coord[secidx1] = secloc1
            coord[secidx2] = secloc2
            primdist = abs(delta[primidx])
            radius = endsize + (startsize - endsize) * abs(delta[primidx]
                                - primoffset) / primdist
            self.crossection(coord, radius, primidx, blockdata, mcmap)

    def makefoliage(self, mcmap):
        '''Generate the foliage for the tree in mcmap.
        '''
        """note, foliage will disintegrate if there is no foliage below, or
        if there is no "log" block within range 2 (square) at the same level or
        one level below"""
        foliage_coords = self.foliage_cords
        for coord in foliage_coords:
            self.foliagecluster(coord, mcmap)
        for cord in foliage_coords:
            assign_value(cord[0], cord[1], cord[2], WOODINFO, mcmap)
            if LIGHTTREE == 1:
                assign_value(cord[0], cord[1] + 1, cord[2], LIGHTINFO, mcmap)
            elif LIGHTTREE in [2, 4]:
                assign_value(cord[0] + 1, cord[1], cord[2], LIGHTINFO, mcmap)
                assign_value(cord[0] - 1, cord[1], cord[2], LIGHTINFO, mcmap)
                if LIGHTTREE == 4:
                    assign_value(cord[0], cord[1], cord[2] + 1, LIGHTINFO, mcmap)
                    assign_value(cord[0], cord[1], cord[2] - 1, LIGHTINFO, mcmap)

    def makebranches(self, mcmap):
        '''Generate the branches and enter them in mcmap.
        '''
        treeposition = self.pos
        height = self.height
        topy = treeposition[1] + int(self.trunkheight + 0.5)
        # endrad is the base radius of the branches at the trunk
        endrad = self.trunkradius * (1 - self.trunkheight / height)
        if endrad < 1.0:
            endrad = 1.0
        for coord in self.foliage_cords:
            dist = (sqrt(float(coord[0] - treeposition[0]) ** 2 +
                            float(coord[2] - treeposition[2]) ** 2))
            ydist = coord[1] - treeposition[1]
            # value is a magic number that weights the probability
            # of generating branches properly so that
            # you get enough on small trees, but not too many
            # on larger trees.
            # Very difficult to get right... do not touch!
            value = (self.branchdensity * 220 * height) / ((ydist + dist) ** 3)
            if value < random():
                continue

            posy = coord[1]
            slope = self.branchslope + (0.5 - random()) * .16
            if coord[1] - dist * slope > topy:
                # Another random rejection, for branches between
                # the top of the trunk and the crown of the tree
                threshhold = 1 / float(height)
                if random() < threshhold:
                    continue
                branchy = topy
                basesize = endrad
            else:
                branchy = posy - dist * slope
                basesize = (endrad + (self.trunkradius - endrad) *
                         (topy - branchy) / self.trunkheight)
            startsize = (basesize * (1 + random()) * .618 *
                         (dist / height) ** 0.618)
            rndr = sqrt(random()) * basesize * 0.618
            rndang = random() * 2 * pi
            rndx = int(rndr * sin(rndang) + 0.5)
            rndz = int(rndr * cos(rndang) + 0.5)
            startcoord = [treeposition[0] + rndx,
                          int(branchy),
                          treeposition[2] + rndz]
            if startsize < 1.0:
                startsize = 1.0
            endsize = 1.0
            self.taperedcylinder(startcoord, coord, startsize, endsize,
                             mcmap, WOODINFO)

    def makeroots(self, rootbases, mcmap):
        '''generate the roots and enter them in mcmap.

        rootbases = [[x, z, base_radius], ...] and is the list of locations
        the roots can originate from, and the size of that location.
        '''
        treeposition = self.pos
        height = self.height
        for coord in self.foliage_cords:
            # First, set the threshhold for randomly selecting this
            # coordinate for root creation.
            dist = (sqrt(float(coord[0] - treeposition[0]) ** 2 +
                            float(coord[2] - treeposition[2]) ** 2))
            ydist = coord[1] - treeposition[1]
            value = (self.branchdensity * 220 * height) / ((ydist + dist) ** 3)
            # Randomly skip roots, based on the above threshold
            if value < random():
                continue
            # initialize the internal variables from a selection of
            # starting locations.
            rootbase = choice(rootbases)
            rootx = rootbase[0]
            rootz = rootbase[1]
            rootbaseradius = rootbase[2]
            # Offset the root origin location by a random amount
            # (radialy) from the starting location.
            rndr = (sqrt(random()) * rootbaseradius * .618)
            rndang = random() * 2 * pi
            rndx = int(rndr * sin(rndang) + 0.5)
            rndz = int(rndr * cos(rndang) + 0.5)
            rndy = int(random() * rootbaseradius * 0.5)
            startcoord = [rootx + rndx, treeposition[1] + rndy, rootz + rndz]
            # offset is the distance from the root base to the root tip.
            offset = [startcoord[i] - coord[i] for i in range(3)]
            # If this is a mangrove tree, make the roots longer.
            if SHAPE == "mangrove":
                offset = [int(val * 1.618 - 1.5) for val in offset]
            endcoord = [startcoord[i] + offset[i] for i in range(3)]
            rootstartsize = (rootbaseradius * 0.618 * abs(offset[1]) /
                             (height * 0.618))
            if rootstartsize < 1.0:
                rootstartsize = 1.0
            endsize = 1.0
            # If ROOTS is set to "tostone" or "hanging" we need to check
            # along the distance for collision with existing materials.
            if ROOTS in ["tostone", "hanging"]:
                offlength = sqrt(float(offset[0]) ** 2 +
                                 float(offset[1]) ** 2 +
                                 float(offset[2]) ** 2)
                if offlength < 1:
                    continue
                rootmid = endsize
                # vec is a unit vector along the direction of the root.
                vec = [offset[i] / offlength for i in range(3)]
                if ROOTS == "tostone":
                    searchindex = STOPSROOTS
                elif ROOTS == "hanging":
                    searchindex = [0]
                # startdist is how many steps to travel before starting to
                # search for the material.  It is used to ensure that large
                # roots will go some distance before changing directions
                # or stopping.
                startdist = int(random() * 6 * sqrt(rootstartsize) + 2.8)
                # searchstart is the coordinate where the search should begin
                searchstart = [startcoord[i] + startdist * vec[i]
                               for i in range(3)]
                # dist stores how far the search went (including searchstart)
                # before encountering the expected marterial.
                dist = startdist + dist_to_mat(searchstart, vec,
                                        searchindex, mcmap, limit=offlength)
                # If the distance to the material is less than the length
                # of the root, change the end point of the root to where
                # the search found the material.
                if dist < offlength:
                    # rootmid is the size of the crossection at endcoord.
                    rootmid += (rootstartsize -
                                         endsize) * (1 - dist / offlength)
                    # endcoord is the midpoint for hanging roots,
                    # and the endpoint for roots stopped by stone.
                    endcoord = [startcoord[i] + int(vec[i] * dist)
                                for i in range(3)]
                    if ROOTS == "hanging":
                        # remaining_dist is how far the root had left
                        # to go when it was stopped.
                        remaining_dist = offlength - dist
                        # Initialize bottomcord to the stopping point of
                        # the root, and then hang straight down
                        # a distance of remaining_dist.
                        bottomcord = endcoord[:]
                        bottomcord[1] += -int(remaining_dist)
                        # Make the hanging part of the hanging root.
                        self.taperedcylinder(endcoord, bottomcord,
                             rootmid, endsize, mcmap, WOODINFO)

                # make the beginning part of hanging or "tostone" roots
                self.taperedcylinder(startcoord, endcoord,
                     rootstartsize, rootmid, mcmap, WOODINFO)

            # If you aren't searching for stone or air, just make the root.
            else:
                self.taperedcylinder(startcoord, endcoord,
                             rootstartsize, endsize, mcmap, WOODINFO)

    def maketrunk(self, mcmap):
        '''Generate the trunk, roots, and branches in mcmap.
        '''
        height = self.height
        trunkheight = self.trunkheight
        trunkradius = self.trunkradius
        treeposition = self.pos
        starty = treeposition[1]
        midy = treeposition[1] + int(trunkheight * .382)
        topy = treeposition[1] + int(trunkheight + 0.5)
        # In this method, x and z are the position of the trunk.
        x = treeposition[0]
        z = treeposition[2]
        end_size_factor = trunkheight / height
        midrad = trunkradius * (1 - end_size_factor * .5)
        endrad = trunkradius * (1 - end_size_factor)
        if endrad < 1.0:
            endrad = 1.0
        if midrad < endrad:
            midrad = endrad
        # Make the root buttresses, if indicated
        if ROOTBUTTRESSES or SHAPE == "mangrove":
            # The start radius of the trunk should be a little smaller if we
            # are using root buttresses.
            startrad = trunkradius * .8
            # rootbases is used later in self.makeroots(...) as
            # starting locations for the roots.
            rootbases = [[x, z, startrad]]
            buttress_radius = trunkradius * 0.382
            # posradius is how far the root buttresses should be offset
            # from the trunk.
            posradius = trunkradius
            # In mangroves, the root buttresses are much more extended.
            if SHAPE == "mangrove":
                posradius = posradius * 2.618
            num_of_buttresses = int(sqrt(trunkradius) + 3.5)
            for i in range(num_of_buttresses):
                rndang = random() * 2 * pi
                thisposradius = posradius * (0.9 + random() * .2)
                # thisx and thisz are the x and z position for the base of
                # the root buttress.
                thisx = x + int(thisposradius * sin(rndang))
                thisz = z + int(thisposradius * cos(rndang))
                # thisbuttressradius is the radius of the buttress.
                # Currently, root buttresses do not taper.
                thisbuttressradius = buttress_radius * (0.618 + random())
                if thisbuttressradius < 1.0:
                    thisbuttressradius = 1.0
                # Make the root buttress.
                self.taperedcylinder([thisx, starty, thisz], [x, midy, z],
                                 thisbuttressradius, thisbuttressradius,
                                 mcmap, WOODINFO)
                # Add this root buttress as a possible location at
                # which roots can spawn.
                rootbases += [[thisx, thisz, thisbuttressradius]]
        else:
            # If root buttresses are turned off, set the trunk radius
            # to normal size.
            startrad = trunkradius
            rootbases = [[x, z, startrad]]
        # Make the lower and upper sections of the trunk.
        self.taperedcylinder([x, starty, z], [x, midy, z], startrad, midrad,
                         mcmap, WOODINFO)
        self.taperedcylinder([x, midy, z], [x, topy, z], midrad, endrad,
                         mcmap, WOODINFO)
        #Make the branches
        self.makebranches(mcmap)
        #Make the roots, if indicated.
        if ROOTS in ["yes", "tostone", "hanging"]:
            self.makeroots(rootbases, mcmap)
        # Hollow the trunk, if specified
        # check to make sure that the trunk is large enough to be hollow
        if trunkradius > 2 and HOLLOWTRUNK:
            # wall thickness is actually the double the wall thickness
            # it is a diameter difference, not a radius difference.
            wall_thickness = (1 + trunkradius * 0.1 * random())
            if wall_thickness < 1.3:
                wall_thickness = 1.3
            base_radius = trunkradius - wall_thickness
            if base_radius < 1:
                base_radius = 1.0
            mid_radius = midrad - wall_thickness
            top_radius = endrad - wall_thickness
            # the starting x and y can be offset by up to the wall thickness.
            base_offset = int(wall_thickness)
            x_choices = [i for i in range(x - base_offset,
                                          x + base_offset + 1)]
            start_x = choice(x_choices)
            z_choices = [i for i in range(z - base_offset,
                                          z + base_offset + 1)]
            start_z = choice(z_choices)
            self.taperedcylinder([start_x, starty, start_z], [x, midy, z],
                                 base_radius, mid_radius,
                         mcmap, TRUNKFILLINFO)
            hollow_top_y = int(topy + trunkradius + 1.5)
            self.taperedcylinder([x, midy, z], [x, hollow_top_y, z],
                                 mid_radius, top_radius,
                                 mcmap, TRUNKFILLINFO)

    def prepare(self, mcmap):
        '''Initialize the internal values for the Tree object.

        Primarily, sets up the foliage cluster locations.
        '''
        treeposition = self.pos
        self.trunkradius = .618 * sqrt(self.height * TRUNKTHICKNESS)
        if self.trunkradius < 1:
            self.trunkradius = 1
        if BROKENTRUNK:
            self.trunkheight = self.height * (.3 + random() * .4)
            yend = int(treeposition[1] + self.trunkheight + .5)
        else:
            self.trunkheight = self.height
            yend = int(treeposition[1] + self.height)
        self.branchdensity = BRANCHDENSITY / FOLIAGEDENSITY
        topy = treeposition[1] + int(self.trunkheight + 0.5)
        foliage_coords = []
        ystart = treeposition[1]
        num_of_clusters_per_y = int(1.5 + (FOLIAGEDENSITY *
                                           self.height / 19.) ** 2)
        if num_of_clusters_per_y < 1:
            num_of_clusters_per_y = 1
        # make sure we don't spend too much time off the top of the map
        if yend > 127:
            yend = 127
        if ystart > 127:
            ystart = 127
        for y in range(yend, ystart, -1):
            for i in range(num_of_clusters_per_y):
                shapefac = self.shapefunc(y - ystart)
                if shapefac is None:
                    continue
                r = (sqrt(random()) + .328) * shapefac

                theta = random() * 2 * pi
                x = int(r * sin(theta)) + treeposition[0]
                z = int(r * cos(theta)) + treeposition[2]
                # if there are values to search in STOPSBRANCHES
                # then check to see if this cluster is blocked
                # by stuff, like dirt or rock, or whatever
                if len(STOPSBRANCHES):
                    dist = (sqrt(float(x - treeposition[0]) ** 2 +
                                float(z - treeposition[2]) ** 2))
                    slope = self.branchslope
                    if y - dist * slope > topy:
                        # the top of the tree
                        starty = topy
                    else:
                        starty = y - dist * slope
                    # the start position of the search
                    start = [treeposition[0], starty, treeposition[2]]
                    offset = [x - treeposition[0],
                              y - starty,
                              z - treeposition[2]]
                    offlength = sqrt(offset[0] ** 2 + offset[1] ** 2 + offset[2] ** 2)
                    # if the branch is as short as... nothing, don't bother.
                    if offlength < 1:
                        continue
                    # unit vector for the search
                    vec = [offset[i] / offlength for i in range(3)]
                    mat_dist = dist_to_mat(start, vec, STOPSBRANCHES,
                                           mcmap, limit=offlength + 3)
                    # after all that, if you find something, don't add
                    # this coordinate to the list
                    if mat_dist < offlength + 2:
                        continue
                foliage_coords += [[x, y, z]]

        self.foliage_cords = foliage_coords


class RoundTree(ProceduralTree):
    '''This kind of tree is designed to resemble a deciduous tree.
    '''
    def prepare(self, mcmap):
        self.branchslope = 0.382
        ProceduralTree.prepare(self, mcmap)
        self.foliage_shape = [2, 3, 3, 2.5, 1.6]
        self.trunkradius = self.trunkradius * 0.8
        self.trunkheight = TRUNKHEIGHT * self.trunkheight

    def shapefunc(self, y):
        twigs = ProceduralTree.shapefunc(self, y)
        if twigs is not None:
            return twigs
        if y < self.height * (.282 + .1 * sqrt(random())):
            return None
        radius = self.height / 2.
        adj = self.height / 2. - y
        if adj == 0:
            dist = radius
        elif abs(adj) >= radius:
            dist = 0
        else:
            dist = sqrt((radius ** 2) - (adj ** 2))
        dist = dist * .618
        return dist


class ConeTree(ProceduralTree):
    '''this kind of tree is designed to resemble a conifer tree.
    '''
    # woodType is the kind of wood the tree has, a data value
    woodType = 1

    def prepare(self, mcmap):
        self.branchslope = 0.15
        ProceduralTree.prepare(self, mcmap)
        self.foliage_shape = [3, 2.6, 2, 1]
        self.trunkradius = self.trunkradius * 0.5

    def shapefunc(self, y):
        twigs = ProceduralTree.shapefunc(self, y)
        if twigs is not None:
            return twigs
        if y < self.height * (.25 + .05 * sqrt(random())):
            return None
        radius = (self.height - y) * 0.382
        if radius < 0:
            radius = 0
        return radius


class RainforestTree(ProceduralTree):
    '''This kind of tree is designed to resemble a rainforest tree.
    '''
    def prepare(self, mcmap):
        self.foliage_shape = [3.4, 2.6]
        self.branchslope = 1.0
        ProceduralTree.prepare(self, mcmap)
        self.trunkradius = self.trunkradius * 0.382
        self.trunkheight = self.trunkheight * .9

    def shapefunc(self, y):
        if y < self.height * 0.8:
            if EDGEHEIGHT < self.height:
                twigs = ProceduralTree.shapefunc(self, y)
                if (twigs is not None) and random() < 0.07:
                    return twigs
            return None
        else:
            width = self.height * .382
            topdist = (self.height - y) / (self.height * 0.2)
            dist = width * (0.618 + topdist) * (0.618 + random()) * 0.382
            return dist


class MangroveTree(RoundTree):
    '''This kind of tree is designed to resemble a mangrove tree.
    '''
    def prepare(self, mcmap):
        self.branchslope = 1.0
        RoundTree.prepare(self, mcmap)
        self.trunkradius = self.trunkradius * 0.618

    def shapefunc(self, y):
        val = RoundTree.shapefunc(self, y)
        if val is None:
            return val
        val = val * 1.618
        return val


def planttrees(mcmap, treelist):
    '''Take mcmap and add trees to random locations on the surface to treelist.
    '''
    assert isinstance(mcmap, mcInterface.SaveFile)
    # keep looping until all the trees are placed
    # calc the radius difference, for interpolation
    in_out_dif = EDGEHEIGHT - CENTERHEIGHT
    if VERBOSE:
        print('Tree Locations: x, y, z, tree height')
    tries = 0
    max_tries = MAXTRIES
    while len(treelist) < TREECOUNT:
        if tries > max_tries:
            if VERBOSE:
                print("Stopping search for tree locations after {0} tries".format(tries))
                print("If you don't have enough trees, check X, Y, RADIUS, and PLANTON")
            break
        tries += 1
        # choose a location
        rad_fraction = random()
        # this is some kind of square interpolation
        rad_fraction = 1.0 - rad_fraction
        rad_fraction **= 2
        rad_fraction = 1.0 - rad_fraction

        rad = rad_fraction * RADIUS
        ang = random() * pi * 2
        x = X + int(rad * sin(ang) + .5)
        z = Z + int(rad * cos(ang) + .5)
        # check to see if this location is suitable
        y_top = mcmap.surface_block(x, z)
        if y_top is None:
            # this location is off the map!
            continue
        if y_top['B'] in PLANTON:
            # plant the tree on the block above the ground
            # hence the " + 1"
            y = y_top['y'] + 1
        else:
            continue
        # this is linear interpolation also.
        base_height = CENTERHEIGHT + (in_out_dif * rad_fraction)
        height_rand = (random() - .5) * 2 * HEIGHTVARIATION
        height = int(base_height + height_rand)
        # if the option is set, check the surrounding area for trees
        if ONLYINFORESTS:
            '''we are looking for foliage
            it should show up in the "surface_block" search
            check every fifth block in a square pattern,
            offset around the trunk
            and equal to the trees height
            if the area is not at least one third foliage,
            don't build the tree'''
            # spacing is how far apart each sample should be
            spacing = 5
            # search_size is how many blocks to check
            # along each axis
            search_size = 2 + (height // spacing)
            # check at least 3 x 3
            search_size = max([search_size, 3])
            # set up the offset values to offset the starting corner
            offset = ((search_size - 1) * spacing) // 2
            # foliage_count is the total number of foliage blocks found
            foliage_count = 0
            # check each sample location for foliage
            for step_x in range(search_size):
                # search_x is the x location to search this sample
                search_x = x - offset + (step_x * spacing)
                for step_z in range(search_size):
                    # same as for search_x
                    search_z = z - offset + (step_z * spacing)
                    search_block = mcmap.surface_block(search_x, search_z)
                    if search_block is None:
                        continue
                    if search_block['B'] == 18:
                        # this sample contains foliage!
                        # add it to the total
                        foliage_count += 1
            #now that we have the total count, find the ratio
            total_searched = search_size ** 2
            foliage_ratio = foliage_count / total_searched
            # the acceptable amount is about a third
            acceptable_ratio = .3
            if foliage_ratio < acceptable_ratio:
                # after all that work, there wasn't enough foliage around!
                # try again!
                continue

        # generate the new tree
        newtree = Tree([x, y, z], height)
        if VERBOSE:
            print(x, y, z, height)
        treelist += [newtree]


def processtrees(mcmap, treelist):
    '''Initalize all of the trees in treelist.

    Set all of the trees to the right type, and run prepare.  If indicated
    limit the height of the trees to the top of the map.
    '''
    assert isinstance(mcmap, mcInterface.SaveFile)
    if SHAPE == "stickly":
        shape_choices = ["normal", "bamboo", "palm"]
    elif SHAPE == "procedural":
        shape_choices = ["round", "cone"]
    else:
        shape_choices = [SHAPE]

    # initialize mapheight, just in case
    mapheight = 127
    for i in range(len(treelist)):
        newshape = choice(shape_choices)
        if newshape == "normal":
            newtree = NormalTree()
        elif newshape == "bamboo":
            newtree = BambooTree()
        elif newshape == "palm":
            newtree = PalmTree()
        elif newshape == "round":
            newtree = RoundTree()
        elif newshape == "cone":
            newtree = ConeTree()
        elif newshape == "rainforest":
            newtree = RainforestTree()
        elif newshape == "mangrove":
            newtree = MangroveTree()

        # Get the height and position of the existing trees in
        # the list.
        newtree.copy(treelist[i])
        # Now check each tree to ensure that it doesn't stick
        # out the top of the map.  If it does, shorten it until
        # the top of the foliage just touches the top of the map.
        if MAPHEIGHTLIMIT:
            height = newtree.height
            ybase = newtree.pos[1]
            if SHAPE == "rainforest":
                foliageheight = 2
            else:
                foliageheight = 4
            if ybase + height + foliageheight > mapheight:
                newheight = mapheight - ybase - foliageheight
                newtree.height = newheight
        # Even if it sticks out the top of the map, every tree
        # should be at least one unit tall.
        if newtree.height < 1:
            newtree.height = 1
        newtree.prepare(mcmap)
        treelist[i] = newtree


def main(the_map):
    '''create the trees
    '''
    treelist = []
    if VERBOSE:
        print("Planting new trees")
    planttrees(the_map, treelist)
    if VERBOSE:
        print("Processing tree changes")
    processtrees(the_map, treelist)
    if FOLIAGE:
        if VERBOSE:
            print("Generating foliage ")
        for i in treelist:
            i.makefoliage(the_map)
        if VERBOSE:
            print(' completed')
    if WOOD:
        if VERBOSE:
            print("Generating trunks, roots, and branches ")
        for i in treelist:
            i.maketrunk(the_map)
        if VERBOSE:
            print(' completed')
    return None


def standalone():
    if VERBOSE:
        print("Importing the map")
    try:
        the_map = mcInterface.SaveFile(LOADNAME)
    except IOError:
        if VERBOSE:
            print('File name invalid or save file otherwise corrupted. Aborting')
        return None
    main(the_map)
    if LIGHTINGFIX:
        if VERBOSE:
            print("Rough re-lighting the map")
        relight_master.save_file = the_map
        relight_master.calc_lighting()
    if VERBOSE:
        print("Saving the map, this could be a while")
    the_map.write()
    if VERBOSE:
        print("finished")

if __name__ == '__main__':
    standalone()

# to do:
# get height limits from map
# set "limit height" or somesuch to respect level height limits
