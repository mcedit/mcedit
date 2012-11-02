import pymclevel
from pymclevel.minecraft_server import MCServerChunkGenerator
from pymclevel import BoundingBox
import logging
logging.basicConfig(level=logging.INFO)

gen = MCServerChunkGenerator()

half_width = 4096

gen.createLevel("HugeWorld", BoundingBox((-half_width, 0, -half_width), (half_width, 0, half_width)))
