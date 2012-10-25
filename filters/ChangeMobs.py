# Feel free to modify and use this filter however you wish. If you do,
# please give credit to SethBling.
# http://youtube.com/SethBling

from pymclevel import TAG_List
from pymclevel import TAG_Byte
from pymclevel import TAG_Int
from pymclevel import TAG_Compound
from pymclevel import TAG_Short
from pymclevel import TAG_Double
from pymclevel import TAG_String

displayName = "Change Mob Properties"

Professions = {
	"Farmer (brown)": 0,
	"Librarian (white)": 1,
	"Priest (purple)": 2,
	"Blacksmith (black apron)": 3,
	"Butcher (white apron)": 4,
	"Villager (green)": 5,
	}
	
ProfessionKeys = ("N/A",)
for key in Professions.keys():
	ProfessionKeys = ProfessionKeys + (key,)
	
	

noop = -1337
	
inputs = (
	("Health", noop),
	("VelocityX", noop),
	("VelocityY", noop),
	("VelocityZ", noop),
	("Fire", noop),
	("FallDistance", noop),
	("Air", noop),
	("AttackTime", noop),
	("HurtTime", noop),
	("Lightning Creeper", ("N/A", "Lightning", "No Lightning")),
	("Enderman Block Id", noop),
	("Enderman Block Data", noop),
	("Villager Profession", ProfessionKeys),
	("Slime Size", noop),
	("Breeding Mode Ticks", noop),
	("Child/Adult Age", noop),
)

def perform(level, box, options):
	health = options["Health"]
	vx = options["VelocityX"]
	vy = options["VelocityY"]
	vz = options["VelocityZ"]
	fire = options["Fire"]
	fall = options["FallDistance"]
	air = options["Air"]
	attackTime = options["AttackTime"]
	hurtTime = options["HurtTime"]
	powered = options["Lightning Creeper"]
	blockId = options["Enderman Block Id"]
	blockData = options["Enderman Block Data"]
	profession = options["Villager Profession"]
	size = options["Slime Size"]
	breedTicks = options["Breeding Mode Ticks"]
	age = options["Child/Adult Age"]
	

	for (chunk, slices, point) in level.getChunkSlices(box):
		for e in chunk.Entities:
			x = e["Pos"][0].value
			y = e["Pos"][1].value
			z = e["Pos"][2].value
			
			if x >= box.minx and x < box.maxx and y >= box.miny and y < box.maxy and z >= box.minz and z < box.maxz:
				if "Health" in e:
					if health != noop:
						e["Health"] = TAG_Short(health)
						
					if vx != noop:
						e["Motion"][0] = TAG_Double(vx)
					if vy != noop:
						e["Motion"][1] = TAG_Double(vy)
					if vz != noop:
						e["Motion"][2] = TAG_Double(vz)
					
					if fire != noop:
						e["Fire"] = TAG_Short(fire)
					
					if fall != noop:
						e["FallDistance"] = TAG_Float(fall)
					
					if air != noop:
						e["Air"] = TAG_Short(air)
					
					if attackTime != noop:
						e["AttackTime"] = TAG_Short(attackTime)
					
					if hurtTime != noop:
						e["HurtTime"] = TAG_Short(hurtTime)
					
					if powered != "N/A" and e["id"].value == "Creeper":
						if powered == "Lightning":
							e["powered"] = TAG_Byte(1)
						if powered == "No Lightning":
							e["powered"] = TAG_Byte(0)

					if blockId != noop and e["id"].value == "Enderman":
						e["carried"] = TAG_Short(blockId)
					if blockData != noop and e["id"].value == "Enderman":
						e["carriedData"] = TAG_Short(blockData)
					
					if profession != "N/A" and e["id"].value == "Villager":
						e["Profession"] = TAG_Int(Professions[profession])
					
					if size != noop and e["id"].value == "Slime":
						e["Size"] = TAG_Int(size)
					
					if breedTicks != noop:
						e["InLove"] = TAG_Int(breedTicks)
					
					if age != noop:
						e["Age"] = TAG_Int(age)
					
					chunk.dirty = True
