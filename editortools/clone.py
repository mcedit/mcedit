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
import os
import traceback
from OpenGL import GL
import numpy
import pygame
from albow import Widget, IntField, Column, Row, Label, Button, CheckBox, AttrRef, FloatField, alert
from depths import DepthOffset
from editortools.editortool import EditorTool
from editortools.nudgebutton import NudgeButton
from editortools.tooloptions import ToolOptions
from glbackground import Panel
from glutils import gl
from mceutils import setWindowCaption, showProgress, alertException, drawFace
import mcplatform
from operation import Operation
import pymclevel
from pymclevel.box import Vector
from renderer import PreviewRenderer

from select import SelectionOperation
from pymclevel.pocket import PocketWorld
from pymclevel import block_copy, BoundingBox

import logging
log = logging.getLogger(__name__)

import config


CloneSettings = config.Settings("Clone")
CloneSettings.copyAir = CloneSettings("Copy Air", True)
CloneSettings.copyWater = CloneSettings("Copy Water", True)
CloneSettings.copyBiomes = CloneSettings("Copy Biomes", True)
CloneSettings.placeImmediately = CloneSettings("Place Immediately", True)


class CoordsInput(Widget):
    is_gl_container = True

    def __init__(self):
        Widget.__init__(self)

        self.nudgeButton = NudgeButton()
        self.nudgeButton.nudge = self._nudge

        self.xField = IntField(value=0)
        self.yField = IntField(value=0)
        self.zField = IntField(value=0)

        for field in (self.xField, self.yField, self.zField):
            field.change_action = self._coordsChanged
            field.enter_passes = False

        offsetCol = Column((self.xField, self.yField, self.zField))

        nudgeOffsetRow = Row((offsetCol, self.nudgeButton))

        self.add(nudgeOffsetRow)
        self.shrink_wrap()

    def getCoords(self):
        return self.xField.value, self.yField.value, self.zField.value

    def setCoords(self, coords):
        x, y, z = coords
        self.xField.text = str(x)
        self.yField.text = str(y)
        self.zField.text = str(z)

    coords = property(getCoords, setCoords, None)

    def _coordsChanged(self):
        self.coordsChanged()

    def coordsChanged(self):
        # called when the inputs change.  override or replace
        pass

    def _nudge(self, nudge):
        self.nudge(nudge)

    def nudge(self, nudge):
        # nudge is a 3-tuple where one of the elements is -1 or 1, and the others are 0.
        pass


class BlockCopyOperation(Operation):
    def __init__(self, editor, sourceLevel, sourceBox, destLevel, destPoint, copyAir, copyWater, copyBiomes):
        super(BlockCopyOperation, self).__init__(editor, destLevel)
        self.sourceLevel = sourceLevel
        self.sourceBox = sourceBox
        self.destPoint = Vector(*destPoint)
        self.copyAir = copyAir
        self.copyWater = copyWater
        self.copyBiomes = copyBiomes
        self.sourceBox, self.destPoint = block_copy.adjustCopyParameters(self.level, self.sourceLevel, self.sourceBox,
                                                                         self.destPoint)

    def dirtyBox(self):
        return BoundingBox(self.destPoint, self.sourceBox.size)

    def name(self):
        return "Copy {0} blocks".format(self.sourceBox.volume)

    def perform(self, recordUndo=True):
        sourceBox = self.sourceBox

        if recordUndo:
            self.undoLevel = self.extractUndo(self.level, BoundingBox(self.destPoint, self.sourceBox.size))


        blocksToCopy = None
        if not (self.copyAir and self.copyWater):
            blocksToCopy = range(pymclevel.materials.id_limit)
            if not self.copyAir:
                blocksToCopy.remove(0)
            if not self.copyWater:
                blocksToCopy.remove(8)
            if not self.copyWater:
                blocksToCopy.remove(9)

        with setWindowCaption("Copying - "):
            i = self.level.copyBlocksFromIter(self.sourceLevel, self.sourceBox, self.destPoint, blocksToCopy, create=True, biomes=self.copyBiomes)
            showProgress("Copying {0:n} blocks...".format(self.sourceBox.volume), i)

    def bufferSize(self):
        return 123456


