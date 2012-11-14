import atexit
import shutil
import tempfile
import pymclevel
from mceutils import showProgress

class Operation(object):
    changedLevel = True
    undoLevel = None

    def __init__(self, editor, level):
        self.editor = editor
        self.level = level

    def extractUndo(self, level, box):
        return self.extractUndoChunks(level, box.chunkPositions, box.chunkCount)

    def extractUndoChunks(self, level, chunks, chunkCount = None):
        undoPath = tempfile.mkdtemp("mceditundo")
        undoLevel = pymclevel.MCInfdevOldLevel(undoPath, create=True)
        atexit.register(shutil.rmtree, undoPath, True)
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

        showProgress("Recording undo...", _extractUndo())

        return undoLevel

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
                for i, (cx, cz) in enumerate(self.undoLevel.allChunks):
                    self.level.copyChunkFrom(self.undoLevel, cx, cz)
                    yield i, self.undoLevel.chunkCount, "Copying chunk %s..." % ((cx, cz),)


            showProgress("Undoing...", _undo())
            self.editor.invalidateChunks(self.undoLevel.allChunks)


    def dirtyBox(self):
        """ The region modified by the operation.
        Return None to indicate no blocks were changed.
        """
        return None
