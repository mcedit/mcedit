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
import collections
from datetime import datetime
import numpy
from numpy import newaxis
import pygame
from albow import AttrRef, Button, ValueDisplay, Row, Label, ValueButton, Column, IntField, CheckBox, FloatField, alert
import bresenham
from editortools.blockpicker import BlockPicker
from editortools.blockview import BlockButton
from editortools.editortool import EditorTool
from editortools.tooloptions import ToolOptions
from glbackground import Panel
from glutils import gl
import mcplatform
from pymclevel import block_fill, BoundingBox
import pymclevel
from pymclevel.level import extractHeights
from mceutils import ChoiceButton, CheckBoxLabel, showProgress, IntInputRow, alertException, drawTerrainCuttingWire
from os.path import basename
import tempfile
import itertools
import logging
from operation import Operation, mkundotemp
from pymclevel.mclevelbase import exhaust

from OpenGL import GL

log = logging.getLogger(__name__)

import config

BrushSettings = config.Settings("Brush")
BrushSettings.brushSizeL = BrushSettings("Brush Shape L", 3)
BrushSettings.brushSizeH = BrushSettings("Brush Shape H", 3)
BrushSettings.brushSizeW = BrushSettings("Brush Shape W", 3)
BrushSettings.updateBrushOffset = BrushSettings("Update Brush Offset", False)
BrushSettings.chooseBlockImmediately = BrushSettings("Choose Block Immediately", False)
BrushSettings.alpha = BrushSettings("Alpha", 0.66)

class BrushMode(object):
    options = []

    def brushBoxForPointAndOptions(self, point, options={}):
        # Return a box of size options['brushSize'] centered around point.
        # also used to position the preview reticle
        size = options['brushSize']
        origin = map(lambda x, s: x - (s >> 1), point, size)
        return BoundingBox(origin, size)

    def apply(self, op, point):
        """
        Called by BrushOperation for brush modes that can't be implemented using applyToChunk
        """
        pass
    apply = NotImplemented

    def applyToChunk(self, op, chunk, point):
        """
        Called by BrushOperation to apply this brush mode to the given chunk with a brush centered on point.
        Default implementation will compute:
          brushBox: a BoundingBox for the world area affected by this brush,
          brushBoxThisChunk: a box for the portion of this chunk affected by this brush,
          slices: a tuple of slices that can index the chunk's Blocks array to select the affected area.

        These three parameters are passed to applyToChunkSlices along with the chunk and the brush operation.
        Brush modes must implement either applyToChunk or applyToChunkSlices
        """
        brushBox = self.brushBoxForPointAndOptions(point, op.options)

        brushBoxThisChunk, slices = chunk.getChunkSlicesForBox(brushBox)
        if brushBoxThisChunk.volume == 0: return

        return self.applyToChunkSlices(op, chunk, slices, brushBox, brushBoxThisChunk)

    def applyToChunkSlices(self, op, chunk, slices, brushBox, brushBoxThisChunk):
        raise NotImplementedError

    def createOptions(self, panel, tool):
        pass