class CloneOperation(Operation):
    def __init__(self, editor, sourceLevel, sourceBox, originSourceBox, destLevel, destPoint, copyAir, copyWater, copyBiomes, repeatCount):
        super(CloneOperation, self).__init__(editor, destLevel)

        self.blockCopyOps = []
        dirtyBoxes = []
        if repeatCount > 1:  # clone tool only
            delta = destPoint - editor.toolbar.tools[0].selectionBox().origin
        else:
            delta = (0, 0, 0)

        for i in range(repeatCount):
            op = BlockCopyOperation(editor, sourceLevel, sourceBox, destLevel, destPoint, copyAir, copyWater, copyBiomes)
            dirty = op.dirtyBox()

            # bounds check - xxx move to BoundingBox
            if dirty.miny >= destLevel.Height or dirty.maxy < 0:
                continue
            if destLevel.Width != 0:
                if dirty.minx >= destLevel.Width or dirty.maxx < 0:
                    continue
                if dirty.minz >= destLevel.Length or dirty.maxz < 0:
                    continue

            dirtyBoxes.append(dirty)
            self.blockCopyOps.append(op)

            destPoint += delta

        if len(dirtyBoxes):
            def enclosingBox(dirtyBoxes):
                return reduce(lambda a, b: a.union(b), dirtyBoxes)

            self._dirtyBox = enclosingBox(dirtyBoxes)

            if repeatCount > 1 and self.selectOriginalAfterRepeat:
                dirtyBoxes.append(originSourceBox)

            dirty = enclosingBox(dirtyBoxes)
            points = (dirty.origin, dirty.maximum - (1, 1, 1))

            self.selectionOps = [SelectionOperation(editor.selectionTool, points)]

        else:
            self._dirtyBox = None
            self.selectionOps = []

    selectOriginalAfterRepeat = True

    def dirtyBox(self):
        return self._dirtyBox

    def perform(self, recordUndo=True):
        with setWindowCaption("COPYING - "):
            self.editor.freezeStatus("Copying %0.1f million blocks" % (float(self._dirtyBox.volume) / 1048576.,))
            if recordUndo:
                chunks = set()
                for op in self.blockCopyOps:
                    chunks.update(op.dirtyBox().chunkPositions)
                self.undoLevel = self.extractUndoChunks(self.level, chunks)

            [i.perform(False) for i in self.blockCopyOps]
            [i.perform(recordUndo) for i in self.selectionOps]

    def undo(self):
        super(CloneOperation, self).undo()
        [i.undo() for i in self.selectionOps]


class CloneToolPanel(Panel):
    useOffsetInput = True

    def transformEnable(self):
        return not isinstance(self.tool.level, pymclevel.MCInfdevOldLevel)

    def __init__(self, tool):
        Panel.__init__(self)
        self.tool = tool

        rotateRow = Row((
            Label(config.config.get("Keys", "Rotate").upper()), Button("Rotate", width=80, action=tool.rotate, enable=self.transformEnable),
        ))

        rollRow = Row((
            Label(config.config.get("Keys", "Roll").upper()), Button("Roll", width=80, action=tool.roll, enable=self.transformEnable),
        ))

        flipRow = Row((
            Label(config.config.get("Keys", "Flip").upper()), Button("Flip", width=80, action=tool.flip, enable=self.transformEnable),
        ))

        mirrorRow = Row((
            Label(config.config.get("Keys", "Mirror").upper()), Button("Mirror", width=80, action=tool.mirror, enable=self.transformEnable),
        ))

        alignRow = Row((
            CheckBox(ref=AttrRef(self.tool, 'chunkAlign')), Label("Chunk Align")
        ))

        # headerLabel = Label("Clone Offset")
        if self.useOffsetInput:
            self.offsetInput = CoordsInput()
            self.offsetInput.coordsChanged = tool.offsetChanged
            self.offsetInput.nudgeButton.bg_color = tool.color
            self.offsetInput.nudge = tool.nudge
        else:
            self.nudgeButton = NudgeButton()
            self.nudgeButton.bg_color = tool.color
            self.nudgeButton.nudge = tool.nudge

        repeatField = IntField(ref=AttrRef(tool, 'repeatCount'))
        repeatField.min = 1
        repeatField.max = 50

        repeatRow = Row((
            Label("Repeat"), repeatField
        ))
        self.repeatField = repeatField

        scaleField = FloatField(ref=AttrRef(tool, 'scaleFactor'))
        scaleField.min = 0.125
        scaleField.max = 8
        dv = scaleField.decrease_value
        iv = scaleField.increase_value

        def scaleFieldDecrease():
            if scaleField.value > 1 / 8.0 and scaleField.value <= 1.0:
                scaleField.value *= 0.5
            else:
                dv()

        def scaleFieldIncrease():
            if scaleField.value < 1.0:
                scaleField.value *= 2.0
            else:
                iv()

        scaleField.decrease_value = scaleFieldDecrease
        scaleField.increase_value = scaleFieldIncrease

        scaleRow = Row((
            Label("Scale Factor"), scaleField
        ))

        self.scaleField = scaleField

        self.copyAirCheckBox = CheckBox(ref=AttrRef(self.tool, "copyAir"))
        self.copyAirLabel = Label("Copy Air")
        self.copyAirLabel.mouse_down = self.copyAirCheckBox.mouse_down
        self.copyAirLabel.tooltipText = "Shortcut: ALT-1"
        self.copyAirCheckBox.tooltipText = self.copyAirLabel.tooltipText

        copyAirRow = Row((self.copyAirCheckBox, self.copyAirLabel))

        self.copyWaterCheckBox = CheckBox(ref=AttrRef(self.tool, "copyWater"))
        self.copyWaterLabel = Label("Copy Water")
        self.copyWaterLabel.mouse_down = self.copyWaterCheckBox.mouse_down
        self.copyWaterLabel.tooltipText = "Shortcut: ALT-2"
        self.copyWaterCheckBox.tooltipText = self.copyWaterLabel.tooltipText

        copyWaterRow = Row((self.copyWaterCheckBox, self.copyWaterLabel))

        self.copyBiomesCheckBox = CheckBox(ref=AttrRef(self.tool, "copyBiomes"))
        self.copyBiomesLabel = Label("Copy Biomes")
        self.copyBiomesLabel.mouse_down = self.copyBiomesCheckBox.mouse_down
        self.copyBiomesLabel.tooltipText = "Shortcut: ALT-3"
        self.copyBiomesCheckBox.tooltipText = self.copyBiomesLabel.tooltipText

        copyBiomesRow = Row((self.copyBiomesCheckBox, self.copyBiomesLabel))

        self.performButton = Button("Clone", width=100, align="c")
        self.performButton.tooltipText = "Shortcut: ENTER"
        self.performButton.action = tool.confirm
        self.performButton.enable = lambda: (tool.destPoint is not None)
        if self.useOffsetInput:
            col = Column((rotateRow, rollRow, flipRow, mirrorRow, alignRow, self.offsetInput, repeatRow, scaleRow, copyAirRow, copyWaterRow, copyBiomesRow, self.performButton))
        else:
            col = Column((rotateRow, rollRow, flipRow, mirrorRow, alignRow, self.nudgeButton, copyAirRow, copyWaterRow, copyBiomesRow, self.performButton))

        self.add(col)
        self.anchor = "lwh"

        self.shrink_wrap()


