# Feel free to modify and use this filter however you wish. If you do,
# please give credit to SethBling.
# http://youtube.com/SethBling

from pymclevel import TAG_List
from pymclevel import TAG_Byte
from pymclevel import TAG_Int
from pymclevel import TAG_Compound

displayName = "Add Potion Effect to Mobs"

Effects = {
	"Strength": 5,
	"Jump Boost": 8,
	"Regeneration": 10,
	"Fire Resistance": 12,
	"Water Breathing": 13,
	"Resistance": 11,
	"Weakness": 18,
	"Poison": 19,
	"Speed (no mob effect)": 1,
	"Slowness (no mob effect)": 2,
	"Haste (no mob effect)": 3,
	"Mining Fatigue (no mob effectg)": 4,
	"Nausea (no mob effect)": 9,
	"Blindness (no mob effect)": 15,
	"Hunger (no mob effect)": 17,
	"Invisibility (no effect)": 14,
	"Night Vision (no effect)": 16,
	}
	
EffectKeys = ()
for key in Effects.keys():
	EffectKeys = EffectKeys + (key,)
	

inputs = (
	("Effect", EffectKeys),
	("Level", 1),
	("Duration (Seconds)", 60),
)

def perform(level, box, options):
	effect = Effects[options["Effect"]]
	amp = options["Level"]
	duration = options["Duration (Seconds)"] * 20

	for (chunk, slices, point) in level.getChunkSlices(box):
		for e in chunk.Entities:
			x = e["Pos"][0].value
			y = e["Pos"][1].value
			z = e["Pos"][2].value
			
			if x >= box.minx and x < box.maxx and y >= box.miny and y < box.maxy and z >= box.minz and z < box.maxz:
				if "Health" in e:
					if "ActiveEffects" not in e:
						e["ActiveEffects"] = TAG_List()

					ef = TAG_Compound()
					ef["Amplifier"] = TAG_Byte(amp)
					ef["Id"] = TAG_Byte(effect)
					ef["Duration"] = TAG_Int(duration)
					e["ActiveEffects"].append(ef)
					chunk.dirty = True