class Modes:
    class Fill(BrushMode):
        name = "Fill"

        def createOptions(self, panel, tool):
            col = [
                panel.modeStyleGrid,
                panel.hollowRow,
                panel.noiseInput,
                panel.brushSizeRows,
                panel.blockButton,
            ]
            return col

        def applyToChunkSlices(self, op, chunk, slices, brushBox, brushBoxThisChunk):
            brushMask = createBrushMask(op.brushSize, op.brushStyle, brushBox.origin, brushBoxThisChunk, op.noise, op.hollow)

            chunk.Blocks[slices][brushMask] = op.blockInfo.ID
            chunk.Data[slices][brushMask] = op.blockInfo.blockData

    class FloodFill(BrushMode):
        name = "Flood Fill"
        options = ['indiscriminate']

        def createOptions(self, panel, tool):
            col = [
                panel.brushModeRow,
                panel.blockButton
            ]
            indiscriminateButton = CheckBoxLabel("Indiscriminate", ref=AttrRef(tool, 'indiscriminate'))

            col.append(indiscriminateButton)
            return col

        def apply(self, op, point):

            undoLevel = pymclevel.MCInfdevOldLevel(mkundotemp(), create=True)
            dirtyChunks = set()

            def saveUndoChunk(cx, cz):
                if (cx, cz) in dirtyChunks:
                    return
                dirtyChunks.add((cx, cz))
                undoLevel.copyChunkFrom(op.level, cx, cz)

            doomedBlock = op.level.blockAt(*point)
            doomedBlockData = op.level.blockDataAt(*point)
            checkData = (doomedBlock not in (8, 9, 10, 11))
            indiscriminate = op.options['indiscriminate']

            if doomedBlock == op.blockInfo.ID:
                return
            if indiscriminate:
                checkData = False
                if doomedBlock == 2:  # grass
                    doomedBlock = 3  # dirt

            x, y, z = point
            saveUndoChunk(x // 16, z // 16)
            op.level.setBlockAt(x, y, z, op.blockInfo.ID)
            op.level.setBlockDataAt(x, y, z, op.blockInfo.blockData)

            def processCoords(coords):
                newcoords = collections.deque()

                for (x, y, z) in coords:
                    for _dir, offsets in pymclevel.faceDirections:
                        dx, dy, dz = offsets
                        p = (x + dx, y + dy, z + dz)

                        nx, ny, nz = p
                        b = op.level.blockAt(nx, ny, nz)
                        if indiscriminate:
                            if b == 2:
                                b = 3
                        if b == doomedBlock:
                            if checkData:
                                if op.level.blockDataAt(nx, ny, nz) != doomedBlockData:
                                    continue

                            saveUndoChunk(nx // 16, nz // 16)
                            op.level.setBlockAt(nx, ny, nz, op.blockInfo.ID)
                            op.level.setBlockDataAt(nx, ny, nz, op.blockInfo.blockData)
                            newcoords.append(p)

                return newcoords

            def spread(coords):
                while len(coords):
                    start = datetime.now()

                    num = len(coords)
                    coords = processCoords(coords)
                    d = datetime.now() - start
                    progress = "Did {0} coords in {1}".format(num, d)
                    log.info(progress)
                    yield progress

            showProgress("Flood fill...", spread([point]), cancel=True)
            op.editor.invalidateChunks(dirtyChunks)
            op.undoLevel = undoLevel

    class Replace(Fill):
        name = "Replace"

        def createOptions(self, panel, tool):
            return Modes.Fill.createOptions(self, panel, tool) + [panel.replaceBlockButton]

        def applyToChunkSlices(self, op, chunk, slices, brushBox, brushBoxThisChunk):

            blocks = chunk.Blocks[slices]
            data = chunk.Data[slices]

            brushMask = createBrushMask(op.brushSize, op.brushStyle, brushBox.origin, brushBoxThisChunk, op.noise, op.hollow)

            replaceWith = op.options['replaceBlockInfo']
            # xxx pasted from fill.py
            if op.blockInfo.wildcard:
                print "Wildcard replace"
                blocksToReplace = []
                for i in range(16):
                    blocksToReplace.append(op.editor.level.materials.blockWithID(op.blockInfo.ID, i))
            else:
                blocksToReplace = [op.blockInfo]

            replaceTable = block_fill.blockReplaceTable(blocksToReplace)
            replaceMask = replaceTable[blocks, data]
            brushMask &= replaceMask

            blocks[brushMask] = replaceWith.ID
            data[brushMask] = replaceWith.blockData

    class Erode(BrushMode):
        name = "Erode"
        options = ['erosionStrength']

        def createOptions(self, panel, tool):
            col = [
                panel.modeStyleGrid,
                panel.brushSizeRows,
            ]
            col.append(IntInputRow("Strength: ", ref=AttrRef(tool, 'erosionStrength'), min=1, max=20, tooltipText="Number of times to apply erosion. Larger numbers are slower."))
            return col

        def apply(self, op, point):
            brushBox = self.brushBoxForPointAndOptions(point, op.options).expand(1)

            if brushBox.volume > 1048576:
                raise ValueError("Affected area is too big for this brush mode")

            strength = op.options["erosionStrength"]

            erosionArea = op.level.extractSchematic(brushBox, entities=False)
            if erosionArea is None:
                return

            blocks = erosionArea.Blocks
            bins = numpy.bincount(blocks.ravel())
            fillBlockID = bins.argmax()

            def getNeighbors(solidBlocks):
                neighbors = numpy.zeros(solidBlocks.shape, dtype='uint8')
                neighbors[1:-1, 1:-1, 1:-1] += solidBlocks[:-2, 1:-1, 1:-1]
                neighbors[1:-1, 1:-1, 1:-1] += solidBlocks[2:, 1:-1, 1:-1]
                neighbors[1:-1, 1:-1, 1:-1] += solidBlocks[1:-1, :-2, 1:-1]
                neighbors[1:-1, 1:-1, 1:-1] += solidBlocks[1:-1, 2:, 1:-1]
                neighbors[1:-1, 1:-1, 1:-1] += solidBlocks[1:-1, 1:-1, :-2]
                neighbors[1:-1, 1:-1, 1:-1] += solidBlocks[1:-1, 1:-1, 2:]
                return neighbors

            for i in range(strength):
                solidBlocks = blocks != 0
                neighbors = getNeighbors(solidBlocks)

                brushMask = createBrushMask(op.brushSize, op.brushStyle)
                erodeBlocks = neighbors < 5
                erodeBlocks &= (numpy.random.random(erodeBlocks.shape) > 0.3)
                erodeBlocks[1:-1, 1:-1, 1:-1] &= brushMask
                blocks[erodeBlocks] = 0

                solidBlocks = blocks != 0
                neighbors = getNeighbors(solidBlocks)

                fillBlocks = neighbors > 2
                fillBlocks &= ~solidBlocks
                fillBlocks[1:-1, 1:-1, 1:-1] &= brushMask
                blocks[fillBlocks] = fillBlockID

            op.level.copyBlocksFrom(erosionArea, erosionArea.bounds.expand(-1), brushBox.origin + (1, 1, 1))

    class Topsoil(BrushMode):
        name = "Topsoil"
        options = ['naturalEarth', 'topsoilDepth']

        def createOptions(self, panel, tool):
            depthRow = IntInputRow("Depth: ", ref=AttrRef(tool, 'topsoilDepth'))
            naturalRow = CheckBoxLabel("Only Change Natural Earth", ref=AttrRef(tool, 'naturalEarth'))
            col = [
                panel.modeStyleGrid,
                panel.hollowRow,
                panel.noiseInput,
                panel.brushSizeRows,
                panel.blockButton,
                depthRow,
                naturalRow
            ]
            return col

        def applyToChunkSlices(self, op, chunk, slices, brushBox, brushBoxThisChunk):

            depth = op.options['topsoilDepth']
            blocktype = op.blockInfo

            blocks = chunk.Blocks[slices]
            data = chunk.Data[slices]

            brushMask = createBrushMask(op.brushSize, op.brushStyle, brushBox.origin, brushBoxThisChunk, op.noise, op.hollow)


            if op.options['naturalEarth']:
                try:
                    # try to get the block mask from the topsoil filter
                    import topsoil  # @UnresolvedImport
                    blockmask = topsoil.naturalBlockmask()
                    blockmask[blocktype.ID] = True
                    blocktypeMask = blockmask[blocks]

                except Exception, e:
                    print repr(e), " while using blockmask from filters.topsoil"
                    blocktypeMask = blocks != 0

            else:
                # topsoil any block
                blocktypeMask = blocks != 0

            if depth < 0:
                blocktypeMask &= (blocks != blocktype.ID)

            heightmap = extractHeights(blocktypeMask)

            for x, z in itertools.product(*map(xrange, heightmap.shape)):
                h = heightmap[x, z]
                if h >= brushBoxThisChunk.height:
                    continue
                if depth > 0:
                    idx = x, z, slice(max(0, h - depth), h)
                else:
                    # negative depth values mean to put a layer above the surface
                    idx = x, z, slice(h, min(blocks.shape[2], h - depth))
                mask = brushMask[idx]
                blocks[idx][mask] = blocktype.ID
                data[idx][mask] = blocktype.blockData

    class Paste(BrushMode):

        name = "Paste"
        options = ['level'] + ['center' + c for c in 'xyz']

        def brushBoxForPointAndOptions(self, point, options={}):
            point = [p + options.get('center' + c, 0) for p, c in zip(point, 'xyz')]
            return BoundingBox(point, options['level'].size)

        def createOptions(self, panel, tool):
            col = [panel.brushModeRow]

            importButton = Button("Import", action=tool.importPaste)
            importLabel = ValueDisplay(width=150, ref=AttrRef(tool, "importFilename"))
            importRow = Row((importButton, importLabel))

            stack = tool.editor.copyStack
            if len(stack) == 0:
                tool.importPaste()
            else:
                tool.loadLevel(stack[0])
            tool.centery = 0
            tool.centerx = -(tool.level.Width / 2)
            tool.centerz = -(tool.level.Length / 2)

            cx, cy, cz = [IntInputRow(c, ref=AttrRef(tool, "center" + c), max=a, min=-a)
                          for a, c in zip(tool.level.size, "xyz")]
            centerRow = Row((cx, cy, cz))

            col.extend([importRow, centerRow])

            return col

        def apply(self, op, point):
            level = op.options['level']
            point = [p + op.options['center' + c] for p, c in zip(point, 'xyz')]

            return op.level.copyBlocksFromIter(level, level.bounds, point, create=True)


class BrushOperation(Operation):

    def __init__(self, editor, level, points, options):
        super(BrushOperation, self).__init__(editor, level)

        # if options is None: options = {}

        self.options = options
        self.editor = editor
        if isinstance(points[0], (int, float)):
            points = [points]

        self.points = points

        self.brushSize = options['brushSize']
        self.blockInfo = options['blockInfo']
        self.brushStyle = options['brushStyle']
        self.brushMode = options['brushMode']

        if max(self.brushSize) > BrushTool.maxBrushSize:
            self.brushSize = (BrushTool.maxBrushSize,) * 3
        if max(self.brushSize) < 1:
            self.brushSize = (1, 1, 1)

        boxes = [self.brushMode.brushBoxForPointAndOptions(p, options) for p in points]
        self._dirtyBox = reduce(lambda a, b: a.union(b), boxes)

    brushStyles = ["Round", "Square", "Diamond"]
    # brushModeNames = ["Fill", "Flood Fill", "Replace", "Erode", "Topsoil", "Paste"]  # "Smooth", "Flatten", "Raise", "Lower", "Build", "Erode", "Evert"]
    brushModeClasses = [
        Modes.Fill,
        Modes.FloodFill,
        Modes.Replace,
        Modes.Erode,
        Modes.Topsoil,
        Modes.Paste
    ]

    @property
    def noise(self):
        return self.options.get('brushNoise', 100)

    @property
    def hollow(self):
        return self.options.get('brushHollow', False)



    def dirtyBox(self):
        return self._dirtyBox

    def perform(self, recordUndo=True):
        if recordUndo:
            self.undoLevel = self.extractUndo(self.level, self._dirtyBox)

        def _perform():
            yield 0, len(self.points), "Applying {0} brush...".format(self.brushMode.name)
            if self.brushMode.apply is not NotImplemented: #xxx double negative
                for i, point in enumerate(self.points):
                    f = self.brushMode.apply(self, point)
                    if hasattr(f, "__iter__"):
                        for progress in f:
                            yield progress
                    else:
                        yield i, len(self.points), "Applying {0} brush...".format(self.brushMode.name)
            else:

                for j, cPos in enumerate(self._dirtyBox.chunkPositions):
                    if not self.level.containsChunk(*cPos):
                        continue
                    chunk = self.level.getChunk(*cPos)
                    for i, point in enumerate(self.points):

                        f = self.brushMode.applyToChunk(self, chunk, point)

                        if hasattr(f, "__iter__"):
                            for progress in f:
                                yield progress
                        else:
                            yield j * len(self.points) + i, len(self.points) * self._dirtyBox.chunkCount, "Applying {0} brush...".format(self.brushMode.name)

                    chunk.chunkChanged()

        if len(self.points) > 10:
            showProgress("Performing brush...", _perform(), cancel=True)
        else:
            exhaust(_perform())



class BrushPanel(Panel):
    def __init__(self, tool):
        Panel.__init__(self)
        self.tool = tool

        self.brushModeButton = ChoiceButton([m.name for m in tool.brushModes],
                                            width=150,
                                            choose=self.brushModeChanged)

        self.brushModeButton.selectedChoice = tool.brushMode.name
        self.brushModeRow = Row((Label("Mode:"), self.brushModeButton))

        self.brushStyleButton = ValueButton(width=self.brushModeButton.width,
                                        ref=AttrRef(tool, "brushStyle"),
                                        action=tool.swapBrushStyles)

        self.brushStyleButton.tooltipText = "Shortcut: ALT-1"

        self.brushStyleRow = Row((Label("Brush:"), self.brushStyleButton))

        self.modeStyleGrid = Column([
            self.brushModeRow,
            self.brushStyleRow,
        ])

        shapeRows = []

        for d in ["L", "W", "H"]:
            l = Label(d)
            f = IntField(ref=getattr(BrushSettings, "brushSize" + d).propertyRef(), min=1, max=tool.maxBrushSize)
            row = Row((l, f))
            shapeRows.append(row)

        self.brushSizeRows = Column(shapeRows)

        self.noiseInput = IntInputRow("Chance: ", ref=AttrRef(tool, "brushNoise"), min=0, max=100)

        hollowCheckBox = CheckBox(ref=AttrRef(tool, "brushHollow"))
        hollowLabel = Label("Hollow")
        hollowLabel.mouse_down = hollowCheckBox.mouse_down
        hollowLabel.tooltipText = hollowCheckBox.tooltipText = "Shortcut: ALT-3"

        self.hollowRow = Row((hollowCheckBox, hollowLabel))

        self.blockButton = blockButton = BlockButton(
            tool.editor.level.materials,
            ref=AttrRef(tool, 'blockInfo'),
            recentBlocks=tool.recentFillBlocks,
            allowWildcards=(tool.brushMode.name == "Replace"))

        # col = [modeStyleGrid, hollowRow, noiseInput, shapeRows, blockButton]

        self.replaceBlockButton = replaceBlockButton = BlockButton(
            tool.editor.level.materials,
            ref=AttrRef(tool, 'replaceBlockInfo'),
            recentBlocks=tool.recentReplaceBlocks)

        col = tool.brushMode.createOptions(self, tool)

        if self.tool.brushMode.name != "Flood Fill":
            spaceRow = IntInputRow("Line Spacing", ref=AttrRef(tool, "minimumSpacing"), min=1, tooltipText="Hold SHIFT to draw lines")
            col.append(spaceRow)
        col = Column(col)

        self.add(col)
        self.shrink_wrap()

    def brushModeChanged(self):
        self.tool.brushMode = self.brushModeButton.selectedChoice

    def pickFillBlock(self):
        self.blockButton.action()
        self.tool.blockInfo = self.blockButton.blockInfo
        self.tool.setupPreview()

    def pickReplaceBlock(self):
        self.replaceBlockButton.action()
        self.tool.replaceBlockInfo = self.replaceBlockButton.blockInfo
        self.tool.setupPreview()

    def swap(self):
        t = self.blockButton.recentBlocks
        self.blockButton.recentBlocks = self.replaceBlockButton.recentBlocks
        self.replaceBlockButton.recentBlocks = t

        self.blockButton.updateRecentBlockView()
        self.replaceBlockButton.updateRecentBlockView()
        b = self.blockButton.blockInfo
        self.blockButton.blockInfo = self.replaceBlockButton.blockInfo
        self.replaceBlockButton.blockInfo = b


class BrushToolOptions(ToolOptions):
    def __init__(self, tool):
        Panel.__init__(self)
        alphaField = FloatField(ref=AttrRef(tool, 'brushAlpha'), min=0.0, max=1.0, width=60)
        alphaField.increment = 0.1
        alphaRow = Row((Label("Alpha: "), alphaField))
        autoChooseCheckBox = CheckBoxLabel("Choose Block Immediately",
                                            ref=AttrRef(tool, "chooseBlockImmediately"),
                                            tooltipText="When the brush tool is chosen, prompt for a block type.")

        updateOffsetCheckBox = CheckBoxLabel("Reset Distance When Brush Size Changes",
                                            ref=AttrRef(tool, "updateBrushOffset"),
                                            tooltipText="Whenever the brush size changes, reset the distance to the brush blocks.")

        col = Column((Label("Brush Options"), alphaRow, autoChooseCheckBox, updateOffsetCheckBox, Button("OK", action=self.dismiss)))
        self.add(col)
        self.shrink_wrap()
        return

from clone import CloneTool


class BrushTool(CloneTool):
    tooltipText = "Brush\nRight-click for options"
    toolIconName = "brush"
    minimumSpacing = 1

    def __init__(self, *args):
        CloneTool.__init__(self, *args)
        self.optionsPanel = BrushToolOptions(self)
        self.recentFillBlocks = []
        self.recentReplaceBlocks = []
        self.draggedPositions = []

        self.brushModes = [c() for c in BrushOperation.brushModeClasses]
        for m in self.brushModes:
            self.options.extend(m.options)

        self._brushMode = self.brushModes[0]
        BrushSettings.updateBrushOffset.addObserver(self)
        BrushSettings.brushSizeW.addObserver(self, 'brushSizeW', callback=self._setBrushSize)
        BrushSettings.brushSizeH.addObserver(self, 'brushSizeH', callback=self._setBrushSize)
        BrushSettings.brushSizeL.addObserver(self, 'brushSizeL', callback=self._setBrushSize)

    panel = None

    def _setBrushSize(self, _):
        if self.updateBrushOffset:
            self.reticleOffset = self.offsetMax()
            self.resetToolDistance()
        self.previewDirty = True

    previewDirty = False
    updateBrushOffset = True

    _reticleOffset = 1
    naturalEarth = True
    erosionStrength = 1
    indiscriminate = False

    @property
    def reticleOffset(self):
        if self.brushMode.name == "Flood Fill":
            return 0
        return self._reticleOffset

    @reticleOffset.setter
    def reticleOffset(self, val):
        self._reticleOffset = val

    brushSizeW, brushSizeH, brushSizeL = 1, 1, 1

    @property
    def brushSize(self):
        if self.brushMode.name == "Flood Fill":
            return 1, 1, 1
        return [self.brushSizeW, self.brushSizeH, self.brushSizeL]

    @brushSize.setter
    def brushSize(self, val):
        (w, h, l) = [max(1, min(i, self.maxBrushSize)) for i in val]
        BrushSettings.brushSizeH.set(h)
        BrushSettings.brushSizeL.set(l)
        BrushSettings.brushSizeW.set(w)

    maxBrushSize = 4096

    brushStyles = BrushOperation.brushStyles
    brushStyle = brushStyles[0]
    brushModes = None

    @property
    def brushMode(self):
        return self._brushMode

    @brushMode.setter
    def brushMode(self, val):
        if isinstance(val, str):
            val = [b for b in self.brushModes if b.name == val][0]

        self._brushMode = val

        self.hidePanel()
        self.showPanel()

    brushNoise = 100
    brushHollow = False
    topsoilDepth = 1

    chooseBlockImmediately = BrushSettings.chooseBlockImmediately.configProperty()

    _blockInfo = pymclevel.alphaMaterials.Stone

    @property
    def blockInfo(self):
        return self._blockInfo

    @blockInfo.setter
    def blockInfo(self, bi):
        self._blockInfo = bi
        self.setupPreview()

    _replaceBlockInfo = pymclevel.alphaMaterials.Stone

    @property
    def replaceBlockInfo(self):
        return self._replaceBlockInfo

    @replaceBlockInfo.setter
    def replaceBlockInfo(self, bi):
        self._replaceBlockInfo = bi
        self.setupPreview()

    @property
    def brushAlpha(self):
        return BrushSettings.alpha.get()

    @brushAlpha.setter
    def brushAlpha(self, f):
        f = min(1.0, max(0.0, f))
        BrushSettings.alpha.set(f)
        self.setupPreview()

    def importPaste(self):
        clipFilename = mcplatform.askOpenFile(title='Choose a schematic or level...', schematics=True)
        # xxx mouthful
        if clipFilename:
            try:
                self.loadLevel(pymclevel.fromFile(clipFilename, readonly=True))
            except Exception, e:
                alert("Failed to load file %s" % clipFilename)
                self.brushMode = "Fill"
                return

    def loadLevel(self, level):
        self.level = level
        self.minimumSpacing = min([s / 4 for s in level.size])
        self.centerx, self.centery, self.centerz = -level.Width / 2, 0, -level.Length / 2
        CloneTool.setupPreview(self)

    @property
    def importFilename(self):
        if self.level:
            return basename(self.level.filename or "No name")
        return "Nothing selected"

    @property
    def statusText(self):
        return "Click and drag to place blocks. ALT-Click to use the block under the cursor. {R} to increase and {F} to decrease size. {E} to rotate, {G} to roll. Mousewheel to adjust distance.".format(
            R=config.config.get("Keys", "Roll").upper(),
            F=config.config.get("Keys", "Flip").upper(),
            E=config.config.get("Keys", "Rotate").upper(),
            G=config.config.get("Keys", "Mirror").upper(),
            )

    @property
    def worldTooltipText(self):
        if pygame.key.get_mods() & pygame.KMOD_ALT:
            try:
                if self.editor.blockFaceUnderCursor is None:
                    return
                pos = self.editor.blockFaceUnderCursor[0]
                blockID = self.editor.level.blockAt(*pos)
                blockdata = self.editor.level.blockDataAt(*pos)
                return "Click to use {0} ({1}:{2})".format(self.editor.level.materials.names[blockID][blockdata], blockID, blockdata)

            except Exception, e:
                return repr(e)

        if self.brushMode.name == "Flood Fill":
            try:
                if self.editor.blockFaceUnderCursor is None:
                    return
                pos = self.editor.blockFaceUnderCursor[0]
                blockID = self.editor.level.blockAt(*pos)
                blockdata = self.editor.level.blockDataAt(*pos)
                return "Click to replace {0} ({1}:{2})".format(self.editor.level.materials.names[blockID][blockdata], blockID, blockdata)

            except Exception, e:
                return repr(e)

    def swapBrushStyles(self):
        brushStyleIndex = self.brushStyles.index(self.brushStyle) + 1
        brushStyleIndex %= len(self.brushStyles)
        self.brushStyle = self.brushStyles[brushStyleIndex]
        self.setupPreview()

    def swapBrushModes(self):
        brushModeIndex = self.brushModes.index(self.brushMode) + 1
        brushModeIndex %= len(self.brushModes)
        self.brushMode = self.brushModes[brushModeIndex]

    options = [
        'blockInfo',
        'brushStyle',
        'brushMode',
        'brushSize',
        'brushNoise',
        'brushHollow',
        'replaceBlockInfo',
    ]

    def getBrushOptions(self):
        return dict(((key, getattr(self, key))
                       for key
                       in self.options))

    draggedDirection = (0, 0, 0)
    centerx = centery = centerz = 0

    @alertException
    def mouseDown(self, evt, pos, direction):
        if pygame.key.get_mods() & pygame.KMOD_ALT:
            id = self.editor.level.blockAt(*pos)
            data = self.editor.level.blockDataAt(*pos)
            if self.brushMode.name == "Replace":
                self.panel.replaceBlockButton.blockInfo = self.editor.level.materials.blockWithID(id, data)
            else:
                self.panel.blockButton.blockInfo = self.editor.level.materials.blockWithID(id, data)

            return

        self.draggedDirection = direction
        point = [p + d * self.reticleOffset for p, d in zip(pos, direction)]
        self.dragLineToPoint(point)

    @alertException
    def mouseDrag(self, evt, pos, _dir):
        direction = self.draggedDirection
        if self.brushMode.name != "Flood Fill":
            if len(self.draggedPositions):  # if self.isDragging
                self.lastPosition = lastPoint = self.draggedPositions[-1]
                point = [p + d * self.reticleOffset for p, d in zip(pos, direction)]
                if any([abs(a - b) >= self.minimumSpacing
                        for a, b in zip(point, lastPoint)]):
                    self.dragLineToPoint(point)

    def dragLineToPoint(self, point):
        if self.brushMode.name == "Flood Fill":
            self.draggedPositions = [point]
            return

        if pygame.key.get_mods() & pygame.KMOD_SHIFT:
            if len(self.draggedPositions):
                points = bresenham.bresenham(self.draggedPositions[-1], point)
                self.draggedPositions.extend(points[::self.minimumSpacing][1:])
            elif self.lastPosition is not None:
                points = bresenham.bresenham(self.lastPosition, point)
                self.draggedPositions.extend(points[::self.minimumSpacing][1:])
        else:
            self.draggedPositions.append(point)

    @alertException
    def mouseUp(self, evt, pos, direction):
        if 0 == len(self.draggedPositions):
            return

        size = self.brushSize
        # point = self.getReticlePoint(pos, direction)
        if self.brushMode.name == "Flood Fill":
            self.draggedPositions = self.draggedPositions[-1:]

        op = BrushOperation(self.editor,
                            self.editor.level,
                            self.draggedPositions,
                            self.getBrushOptions())

        box = op.dirtyBox()
        self.editor.addOperation(op)
        self.editor.addUnsavedEdit()

        self.editor.invalidateBox(box)
        self.lastPosition = self.draggedPositions[-1]

        self.draggedPositions = []

    def toolEnabled(self):
        return True

    def rotate(self):
        offs = self.reticleOffset
        dist = self.editor.cameraToolDistance
        W, H, L = self.brushSize
        self.brushSize = L, H, W
        self.reticleOffset = offs
        self.editor.cameraToolDistance = dist

    def mirror(self):
        offs = self.reticleOffset
        dist = self.editor.cameraToolDistance
        W, H, L = self.brushSize
        self.brushSize = W, L, H
        self.reticleOffset = offs
        self.editor.cameraToolDistance = dist

    def toolReselected(self):
        if self.brushMode.name == "Replace":
            self.panel.pickReplaceBlock()
        else:
            self.panel.pickFillBlock()

    def flip(self):
        self.decreaseBrushSize()

    def roll(self):
        self.increaseBrushSize()

    def swap(self):
        self.panel.swap()

    def decreaseBrushSize(self):
        self.brushSize = [i - 1 for i in self.brushSize]
        # self.setupPreview()

    def increaseBrushSize(self):
        self.brushSize = [i + 1 for i in self.brushSize]

    @alertException
    def setupPreview(self):
        self.previewDirty = False
        brushSize = self.brushSize
        brushStyle = self.brushStyle
        if self.brushMode.name == "Replace":
            blockInfo = self.replaceBlockInfo
        else:
            blockInfo = self.blockInfo

        class FakeLevel(pymclevel.MCLevel):
            filename = "Fake Level"
            materials = self.editor.level.materials

            def __init__(self):
                self.chunkCache = {}

            Width, Height, Length = brushSize

            zerolight = numpy.zeros((16, 16, Height), dtype='uint8')
            zerolight[:] = 15

            def getChunk(self, cx, cz):
                if (cx, cz) in self.chunkCache:
                    return self.chunkCache[cx, cz]

                class FakeBrushChunk(pymclevel.level.FakeChunk):
                    Entities = []
                    TileEntities = []

                f = FakeBrushChunk()
                f.world = self
                f.chunkPosition = (cx, cz)

                mask = createBrushMask(brushSize, brushStyle, (0, 0, 0), BoundingBox((cx << 4, 0, cz << 4), (16, self.Height, 16)))
                f.Blocks = numpy.zeros(mask.shape, dtype='uint8')
                f.Data = numpy.zeros(mask.shape, dtype='uint8')
                f.BlockLight = self.zerolight
                f.SkyLight = self.zerolight

                if blockInfo.ID:
                    f.Blocks[mask] = blockInfo.ID
                    f.Data[mask] = blockInfo.blockData

                else:
                    f.Blocks[mask] = 255
                self.chunkCache[cx, cz] = f
                return f

        self.level = FakeLevel()

        CloneTool.setupPreview(self, alpha=self.brushAlpha)

    def resetToolDistance(self):
        distance = max(self.editor.cameraToolDistance, 6 + max(self.brushSize) * 1.25)
        # print "Adjusted distance", distance, max(self.brushSize) * 1.25
        self.editor.cameraToolDistance = distance

    def toolSelected(self):

        if self.chooseBlockImmediately:
            blockPicker = BlockPicker(
                self.blockInfo,
                self.editor.level.materials,
                allowWildcards=self.brushMode.name == "Replace")

            if blockPicker.present():
                self.blockInfo = blockPicker.blockInfo

        if self.updateBrushOffset:
            self.reticleOffset = self.offsetMax()
        self.resetToolDistance()
        self.setupPreview()
        self.showPanel()

#    def cancel(self):
#        self.hidePanel()
#        super(BrushTool, self).cancel()

    def showPanel(self):
        if self.panel:
            self.panel.parent.remove(self.panel)

        panel = BrushPanel(self)
        panel.centery = self.editor.centery
        panel.left = self.editor.left
        panel.anchor = "lwh"

        self.panel = panel
        self.editor.add(panel)

    def increaseToolReach(self):
        # self.reticleOffset = max(self.reticleOffset-1, 0)
        if self.editor.mainViewport.mouseMovesCamera and not self.editor.longDistanceMode:
            return False
        self.reticleOffset = self.reticleOffset + 1
        return True

    def decreaseToolReach(self):
        if self.editor.mainViewport.mouseMovesCamera and not self.editor.longDistanceMode:
            return False
        self.reticleOffset = max(self.reticleOffset - 1, 0)
        return True

    def resetToolReach(self):
        if self.editor.mainViewport.mouseMovesCamera and not self.editor.longDistanceMode:
            self.resetToolDistance()
        else:
            self.reticleOffset = self.offsetMax()
        return True

    cameraDistance = EditorTool.cameraDistance

    def offsetMax(self):
        return max(1, ((0.5 * max(self.brushSize)) + 1))

    def getReticleOffset(self):
        return self.reticleOffset

    def getReticlePoint(self, pos, direction):
        if len(self.draggedPositions):
            direction = self.draggedDirection
        return map(lambda a, b: a + (b * self.getReticleOffset()), pos, direction)

    def drawToolReticle(self):
        for pos in self.draggedPositions:
            drawTerrainCuttingWire(BoundingBox(pos, (1, 1, 1)),
                                   (0.75, 0.75, 0.1, 0.4),
                                   (1.0, 1.0, 0.5, 1.0))

    lastPosition = None

    def drawTerrainReticle(self):
        if pygame.key.get_mods() & pygame.KMOD_ALT:
            # eyedropper mode
            self.editor.drawWireCubeReticle(color=(0.2, 0.6, 0.9, 1.0))
        else:
            pos, direction = self.editor.blockFaceUnderCursor
            reticlePoint = self.getReticlePoint(pos, direction)

            self.editor.drawWireCubeReticle(position=reticlePoint)
            if reticlePoint != pos:
                GL.glColor4f(1.0, 1.0, 0.0, 0.7)
                with gl.glBegin(GL.GL_LINES):
                    GL.glVertex3f(*map(lambda a: a + 0.5, reticlePoint))  # center of reticle block
                    GL.glVertex3f(*map(lambda a, b: a + 0.5 + b * 0.5, pos, direction))  # top side of surface block

            if self.previewDirty:
                self.setupPreview()

            dirtyBox = self.brushMode.brushBoxForPointAndOptions(reticlePoint, self.getBrushOptions())
            self.drawTerrainPreview(dirtyBox.origin)
            if pygame.key.get_mods() & pygame.KMOD_SHIFT and self.lastPosition and self.brushMode.name != "Flood Fill":
                GL.glColor4f(1.0, 1.0, 1.0, 0.7)
                with gl.glBegin(GL.GL_LINES):
                    GL.glVertex3f(*map(lambda a: a + 0.5, self.lastPosition))
                    GL.glVertex3f(*map(lambda a: a + 0.5, reticlePoint))

    def updateOffsets(self):
        pass

    def selectionChanged(self):
        pass

    def option1(self):
        self.swapBrushStyles()

    def option2(self):
        self.swapBrushModes()

    def option3(self):
        self.brushHollow = not self.brushHollow

def createBrushMask(shape, style="Round", offset=(0, 0, 0), box=None, chance=100, hollow=False):
    """
    Return a boolean array for a brush with the given shape and style.
    If 'offset' and 'box' are given, then the brush is offset into the world
    and only the part of the world contained in box is returned as an array
    """

    # we are returning indices for a Blocks array, so swap axes
    if box is None:
        box = BoundingBox(offset, shape)
    if chance < 100 or hollow:
        box = box.expand(1)

    outputShape = box.size
    outputShape = (outputShape[0], outputShape[2], outputShape[1])

    shape = shape[0], shape[2], shape[1]
    offset = numpy.array(offset) - numpy.array(box.origin)
    offset = offset[[0, 2, 1]]

    inds = numpy.indices(outputShape, dtype=float)
    halfshape = numpy.array([(i >> 1) - ((i & 1 == 0) and 0.5 or 0) for i in shape])

    blockCenters = inds - halfshape[:, newaxis, newaxis, newaxis]
    blockCenters -= offset[:, newaxis, newaxis, newaxis]

    # odd diameter means measure from the center of the block at 0,0,0 to each block center
    # even diameter means measure from the 0,0,0 grid point to each block center

    # if diameter & 1 == 0: blockCenters += 0.5
    shape = numpy.array(shape, dtype='float32')

    # if not isSphere(shape):
    if style == "Round":
        blockCenters *= blockCenters
        shape /= 2
        shape *= shape

        blockCenters /= shape[:, newaxis, newaxis, newaxis]
        distances = sum(blockCenters, 0)
        mask = distances < 1
    elif style == "Square":
        # mask = ones(outputShape, dtype=bool)
        # mask = blockCenters[:, newaxis, newaxis, newaxis] < shape
        blockCenters /= shape[:, newaxis, newaxis, newaxis]

        distances = numpy.absolute(blockCenters).max(0)
        mask = distances < .5

    elif style == "Diamond":
        blockCenters = numpy.abs(blockCenters)
        shape /= 2
        blockCenters /= shape[:, newaxis, newaxis, newaxis]
        distances = sum(blockCenters, 0)
        mask = distances < 1
    else:
        raise ValueError, "Unknown style: " + style

    if (chance < 100 or hollow) and max(shape) > 1:
        threshold = chance / 100.0
        exposedBlockMask = numpy.ones(shape=outputShape, dtype='bool')
        exposedBlockMask[:] = mask
        submask = mask[1:-1, 1:-1, 1:-1]
        exposedBlockSubMask = exposedBlockMask[1:-1, 1:-1, 1:-1]
        exposedBlockSubMask[:] = False

        for dim in (0, 1, 2):
            slices = [slice(1, -1), slice(1, -1), slice(1, -1)]
            slices[dim] = slice(None, -2)
            exposedBlockSubMask |= (submask & (mask[slices] != submask))
            slices[dim] = slice(2, None)
            exposedBlockSubMask |= (submask & (mask[slices] != submask))

        if hollow:
            mask[~exposedBlockMask] = False
        if chance < 100:
            rmask = numpy.random.random(mask.shape) < threshold

            mask[exposedBlockMask] = rmask[exposedBlockMask]

    if chance < 100 or hollow:
        return mask[1:-1, 1:-1, 1:-1]
    else:
        return mask
