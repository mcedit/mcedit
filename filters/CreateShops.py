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

Professions = {
	"Farmer (brown)": 0,
	"Librarian (white)": 1,
	"Priest (purple)": 2,
	"Blacksmith (black apron)": 3,
	"Butcher (white apron)": 4,
	"Villager (green)": 5,
	}
	
ProfessionKeys = ()
for key in Professions.keys():
	ProfessionKeys = ProfessionKeys + (key,)
	

inputs = (
	("Profession", ProfessionKeys),
	("Add Unusable Trade", False),
	("Invincible Villagers", False),
	("Unlimited Trades", True),
)

displayName = "Create Shops"


def perform(level, box, options):
	emptyTrade = options["Add Unusable Trade"]
	invincible = options["Invincible Villagers"]
	unlimited = options["Unlimited Trades"]
	
	for x in range(box.minx, box.maxx):
		for y in range(box.miny, box.maxy):
			for z in range(box.minz, box.maxz):
				if level.blockAt(x, y, z) == 54:
					createShop(level, x, y, z, emptyTrade, invincible, Professions[options["Profession"]], unlimited)

def createShop(level, x, y, z, emptyTrade, invincible, profession, unlimited):
	chest = level.tileEntityAt(x, y, z)
	if chest == None:
		return

	priceList = {}
	priceListB = {}
	saleList = {}

	for item in chest["Items"]:
		slot = item["Slot"].value
		if slot >= 0 and slot <= 8:
			priceList[slot] = item
		elif slot >= 9 and slot <= 17:
			priceListB[slot-9] = item
		elif slot >= 18 and slot <= 26:
			saleList[slot-18] = item

	villager = TAG_Compound()
	villager["OnGround"] = TAG_Byte(1)
	villager["Air"] = TAG_Short(300)
	villager["AttackTime"] = TAG_Short(0)
	villager["DeathTime"] = TAG_Short(0)
	villager["Fire"] = TAG_Short(-1)
	villager["Health"] = TAG_Short(20)
	villager["HurtTime"] = TAG_Short(0)
	villager["Age"] = TAG_Int(0)
	villager["Profession"] = TAG_Int(profession)
	villager["Riches"] = TAG_Int(0)
	villager["FallDistance"] = TAG_Float(0)
	villager["id"] = TAG_String("Villager")
	villager["Motion"] = TAG_List()
	villager["Motion"].append(TAG_Double(0))
	villager["Motion"].append(TAG_Double(0))
	villager["Motion"].append(TAG_Double(0))
	villager["Pos"] = TAG_List()
	villager["Pos"].append(TAG_Double(x + 0.5))
	villager["Pos"].append(TAG_Double(y))
	villager["Pos"].append(TAG_Double(z + 0.5))
	villager["Rotation"] = TAG_List()
	villager["Rotation"].append(TAG_Float(0))
	villager["Rotation"].append(TAG_Float(0))

	villager["Offers"] = TAG_Compound()
	villager["Offers"]["Recipes"] = TAG_List()
	for i in range(9):
		if (i in priceList or i in priceListB) and i in saleList:
			offer = TAG_Compound()
			if unlimited:
				offer["uses"] = TAG_Int(-2000000000)
			else:
				offer["uses"] = TAG_Int(0)
			
			if i in priceList:
				offer["buy"] = priceList[i]
			if i in priceListB:
				if i in priceList:
					offer["buyB"] = priceListB[i]
				else:
					offer["buy"] = priceListB[i]
			
			offer["sell"] = saleList[i]
			villager["Offers"]["Recipes"].append(offer)

	if emptyTrade:
		offer = TAG_Compound()
		offer["buy"] = TAG_Compound()
		offer["buy"]["Count"] = TAG_Byte(1)
		offer["buy"]["Damage"] = TAG_Short(0)
		offer["buy"]["id"] = TAG_Short(36)
		offer["sell"] = TAG_Compound()
		offer["sell"]["Count"] = TAG_Byte(1)
		offer["sell"]["Damage"] = TAG_Short(0)
		offer["sell"]["id"] = TAG_Short(36)
		villager["Offers"]["Recipes"].append(offer)

	if invincible:
		if "ActiveEffects" not in villager:
			villager["ActiveEffects"] = TAG_List()

			resist = TAG_Compound()
			resist["Amplifier"] = TAG_Byte(4)
			resist["Id"] = TAG_Byte(11)
			resist["Duration"] = TAG_Int(2000000000)
			villager["ActiveEffects"].append(resist)

	level.setBlockAt(x, y, z, 0)

	chunk = level.getChunk(x / 16, z / 16)
	chunk.Entities.append(villager)
	chunk.TileEntities.remove(chest)
	chunk.dirty = True