class CloneToolOptions(ToolOptions):
    def __init__(self, tool):
        Panel.__init__(self)
        self.tool = tool
        self.autoPlaceCheckBox = CheckBox(ref=AttrRef(tool, "placeImmediately"))
        self.autoPlaceLabel = Label("Place Immediately")
        self.autoPlaceLabel.mouse_down = self.autoPlaceCheckBox.mouse_down

        tooltipText = "When the clone tool is chosen, place the clone at the selection right away."
        self.autoPlaceLabel.tooltipText = self.autoPlaceCheckBox.tooltipText = tooltipText

        row = Row((self.autoPlaceCheckBox, self.autoPlaceLabel))
        col = Column((Label("Clone Options"), row, Button("OK", action=self.dismiss)))

        self.add(col)
        self.shrink_wrap()


class CloneTool(EditorTool):
    surfaceBuild = True
    toolIconName = "clone"
    tooltipText = "Clone\nRight-click for options"
    level = None
    repeatCount = 1
    _scaleFactor = 1.0
    _chunkAlign = False

    @property
    def scaleFactor(self):
        return self._scaleFactor

    @scaleFactor.setter
    def scaleFactor(self, val):
        self.rescaleLevel(val)
        self._scaleFactor = val

    @property
    def chunkAlign(self):
        return self._chunkAlign

    @chunkAlign.setter
    def chunkAlign(self, value):
        self._chunkAlign = value
        self.alignDestPoint()

    def alignDestPoint(self):
        if self.destPoint is not None:
            x, y, z = self.destPoint
            self.destPoint = Vector((x >> 4) << 4, y, (z >> 4) << 4)

    placeImmediately = CloneSettings.placeImmediately.configProperty()

    panelClass = CloneToolPanel
    # color = (0.89, 0.65, 0.35, 0.33)
    color = (0.3, 1.0, 0.3, 0.19)

    def __init__(self, *args):
        self.rotation = 0

        EditorTool.__init__(self, *args)
        self.previewRenderer = None
        self.panel = None

        self.optionsPanel = CloneToolOptions(self)

        self.destPoint = None

    @property
    def statusText(self):
        if self.destPoint == None:
            return "Click to set this item down."
        if self.draggingFace is not None:
            return "Mousewheel to move along the third axis. Hold SHIFT to only move along one axis."

        return "Click and drag to reposition the item. Double-click to pick it up. Click Clone or press ENTER to confirm."

    def quickNudge(self, nudge):
        return map(int.__mul__, nudge, self.selectionBox().size)

    copyAir = CloneSettings.copyAir.configProperty()
    copyWater = CloneSettings.copyWater.configProperty()
    copyBiomes = CloneSettings.copyBiomes.configProperty()

    def nudge(self, nudge):
        if self.destPoint is None:
            if self.selectionBox() is None:
                return
            self.destPoint = self.selectionBox().origin

        if self.chunkAlign:
            x, y, z = nudge
            nudge = x << 4, y, z << 4

        if pygame.key.get_mods() & pygame.KMOD_SHIFT:
            nudge = self.quickNudge(nudge)

        # self.panel.performButton.enabled = True
        self.destPoint = self.destPoint + nudge
        self.updateOffsets()

    def selectionChanged(self):
        if self.selectionBox() is not None:
            self.updateSchematic()
            self.updateOffsets()

    def updateOffsets(self):
        if self.panel and self.panel.useOffsetInput and self.destPoint is not None:
            self.panel.offsetInput.setCoords(self.destPoint - self.selectionBox().origin)

    def offsetChanged(self):

        if self.panel:
            if not self.panel.useOffsetInput:
                return
            box = self.selectionBox()
            if box is None:
                return

            delta = self.panel.offsetInput.coords
            self.destPoint = box.origin + delta

    def toolEnabled(self):
        return not (self.selectionBox() is None)

    def cancel(self):

        self.discardPreviewer()
        if self.panel:
            self.panel.parent.remove(self.panel)
            self.panel = None

        self.destPoint = None
        self.level = None
        self.originalLevel = None

    def toolReselected(self):
        self.pickUp()

    def safeToolDistance(self):
        return numpy.sqrt(sum([self.level.Width ** 2, self.level.Height ** 2, self.level.Length ** 2]))

    def toolSelected(self):
        box = self.selectionBox()
        if box is None:
            self.editor.toolbar.selectTool(-1)
            return

        if box.volume > self.maxBlocks:
            self.editor.mouseLookOff()
            alert("Selection exceeds {0:n} blocks. Increase the block buffer setting and try again.".format(self.maxBlocks))
            self.editor.toolbar.selectTool(-1)
            return

        self.rotation = 0
        self.repeatCount = 1
        self._scaleFactor = 1.0

        if self.placeImmediately:
            self.destPoint = box.origin
        else:
            self.destPoint = None

        self.updateSchematic()
        self.cloneCameraDistance = max(self.cloneCameraDistance, self.safeToolDistance())
        self.showPanel()

    cloneCameraDistance = 0

    @property
    def cameraDistance(self):
        return self.cloneCameraDistance

    @alertException
    def rescaleLevel(self, factor):
        # if self.level.cloneToolScaleFactor == newFactor:
        #    return
        # oldfactor = self.level.cloneToolScaleFactor
        # factor = newFactor / oldfactor
        if factor == 1:
            self.level = self.originalLevel
            self.setupPreview()
            return

        oldshape = self.originalLevel.Blocks.shape
        blocks = self.originalLevel.Blocks
        data = self.originalLevel.Data

        if factor < 1.0:
            roundedShape = map(lambda x: int(int(x * factor) / factor), oldshape)
            roundedSlices = map(lambda x: slice(0, x), roundedShape)
            blocks = blocks[roundedSlices]
            data = data[roundedSlices]
        else:
            roundedShape = oldshape

        newshape = map(lambda x: int(x * factor), oldshape)
        xyzshape = newshape[0], newshape[2], newshape[1]
        newlevel = pymclevel.MCSchematic(xyzshape, mats=self.editor.level.materials)

        srcgrid = numpy.mgrid[0:roundedShape[0]:1.0 / factor, 0:roundedShape[1]:1.0 / factor, 0:roundedShape[2]:1.0 / factor].astype('uint')
        dstgrid = numpy.mgrid[0:newshape[0], 0:newshape[1], 0:newshape[2]].astype('uint')
        srcgrid = srcgrid[map(slice, dstgrid.shape)]
        dstgrid = dstgrid[map(slice, srcgrid.shape)]

        def copyArray(dest, src):
            dest[dstgrid[0], dstgrid[1], dstgrid[2]] = src[srcgrid[0], srcgrid[1], srcgrid[2]]

        copyArray(newlevel.Blocks, blocks)
        copyArray(newlevel.Data, data)

        self.level = newlevel
        self.setupPreview()
