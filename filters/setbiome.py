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
    ("Biome", ( "Ocean",
				"Plains",
				"Desert",
				"Extreme Hills",
				"Forest",
				"Taiga",
				"Swamppland",
				"River",
				"Hell (Nether)",
				"Sky (End)",
				"Frozen Ocean",
				"Frozen River",
				"Ice Plains",
				"Ice Mountains",
				"Mushroom Island",
				"Mushroom Island Shore",
				"Beach",
				"Desert Hills",
				"Forest Hills",
				"Taiga Hills",
				"Extreme Hills Edge",
				"Jungle",
				"Jungle Hills",
				"Jungle Edge",
				"Deep Ocean",
				"Stone Beach",
				"Cold Beach",
				"Birch Forest",
				"Birch Forest Hills",
				"Roofed Forest",
				"Cold Taiga",
				"Cold Taiga Hills",
				"Mega Taiga",
				"Mega Taiga Hills",
				"Extreme Hills+",
				"Savanna",
				"Savanna Plateau",
				"Messa",
				"Messa Plateau F",
				"Messa Plateau",
				"Sunflower Plains",
				"Desert M",
				"Extreme Hills M",
				"Flower Forest",
				"Taiga M",
				"Swampland M",
				"Ice Plains Spikes",
				"Ice Mountains Spikes",
				"Jungle M",
				"JungleEdge M",
				"Birch Forest M",
				"Birch Forest Hills M",
				"Roofed Forest M",
				"Cold Taiga M",
				"Mega Spruce Taiga",
				"Mega Spruce Taiga ",
				"Extreme Hills+ M",
				"Savanna M",
				"Savanna Plateau M",
				"Mesa (Bryce)",
				"Mesa Plateau F M",
				"Mesa Plateau M",
				"(Uncalculated)",
				)),
)

biomes = {
    "Ocean":0,
    "Plains":1,
    "Desert":2,
    "Extreme Hills":3,
    "Forest":4,
    "Taiga":5,
    "Swamppland":6,
    "River":7,
    "Hell (Nether)":8,
    "Sky (End)":9,
    "Frozen Ocean":10,
    "Frozen River":11,
    "Ice Plains":12,
    "Ice Mountains":13,
    "Mushroom Island":14,
    "Mushroom Island Shore":15,
    "Beach":16,
    "Desert Hills":17,
    "Forest Hills":18,
    "Taiga Hills":19,
    "Extreme Hills Edge":20,
    "Jungle":21,
    "Jungle Hills":22,
    "Jungle Edge":23,
    "Deep Ocean":24,
    "Stone Beach":25,
    "Cold Beach":26,
    "Birch Forest":27,
    "Birch Forest Hills":28,
    "Roofed Forest":29,
    "Cold Taiga":30,
    "Cold Taiga Hills":31,
    "Mega Taiga":32,
    "Mega Taiga Hills":33,
    "Extreme Hills+":34,
    "Savanna":35,
    "Savanna Plateau":36,
    "Messa":37,
    "Messa Plateau F":38,
    "Messa Plateau":39,
    "Sunflower Plains":129,
    "Desert M":130,
    "Extreme Hills M":131,
    "Flower Forest":132,
    "Taiga M":133,
    "Swampland M":134,
    "Ice Plains Spikes":140,
    "Ice Mountains Spikes":141,
    "Jungle M":149,
    "JungleEdge M":151,
    "Birch Forest M":155,
    "Birch Forest Hills M":156,
    "Roofed Forest M":157,
    "Cold Taiga M":158,
    "Mega Spruce Taiga":160,
    "Mega Spruce Taiga 2":161,
    "Extreme Hills+ M":162,
    "Savanna M":163,
    "Savanna Plateau M":164,
    "Mesa (Bryce)":165,
    "Mesa Plateau F M":166,
    "Mesa Plateau M":167,
    "(Uncalculated)":-1,
    }

def perform(level, box, options):
    biome = biomes[options["Biome"]]

    minx = int(box.minx/16)*16
    minz = int(box.minz/16)*16

    for x in xrange(minx, box.maxx, 16):
        for z in xrange(minz, box.maxz, 16):
            chunk = level.getChunk(x / 16, z / 16)
            chunk.dirty = True
            array = chunk.root_tag["Level"]["Biomes"].value

            chunkx = int(x/16)*16
            chunkz = int(z/16)*16

            for bx in xrange(max(box.minx, chunkx), min(box.maxx, chunkx+16)):
                for bz in xrange(max(box.minz, chunkz), min(box.maxz, chunkz+16)):
                    idx = 16*(bz-chunkz)+(bx-chunkx)
                    array[idx] = biome

            chunk.root_tag["Level"]["Biomes"].value = array
