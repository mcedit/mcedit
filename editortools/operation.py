import atexit
import os
import shutil
import tempfile
import albow
from pymclevel import BoundingBox
import numpy
from albow.root import Cancel
import pymclevel
from mceutils import showProgress
from pymclevel.mclevelbase import exhaust

undo_folder = os.path.join(tempfile.gettempdir(), "mcedit_undo", str(os.getpid()))

def mkundotemp():
    if not os.path.exists(undo_folder):
        os.makedirs(undo_folder)

    return tempfile.mkdtemp("mceditundo", dir=undo_folder)

atexit.register(shutil.rmtree, undo_folder, True)

class Operation(object):
    changedLevel = True
    undoLevel = None

    def __init__(self, editor, level):
        self.editor = editor
        self.level = level

    def extractUndo(self, level, box):
        if isinstance(level, pymclevel.MCInfdevOldLevel):
            return self.extractUndoChunks(level, box.chunkPositions, box.chunkCount)
        else:
            return self.extractUndoSchematic(level, box)

    def extractUndoChunks(self, level, chunks, chunkCount = None):
        if not isinstance(level, pymclevel.MCInfdevOldLevel):
            chunks = numpy.array(list(chunks))
            mincx, mincz = numpy.min(chunks, 0)
            maxcx, maxcz = numpy.max(chunks, 0)
            box = BoundingBox((mincx << 4, 0, mincz << 4), (maxcx << 4, level.Height, maxcz << 4))

            return self.extractUndoSchematic(level, box)

        undoLevel = pymclevel.MCInfdevOldLevel(mkundotemp(), create=True)
        if not chunkCount:
            try:
                chunkCount = len(chunks)
            except TypeError:
                chunkCount = -1

        def _extractUndo():
            yield 0, 0, "Recording undo..."
            for i, (cx, cz) in enumerate(chunks):
                undoLevel.copyChunkFrom(level, cx, cz)
                yield i, chunkCount, "Copying chunk %s..." % ((cx, cz),)
            undoLevel.saveInPlace()

        if chunkCount > 25 or chunkCount < 1:
            if "Canceled" == showProgress("Recording undo...", _extractUndo(), cancel=True):
                if albow.ask("Continue with undo disabled?", ["Continue", "Cancel"]) == "Cancel":
                    raise Cancel
                else:
                    return None
        else:
            exhaust(_extractUndo())

        return undoLevel

    def extractUndoSchematic(self, level, box):
        if box.volume > 131072:
            sch = showProgress("Recording undo...", level.extractZipSchematicIter(box), cancel=True)
        else:
            sch = level.extractZipSchematic(box)
        if sch == "Cancel":
            raise Cancel
        if sch:
            sch.sourcePoint = box.origin

        return sch


    # represents a single undoable operation
    def perform(self, recordUndo=True):
        " Perform the operation. Record undo information if recordUndo"

    def undo(self):
        """ Undo the operation. Ought to leave the Operation in a state where it can be performed again.
            Default implementation copies all chunks in undoLevel back into level. Non-chunk-based operations
            should override this."""

        if self.undoLevel:

            def _undo():
                yield 0, 0, "Undoing..."
                if hasattr(self.level, 'copyChunkFrom'):
                    for i, (cx, cz) in enumerate(self.undoLevel.allChunks):
                        self.level.copyChunkFrom(self.undoLevel, cx, cz)
                        yield i, self.undoLevel.chunkCount, "Copying chunk %s..." % ((cx, cz),)
                else:
                    for i in self.level.copyBlocksFromIter(self.undoLevel, self.undoLevel.bounds, self.undoLevel.sourcePoint, biomes=True):
                        yield i, self.undoLevel.chunkCount, "Copying..."

            if self.undoLevel.chunkCount > 25:
                showProgress("Undoing...", _undo())
            else:
                exhaust(_undo())

            self.editor.invalidateChunks(self.undoLevel.allChunks)


    def dirtyBox(self):
        """ The region modified by the operation.
        Return None to indicate no blocks were changed.
        """
        return None
