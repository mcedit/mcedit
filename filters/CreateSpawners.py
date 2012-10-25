# Feel free to modify and use this filter however you wish. If you do,
# please give credit to SethBling.
# http://youtube.com/SethBling

from pymclevel import TAG_Compound
from pymclevel import TAG_Int
from pymclevel import TAG_Short
from pymclevel import TAG_Byte
from pymclevel import TAG_String
from pymclevel import TAG_Float
from pymclevel import TAG_Double
from pymclevel import TAG_List
from pymclevel import TileEntity

displayName = "Create Spawners"

inputs = (
	("Include position data", False),
)

def perform(level, box, options):
	includePos = options["Include position data"]
	entitiesToRemove = []

	for (chunk, slices, point) in level.getChunkSlices(box):
	
		for entity in chunk.Entities:
			x = int(entity["Pos"][0].value)
			y = int(entity["Pos"][1].value)
			z = int(entity["Pos"][2].value)
			
			if x >= box.minx and x < box.maxx and y >= box.miny and y < box.maxy and z >= box.minz and z < box.maxz:
				entitiesToRemove.append((chunk, entity))

				level.setBlockAt(x, y, z, 52)

				spawner = TileEntity.Create("MobSpawner")
				TileEntity.setpos(spawner, (x, y, z))
				spawner["Delay"] = TAG_Short(120)
				spawner["SpawnData"] = entity
				if not includePos:
					del spawner["SpawnData"]["Pos"]
				spawner["EntityId"] = entity["id"]
				
				chunk.TileEntities.append(spawner)
		
	for (chunk, entity) in entitiesToRemove:
		chunk.Entities.remove(entity)