#
#        """
#        use array broadcasting to fill in the extra dimensions with copies of the
#        existing ones, then later change the shape to "fold" the extras back
#        into the original three
#        """
#        # if factor > 1.0:
#        sourceSlice = slice(0, 1)
#        destSlice = slice(None)
#
#        # if factor < 1.0:
#
#        destfactor = factor
#        srcfactor = 1
#        if factor < 1.0:
#            destfactor = 1.0
#            srcfactor = 1.0 / factor
#
#        intershape = newshape[0]/destfactor, destfactor, newshape[1]/destfactor, destfactor, newshape[2]/destfactor, destfactor
#        srcshape = roundedShape[0]/srcfactor, srcfactor, roundedShape[1]/srcfactor, srcfactor, roundedShape[2]/srcfactor, srcfactor
#
#        newlevel = MCSchematic(xyzshape)
#
#        def copyArray(dest, src):
#            dest.shape = intershape
#            src.shape = srcshape
#
#            dest[:, destSlice, :, destSlice, :, destSlice] = src[:, sourceSlice, :, sourceSlice, :, sourceSlice]
#            dest.shape = newshape
#            src.shape = roundedShape
#
#        copyArray(newlevel.Blocks, blocks)
#        copyArray(newlevel.Data, data)
#
#        newlevel.cloneToolScaleFactor = newFactor
#

    @alertException
    def updateSchematic(self):
        # extract blocks
        with setWindowCaption("COPYING - "):
            self.editor.freezeStatus("Copying to clone buffer...")
            box = self.selectionBox()
            self.level = self.editor.level.extractSchematic(box)
            self.originalLevel = self.level
            # self.level.cloneToolScaleFactor = 1.0
            self.rescaleLevel(self.scaleFactor)
            self.setupPreview()

    def showPanel(self):
        if self.panel:
            self.panel.set_parent(None)

        self.panel = self.panelClass(self)
        # self.panel.performButton.enabled = False

        self.panel.centery = self.editor.centery
        self.panel.left = self.editor.left
        self.editor.add(self.panel)

    def setupPreview(self, alpha=1.0):
        self.discardPreviewer()
        if self.level:
            self.previewRenderer = PreviewRenderer(self.level, alpha)
            self.previewRenderer.position = self.editor.renderer.position
            self.editor.addWorker(self.previewRenderer)
        else:
            self.editor.toolbar.selectTool(-1)

    @property
    def canRotateLevel(self):
        return not isinstance(self.level, (pymclevel.MCInfdevOldLevel, PocketWorld))

    def rotatedSelectionSize(self):
        if self.canRotateLevel:
            sizes = self.level.Blocks.shape
            return sizes[0], sizes[2], sizes[1]
        else:
            return self.level.size

    # ===========================================================================
    # def getSelectionRanges(self):
    #    return self.editor.selectionTool.selectionBox()
    #
    # ===========================================================================
    def getBlockAt(self):
        return None  # use level's blockAt

    def getReticleOrigin(self):
        # returns a new origin for the current selection, where the old origin is at the new selection's center.
        pos, direction = self.editor.blockFaceUnderCursor

        lev = self.editor.level
        size = self.rotatedSelectionSize()
        if not size:
            return
        if size[1] >= self.editor.level.Height:
            direction = (0, 1, 0)  # always use the upward face whenever we're splicing full-height pieces, to avoid "jitter"

        # print size; raise SystemExit
        if any(direction) and pos[1] >= 0:
            x, y, z = map(lambda p, s, d: p - s / 2 + s * d / 2 + (d > 0), pos, size, direction)
        else:
            x, y, z = map(lambda p, s: p - s / 2, pos, size)

        if self.chunkAlign:
            x = x & ~0xf
            z = z & ~0xf

        sy = size[1]
        if sy > lev.Height:  # don't snap really tall stuff to the height
            return Vector(x, y, z)

        if y + sy > lev.Height:
            y = lev.Height - sy
        if y < 0:
            y = 0

        if not isinstance(lev, pymclevel.MCInfdevOldLevel):
            sx = size[0]
            if x + sx > lev.Width:
                x = lev.Width - sx
            if x < 0:
                x = 0

            sz = size[2]
            if z + sz > lev.Length:
                z = lev.Length - sz
            if z < 0:
                z = 0

        return Vector(x, y, z)

    def getReticleBox(self):

        pos = self.getReticleOrigin()
        sizes = self.rotatedSelectionSize()

        if None is sizes:
            return

        return BoundingBox(pos, sizes)

    def getDestBox(self):
        selectionSize = self.rotatedSelectionSize()
        return BoundingBox(self.destPoint, selectionSize)

    def drawTerrainReticle(self):
        if self.level is None:
            return

        if self.destPoint != None:
            destPoint = self.destPoint
            if self.draggingFace is not None:
                # debugDrawPoint()
                destPoint = self.draggingOrigin()

            self.drawTerrainPreview(destPoint)
        else:
            self.drawTerrainPreview(self.getReticleBox().origin)

    draggingColor = (0.77, 1.0, 0.55, 0.05)

    def drawToolReticle(self):

        if self.level is None:
            return

        GL.glPolygonOffset(DepthOffset.CloneMarkers, DepthOffset.CloneMarkers)

        color = self.color
        if self.destPoint is not None:
            color = (self.color[0], self.color[1], self.color[2], 0.06)
            box = self.getDestBox()
            if self.draggingFace is not None:
                o = list(self.draggingOrigin())
                s = list(box.size)
                for i in range(3):
                    if i == self.draggingFace >> 1:
                        continue
                    o[i] -= 1000
                    s[i] += 2000
                guideBox = BoundingBox(o, s)

                color = self.draggingColor
                GL.glColor(1.0, 1.0, 1.0, 0.33)
                with gl.glEnable(GL.GL_BLEND, GL.GL_TEXTURE_2D, GL.GL_DEPTH_TEST):
                    self.editor.sixteenBlockTex.bind()
                    drawFace(guideBox, self.draggingFace ^ 1)
        else:
            box = self.getReticleBox()
            if box is None:
                return
        self.drawRepeatedCube(box, color)

        GL.glPolygonOffset(DepthOffset.CloneReticle, DepthOffset.CloneReticle)
        if self.destPoint:
            box = self.getDestBox()
            if self.draggingFace is not None:
                face = self.draggingFace
                box = BoundingBox(self.draggingOrigin(), box.size)
            face, point = self.boxFaceUnderCursor(box)
            if face is not None:
                GL.glEnable(GL.GL_BLEND)
                GL.glDisable(GL.GL_DEPTH_TEST)

                GL.glColor(*self.color)
                drawFace(box, face)
                GL.glDisable(GL.GL_BLEND)
                GL.glEnable(GL.GL_DEPTH_TEST)

    def drawRepeatedCube(self, box, color):
        # draw several cubes according to the repeat count
        # it's not really sensible to repeat a crane because the origin point is literally out of this world.
        delta = box.origin - self.selectionBox().origin

        for i in range(self.repeatCount):
            self.editor.drawConstructionCube(box, color)
            box = BoundingBox(box.origin + delta, box.size)

    def sourceLevel(self):
        return self.level

    @alertException
    def rotate(self, amount=1):
        if self.canRotateLevel:
            self.rotation += amount
            self.rotation &= 0x3
            for i in range(amount & 0x3):
                self.level.rotateLeft()

            self.previewRenderer.level = self.level

    @alertException
    def roll(self, amount=1):
        if self.canRotateLevel:
            for i in range(amount & 0x3):
                self.level.roll()

            self.previewRenderer.level = self.level

    @alertException
    def flip(self, amount=1):
        if self.canRotateLevel:
            for i in range(amount & 0x1):
                self.level.flipVertical()

            self.previewRenderer.level = self.level

    @alertException
    def mirror(self):
        if self.canRotateLevel:
            yaw = int(self.editor.mainViewport.yaw) % 360
            if (yaw >= 45 and yaw < 135) or (yaw > 225 and yaw <= 315):
                self.level.flipEastWest()
            else:
                self.level.flipNorthSouth()

            self.previewRenderer.level = self.level

    def option1(self):
        self.copyAir = not self.copyAir

    def option2(self):
        self.copyWater = not self.copyWater

    draggingFace = None
    draggingStartPoint = None

    def draggingOrigin(self):
        p = self._draggingOrigin()
        return p

    def _draggingOrigin(self):
        dragPos = map(int, map(numpy.floor, self.positionOnDraggingPlane()))
        delta = map(lambda s, e: e - int(numpy.floor(s)), self.draggingStartPoint, dragPos)

        if pygame.key.get_mods() & pygame.KMOD_SHIFT:
            ad = map(abs, delta)
            midx = ad.index(max(ad))
            d = [0, 0, 0]
            d[midx] = delta[midx]
            dragY = self.draggingFace >> 1
            d[dragY] = delta[dragY]
            delta = d

        p = self.destPoint + delta
        if self.chunkAlign:
            p = [i // 16 * 16 for i in p]
        return Vector(*p)

    def positionOnDraggingPlane(self):
        pos = self.editor.mainViewport.cameraPosition
        dim = self.draggingFace >> 1
#        if key.get_mods() & KMOD_SHIFT:
#            dim = self.findBestTrackingPlane(self.draggingFace)
#
        distance = self.draggingStartPoint[dim] - pos[dim]
        distance += self.draggingY

        mouseVector = self.editor.mainViewport.mouseVector
        scale = distance / (mouseVector[dim] or 1)
        point = map(lambda a, b: a * scale + b, mouseVector, pos)
        return point

    draggingY = 0

    @alertException
    def mouseDown(self, evt, pos, direction):
        box = self.selectionBox()
        if not box:
            return
        self.draggingY = 0

        if self.destPoint is not None:
            if evt.num_clicks == 2:
                self.pickUp()
                return

            face, point = self.boxFaceUnderCursor(self.getDestBox())
            if face is not None:
                self.draggingFace = face
                self.draggingStartPoint = point

        else:
            self.destPoint = self.getReticleOrigin()

            if self.panel and self.panel.useOffsetInput:
                self.panel.offsetInput.setCoords(self.destPoint - box.origin)
            print "Destination: ", self.destPoint

    @alertException
    def mouseUp(self, evt, pos, direction):
        if self.draggingFace is not None:
            self.destPoint = self.draggingOrigin()

        self.draggingFace = None
        self.draggingStartPoint = None

    def increaseToolReach(self):
        if self.draggingFace is not None:
            d = (1, -1)[self.draggingFace & 1]
            if self.draggingFace >> 1 != 1:  # xxxxx y
                d = -d
            self.draggingY += d
            x, y, z = self.editor.mainViewport.cameraPosition
            pos = [x, y, z]
            pos[self.draggingFace >> 1] += d
            self.editor.mainViewport.cameraPosition = tuple(pos)

        else:
            self.cloneCameraDistance = self.editor._incrementReach(self.cloneCameraDistance)
        return True

    def decreaseToolReach(self):
        if self.draggingFace is not None:
            d = (1, -1)[self.draggingFace & 1]
            if self.draggingFace >> 1 != 1:  # xxxxx y
                d = -d

            self.draggingY -= d
            x, y, z = self.editor.mainViewport.cameraPosition
            pos = [x, y, z]
            pos[self.draggingFace >> 1] -= d
            self.editor.mainViewport.cameraPosition = tuple(pos)

        else:
            self.cloneCameraDistance = self.editor._decrementReach(self.cloneCameraDistance)
        return True

    def resetToolReach(self):
        if self.draggingFace is not None:
            x, y, z = self.editor.mainViewport.cameraPosition
            pos = [x, y, z]
            pos[self.draggingFace >> 1] += (1, -1)[self.draggingFace & 1] * -self.draggingY
            self.editor.mainViewport.cameraPosition = tuple(pos)
            self.draggingY = 0

        else:
            self.cloneCameraDistance = max(self.editor.defaultCameraToolDistance, self.safeToolDistance())

        return True

    def pickUp(self):
        if self.destPoint == None:
            return

        box = self.selectionBox()

        # pick up the object. reset the tool distance to the object's distance from the camera
        d = map(lambda a, b, c: abs(a - b - c / 2), self.editor.mainViewport.cameraPosition, self.destPoint, box.size)
        self.cloneCameraDistance = numpy.sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2])
        self.destPoint = None
        # self.panel.performButton.enabled = False
        print "Picked up"

    @alertException
    def confirm(self):
        destPoint = self.destPoint
        if destPoint is None:
            return

        sourceLevel = self.sourceLevel()
        sourceBox = sourceLevel.bounds

        destLevel = self.editor.level
        destVolume = BoundingBox(destPoint, sourceBox.size).volume

        op = CloneOperation(editor=self.editor,
                            sourceLevel=sourceLevel,
                            sourceBox=sourceBox,
                            originSourceBox=self.selectionBox(),
                            destLevel=destLevel,
                            destPoint=self.destPoint,
                            copyAir=self.copyAir,
                            copyWater=self.copyWater,
                            copyBiomes=self.copyBiomes,
                            repeatCount=self.repeatCount)

        self.editor.toolbar.selectTool(-1)  # deselect tool so that the clone tool's selection change doesn't update its schematic

        self.editor.addUnsavedEdit()

        self.editor.addOperation(op)

        dirtyBox = op.dirtyBox()
        if dirtyBox:
            self.editor.invalidateBox(dirtyBox)
        self.editor.renderer.invalidateChunkMarkers()

        self.editor.currentOperation = None

        self.destPoint = None
        self.level = None

    def discardPreviewer(self):
        if self.previewRenderer is None:
            return
        self.previewRenderer.stopWork()
        self.previewRenderer.discardAllChunks()
        self.editor.removeWorker(self.previewRenderer)
        self.previewRenderer = None


