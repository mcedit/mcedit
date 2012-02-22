"""Copyright (c) 2010-2012 David Rio Vierra

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE."""



from toolbasics import *
from select import SelectionTool
from brush import BrushTool
from fill import FillTool
from clone import CloneTool, ConstructionTool
from filter import FilterTool
from player import PlayerPositionTool, PlayerSpawnPositionTool
from chunk import ChunkTool
"""
class CameraTool(EditorTool):
    snapshotCounter = 0;
    def toolSelected(self, *args):
        glReadBuffer(GL_FRONT);

        (w, h) = self.editor.size

        pixels = glReadPixels(0, 0, w, h, GL_RGB, GL_UNSIGNED_BYTE);

        try:
            (filename, customfilter, flags) = win32gui.GetSaveFileNameW(
                hwndOwner = display.get_wm_info()['window'],
                InitialDir='My Documents',
                Flags=win32con.OFN_EXPLORER | win32con.OFN_OVERWRITEPROMPT,
                File='.'.join(self.editor.level.filename.split('.')[:-1]) + '-Snapshot%04d'% self.snapshotCounter,
                DefExt='png',
                Title='Save this snapshot...',
                Filter='PNG files\0*.png\0\0',
                )
        except :
            #print e;
            pass
        else:
            self.snapshotCounter += 1;
            pixarray = fromstring(pixels, dtype='uint8')
            #print len(pixarray), w, h;
            #print pixarray[0:24];
            pixgrid = pixarray.reshape(h,w*3) #3bpp
            writer = png.Writer(int(w), int(h));
            writer.write_array(file(filename, "wb"), pixgrid[::-1,:].flatten());  #black magic!  no, an array slice with negative stepping

            # glLineWidth(1.0);"""
