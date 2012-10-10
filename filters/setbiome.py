# SethBling's SetBiome Filter
# Directions: Just select a region and use this filter, it will apply the
# biome to all columns within the selected region. It can be used on regions
# of any size, they need not correspond to chunks.
#
# If you modify and redistribute this code, please credit SethBling

from pymclevel import MCSchematic
from pymclevel import TAG_Compound
from pymclevel import TAG_Short
from pymclevel import TAG_Byte
from pymclevel import TAG_Byte_Array
from pymclevel import TAG_String
from numpy import zeros

inputs = (
    ("Biome", ("Desert",
               "Mushroom Island",
               "Ocean",
               "Plains",
               "Mountains",
               "Forest",
               "Taiga",
               "Swamp",
               "River",
               "Nether",
               "Sky",
               "Frozen Ocean",
               "Frozen River",
               "Ice Plains",
               "Ice Mountains",
               "Mushroom Shore",
               "Beach",
               "Desert Hills",
               "Forest Hills",
               "Taiga Hills",
               "Mountains Edge",
               "Jungle",
               "Jungle Hills",
               )),
)

biomes = {
    "Ocean":0,
    "Plains":1,
    "Desert":2,
    "Mountains":3,
    "Forest":4,
    "Taiga":5,
    "Swamp":6,
    "River":7,
    "Nether":8,
    "Sky":9,
    "Frozen Ocean":10,
    "Frozen River":11,
    "Ice Plains":12,
    "Ice Mountains":13,
    "Mushroom Island":14,
    "Mushroom Shore":15,
    "Beach":16,
    "Desert Hills":17,
    "Forest Hills":18,
    "Taiga Hills":19,
    "Mountains Edge":20,
    "Jungle":21,
    "Jungle Hills":22,
    }

def perform(level, box, options):
    biome = biomes[options["Biome"]]

    minx = int(box.minx/16)*16
    minz = int(box.minz/16)*16

    for x in xrange(minx, box.maxx, 16):
        for z in xrange(minz, box.maxz, 16):
            chunk = level.getChunk(x / 16, z / 16)
            chunk.decompress()
            chunk.dirty = True
            array = chunk.root_tag["Level"]["Biomes"].value

            chunkx = int(x/16)*16
            chunkz = int(z/16)*16

            for bx in xrange(max(box.minx, chunkx), min(box.maxx, chunkx+16)):
                for bz in xrange(max(box.minz, chunkz), min(box.maxz, chunkz+16)):
                    idx = 16*(bz-chunkz)+(bx-chunkx)
                    array[idx] = biome

            chunk.root_tag["Level"]["Biomes"].value = array