class ConstructionToolPanel (CloneToolPanel):
    useOffsetInput = False


class ConstructionTool(CloneTool):
    surfaceBuild = True
    toolIconName = "crane"
    tooltipText = "Import"

    panelClass = ConstructionToolPanel

    def toolEnabled(self):
        return True

    def selectionChanged(self):
        pass

    def updateSchematic(self):
        pass

    def quickNudge(self, nudge):
        return map(lambda x: x * 8, nudge)

    def __init__(self, *args):
        CloneTool.__init__(self, *args)
        self.level = None
        self.optionsPanel = None

    @property
    def statusText(self):
        if self.destPoint == None:
            return "Click to set this item down."

        return "Click and drag to reposition the item. Double-click to pick it up. Click Import or press ENTER to confirm."

    def showPanel(self):
        CloneTool.showPanel(self)
        self.panel.performButton.text = "Import"

    def toolReselected(self):
        self.toolSelected()

    #    def cancel(self):
#        print "Cancelled Clone"
#        self.level = None
#        super(ConstructionTool, self).cancel(self)
#

    def createTestBoard(self, anyBlock=True):
        if anyBlock:
            allBlocks = [self.editor.level.materials[a, b] for a in range(256) for b in range(16)]
            blockWidth = 64
        else:
            allBlocks = self.editor.level.materials.allBlocks
            blockWidth = 16
        blockCount = len(allBlocks)

        width = blockWidth * 3 + 1
        rows = blockCount // blockWidth + 1
        length = rows * 3 + 1
        height = 3

        schematic = pymclevel.MCSchematic((width, height, length), mats=self.editor.level.materials)
        schematic.Blocks[:, :, 0] = 1

        for i, block in enumerate(allBlocks):
            col = (i % blockWidth) * 3 + 1
            row = (i // blockWidth) * 3
            schematic.Blocks[col:col + 2, row:row + 2, 2] = block.ID
            schematic.Data[col:col + 2, row:row + 2, 2] = block.blockData

        return schematic

    def toolSelected(self):
        self.editor.mouseLookOff()

        mods = pygame.key.get_mods()
        if mods & pygame.KMOD_ALT and mods & pygame.KMOD_SHIFT:
            self.loadLevel(self.createTestBoard())
            return

        self.editor.mouseLookOff()

        clipFilename = mcplatform.askOpenFile(title='Import a schematic or level...', schematics=True)
        # xxx mouthful
        if clipFilename:

            self.loadSchematic(clipFilename)

        print "Canceled"
        if self.level is None:
            print "No level selected."

            self.editor.toolbar.selectTool(-1)

        # CloneTool.toolSelected(self)

    originalLevelSize = (0, 0, 0)

    def loadSchematic(self, filename):
        """ actually loads a schematic or a level """

        try:
            level = pymclevel.fromFile(filename, readonly=True)
            self.loadLevel(level)
        except Exception, e:
            logging.warn(u"Unable to import file %s : %s", filename, e)

            traceback.print_exc()
            if filename:
                # self.editor.toolbar.selectTool(-1)
                alert(u"I don't know how to import this file: {0}.\n\nError: {1!r}".format(os.path.basename(filename), e))

            return

    @alertException
    def loadLevel(self, level):
        if level:
            self.level = level
            self.repeatCount = 1
            self.destPoint = None

            self.editor.currentTool = self  # because save window triggers loseFocus, which triggers tool.cancel... hmmmmmm

            self.cloneCameraDistance = self.safeToolDistance()

            self.chunkAlign = isinstance(self.level, pymclevel.MCInfdevOldLevel) and all(b % 16 == 0 for b in self.level.bounds.size)

            self.setupPreview()
            self.originalLevelSize = (self.level.Width, self.level.Height, self.level.Length)
            self.showPanel()
            return

    def selectionSize(self):
        if not self.level:
            return None
        return  self.originalLevelSize

    def selectionBox(self):
        if not self.level:
            return None
        return BoundingBox((0, 0, 0), self.selectionSize())

    def sourceLevel(self):
        return self.level

    def mouseDown(self, evt, pos, direction):
        # x,y,z = pos
        box = self.selectionBox()
        if not box:
            return

        CloneTool.mouseDown(self, evt, pos, direction)
