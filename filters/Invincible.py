# Feel free to modify and use this filter however you wish. If you do,
# please give credit to SethBling.
# http://youtube.com/SethBling

from pymclevel import TAG_List
from pymclevel import TAG_Byte
from pymclevel import TAG_Int
from pymclevel import TAG_Compound

displayName = "Make Mobs Invincible"

def perform(level, box, options):
    for (chunk, slices, point) in level.getChunkSlices(box):
        for e in chunk.Entities:
            x = e["Pos"][0].value
            y = e["Pos"][1].value
            z = e["Pos"][2].value

            if x >= box.minx and x < box.maxx and y >= box.miny and y < box.maxy and z >= box.minz and z < box.maxz:
                if "Health" in e:
                    if "ActiveEffects" not in e:
                        e["ActiveEffects"] = TAG_List()

                    resist = TAG_Compound()
                    resist["Amplifier"] = TAG_Byte(4)
                    resist["Id"] = TAG_Byte(11)
                    resist["Duration"] = TAG_Int(2000000000)
                    e["ActiveEffects"].append(resist)
                    chunk.dirty = True
