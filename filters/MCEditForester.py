'''MCEditForester.py
   Tree-generating script by dudecon
   http://www.minecraftforum.net/viewtopic.php?f=1022&t=219461

   Needs the dummy mcInterface for MCEdit, and the default Forester script.
'''

from pymclevel.materials import alphaMaterials
import Forester
import mcInterface

displayName = "Forester"

inputs = (
    ("Forester script by dudecon", "label"),
    ("Shape", ("Procedural",
               "Normal",
               "Bamboo",
               "Palm",
               "Stickly",
               "Round",
               "Cone",
               "Rainforest",
               "Mangrove",
               )),

    ("Tree Count", 2),
    ("Tree Height", 35),
    ("Height Variation", 12),

    ("Branch Density", 1.0),
    ("Trunk Thickness", 1.0),
    ("Broken Trunk", False),
    ("Hollow Trunk", False),
    ("Wood", True),

    ("Foliage", True),
    ("Foliage Density", 1.0),

    ("Roots", ("Yes", "To Stone", "Hanging", "No")),
    ("Root Buttresses", False),

    ("Wood Material", alphaMaterials.Wood),
    ("Leaf Material", alphaMaterials.Leaves),
    ("Plant On", alphaMaterials.Grass),

)


def perform(level, box, options):
    '''Load the file, create the trees, and save the new file.
    '''
    # set up the non 1 to 1 mappings of options to Forester global names
    optmap = {
        "Tree Height": "CENTERHEIGHT",
    }
    # automatically set the options that map 1 to 1 from options to Forester

    def setOption(opt):
        OPT = optmap.get(opt, opt.replace(" ", "").upper())
        if OPT in dir(Forester):
            val = options[opt]
            if isinstance(val, str):
                val = val.replace(" ", "").lower()

            setattr(Forester, OPT, val)

    # set all of the options
    for option in options:
        setOption(option)
    # set the EDGEHEIGHT the same as CENTERHEIGHT
    Forester.EDGEHEIGHT = Forester.CENTERHEIGHT
    # set the materials
    wood = options["Wood Material"]
    leaf = options["Leaf Material"]
    grass = options["Plant On"]

    Forester.WOODINFO = {"B": wood.ID, "D": wood.blockData}
    Forester.LEAFINFO = {"B": leaf.ID, "D": leaf.blockData}
    Forester.PLANTON = [grass.ID]

    # calculate the plant-on center and radius
    x_center = int(box.minx + (box.width / 2))
    z_center = int(box.minz + (box.length / 2))
    edge_padding = int(Forester.EDGEHEIGHT * 0.618)
    max_dim = min(box.width, box.length)
    planting_radius = (max_dim / 2) - edge_padding
    if planting_radius <= 1:
        planting_radius = 1
        Forester.TREECOUNT = 1
        print("Box isn't wide and/or long enough. Only planting one tree.")
    # set the position to plant
    Forester.X = x_center
    Forester.Z = z_center
    Forester.RADIUS = planting_radius
    print("Plant radius = " + str(planting_radius))

    # set the Forester settings that are not in the inputs
    # and should be a specific value
    # take these out if added to settings
    Forester.LIGHTINGFIX = False
    Forester.MAXTRIES = 5000
    Forester.VERBOSE = True

    # create the dummy map object
    mcmap = mcInterface.MCLevelAdapter(level, box)
    # call forester's main function on the map object.
    Forester.main(mcmap)

    level.markDirtyBox(box)
