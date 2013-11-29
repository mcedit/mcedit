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
from OpenGL import GL
import numpy
import pygame
from albow import Label, Button, Column
from depths import DepthOffset
from editortools.blockpicker import BlockPicker
from editortools.blockview import BlockButton
from editortools.editortool import EditorTool
from editortools.tooloptions import ToolOptions
from glbackground import Panel
from glutils import Texture
from mceutils import showProgress, CheckBoxLabel, alertException, setWindowCaption
from operation import Operation

import config
import pymclevel

FillSettings = config.Settings("Fill")
FillSettings.chooseBlockImmediately = FillSettings("Choose Block Immediately", True)


class BlockFillOperation(Operation):
    def __init__(self, editor, destLevel, destBox, blockInfo, blocksToReplace):
        super(BlockFillOperation, self).__init__(editor, destLevel)
        self.destBox = destBox
        self.blockInfo = blockInfo
        self.blocksToReplace = blocksToReplace

    def name(self):
        return "Fill with " + self.blockInfo.name

    def perform(self, recordUndo=True):
        if recordUndo:
            self.undoLevel = self.extractUndo(self.level, self.destBox)

        destBox = self.destBox
        if self.level.bounds == self.destBox:
            destBox = None

        fill = self.level.fillBlocksIter(destBox, self.blockInfo, blocksToReplace=self.blocksToReplace)
        showProgress("Replacing blocks...", fill, cancel=True)

    def bufferSize(self):
        return self.destBox.volume * 2

    def dirtyBox(self):
        return self.destBox


class FillToolPanel(Panel):

    def __init__(self, tool):
        Panel.__init__(self)
        self.tool = tool
        replacing = tool.replacing

        self.blockButton = BlockButton(tool.editor.level.materials)
        self.blockButton.blockInfo = tool.blockInfo
        self.blockButton.action = self.pickFillBlock

        self.fillWithLabel = Label("Fill with:", width=self.blockButton.width, align="c")
        self.fillButton = Button("Fill", action=tool.confirm, width=self.blockButton.width)
        self.fillButton.tooltipText = "Shortcut: ENTER"

        rollkey = config.config.get("Keys", "Roll").upper()

        self.replaceLabel = replaceLabel = Label("Replace", width=self.blockButton.width)
        replaceLabel.mouse_down = lambda a: self.tool.toggleReplacing()
        replaceLabel.fg_color = (177, 177, 255, 255)
        # replaceLabelRow = Row( (Label(rollkey), replaceLabel) )
        replaceLabel.tooltipText = "Shortcut: {0}".format(rollkey)
        replaceLabel.align = "c"

        col = (self.fillWithLabel,
                self.blockButton,
                # swapRow,
                replaceLabel,
                # self.replaceBlockButton,
                self.fillButton)

        if replacing:
            self.fillWithLabel = Label("Find:", width=self.blockButton.width, align="c")

            self.replaceBlockButton = BlockButton(tool.editor.level.materials)
            self.replaceBlockButton.blockInfo = tool.replaceBlockInfo
            self.replaceBlockButton.action = self.pickReplaceBlock
            self.replaceLabel.text = "Replace with:"

            self.swapButton = Button("Swap", action=self.swapBlockTypes, width=self.blockButton.width)
            self.swapButton.fg_color = (255, 255, 255, 255)
            self.swapButton.highlight_color = (60, 255, 60, 255)
            swapkey = config.config.get("Keys", "Swap").upper()

            self.swapButton.tooltipText = "Shortcut: {0}".format(swapkey)

            self.fillButton = Button("Replace", action=tool.confirm, width=self.blockButton.width)
            self.fillButton.tooltipText = "Shortcut: ENTER"

            col = (self.fillWithLabel,
                    self.blockButton,
                    replaceLabel,
                    self.replaceBlockButton,
                    self.swapButton,
                    self.fillButton)

        col = Column(col)

        self.add(col)
        self.shrink_wrap()

    def swapBlockTypes(self):
        t = self.tool.replaceBlockInfo
        self.tool.replaceBlockInfo = self.tool.blockInfo
        self.tool.blockInfo = t

        self.replaceBlockButton.blockInfo = self.tool.replaceBlockInfo
        self.blockButton.blockInfo = self.tool.blockInfo  # xxx put this in a property

    def pickReplaceBlock(self):
        blockPicker = BlockPicker(self.tool.replaceBlockInfo, self.tool.editor.level.materials)
        if blockPicker.present():
            self.replaceBlockButton.blockInfo = self.tool.replaceBlockInfo = blockPicker.blockInfo

    def pickFillBlock(self):
        blockPicker = BlockPicker(self.tool.blockInfo, self.tool.editor.level.materials, allowWildcards=True)
        if blockPicker.present():
            self.tool.blockInfo = blockPicker.blockInfo


class FillToolOptions(ToolOptions):
    def __init__(self, tool):
        Panel.__init__(self)
        self.tool = tool
        self.autoChooseCheckBox = CheckBoxLabel("Choose Block Immediately",
                                                ref=FillSettings.chooseBlockImmediately.propertyRef(),
                                                tooltipText="When the fill tool is chosen, prompt for a block type.")

        col = Column((Label("Fill Options"), self.autoChooseCheckBox, Button("OK", action=self.dismiss)))

        self.add(col)
        self.shrink_wrap()


class FillTool(EditorTool):
    toolIconName = "fill"
    _blockInfo = pymclevel.alphaMaterials.Stone
    replaceBlockInfo = pymclevel.alphaMaterials.Air
    tooltipText = "Fill and Replace\nRight-click for options"
    replacing = False

    def __init__(self, *args, **kw):
        EditorTool.__init__(self, *args, **kw)
        self.optionsPanel = FillToolOptions(self)

    @property
    def blockInfo(self):
        return self._blockInfo

    @blockInfo.setter
    def blockInfo(self, bt):
        self._blockInfo = bt
        if self.panel:
            self.panel.blockButton.blockInfo = bt

    def levelChanged(self):
        self.initTextures()

    def showPanel(self):
        if self.panel:
            self.panel.parent.remove(self.panel)

        panel = FillToolPanel(self)
        panel.centery = self.editor.centery
        panel.left = self.editor.left
        panel.anchor = "lwh"

        self.panel = panel
        self.editor.add(panel)

    def toolEnabled(self):
        return not (self.selectionBox() is None)

    def toolSelected(self):
        box = self.selectionBox()
        if None is box:
            return

        self.replacing = False
        self.showPanel()

        if self.chooseBlockImmediately:
            blockPicker = BlockPicker(self.blockInfo, self.editor.level.materials, allowWildcards=True)

            if blockPicker.present():
                self.blockInfo = blockPicker.blockInfo
                self.showPanel()

            else:
                self.editor.toolbar.selectTool(-1)

    chooseBlockImmediately = FillSettings.chooseBlockImmediately.configProperty()

    def toolReselected(self):
        self.showPanel()
        self.panel.pickFillBlock()

    def cancel(self):
        self.hidePanel()

    @alertException
    def confirm(self):
        box = self.selectionBox()
        if None is box:
            return

        with setWindowCaption("REPLACING - "):
            self.editor.freezeStatus("Replacing %0.1f million blocks" % (float(box.volume) / 1048576.,))

            if self.replacing:
                if self.blockInfo.wildcard:
                    print "Wildcard replace"
                    blocksToReplace = []
                    for i in range(16):
                        blocksToReplace.append(self.editor.level.materials.blockWithID(self.blockInfo.ID, i))
                else:
                    blocksToReplace = [self.blockInfo]

                op = BlockFillOperation(self.editor, self.editor.level, self.selectionBox(), self.replaceBlockInfo, blocksToReplace)

            else:
                blocksToReplace = []
                op = BlockFillOperation(self.editor, self.editor.level, self.selectionBox(), self.blockInfo, blocksToReplace)


        self.editor.addOperation(op)

        self.editor.addUnsavedEdit()
        self.editor.invalidateBox(box)
        self.editor.toolbar.selectTool(-1)

    def roll(self):
        self.toggleReplacing()

    def toggleReplacing(self):
        self.replacing = not self.replacing

        self.hidePanel()
        self.showPanel()
        if self.replacing:
            self.panel.pickReplaceBlock()

    @alertException
    def swap(self):
        if self.panel and self.replacing:
            self.panel.swapBlockTypes()

    def initTextures(self):

        terrainTexture = self.editor.level.materials.terrainTexture

        blockTextures = self.editor.level.materials.blockTextures[:, 0]

        if hasattr(self, 'blockTextures'):
            for tex in self.blockTextures.itervalues():
                tex.delete()

        self.blockTextures = {}

        pixelWidth = 512 if self.editor.level.materials.name in ("Pocket", "Alpha") else 256

        def blockTexFunc(type):
            def _func():
                s, t = blockTextures[type][0]
                if not hasattr(terrainTexture, "data"):
                    return
                w, h = terrainTexture.data.shape[:2]
                s = s * w / pixelWidth
                t = t * h / pixelWidth
                texData = numpy.array(terrainTexture.data[t:t + h / 16, s:s + w / 16])
                GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, w / 16, h / 16, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, texData)
            return _func

        for type in range(256):
            self.blockTextures[type] = Texture(blockTexFunc(type))

    def drawToolReticle(self):
        if pygame.key.get_mods() & pygame.KMOD_ALT:
            # eyedropper mode
            self.editor.drawWireCubeReticle(color=(0.2, 0.6, 0.9, 1.0))

    def drawToolMarkers(self):
        if self.editor.currentTool != self:
            return

        if self.panel and self.replacing:
            blockInfo = self.replaceBlockInfo
        else:
            blockInfo = self.blockInfo

        color = 1.0, 1.0, 1.0, 0.35
        if blockInfo:
            tex = self.blockTextures.get(blockInfo.ID, self.blockTextures[255]) # xxx

            # color = (1.5 - alpha, 1.0, 1.5 - alpha, alpha - 0.35)
            GL.glMatrixMode(GL.GL_TEXTURE)
            GL.glPushMatrix()
            GL.glScale(16., 16., 16.)

        else:
            tex = None
            # color = (1.0, 0.3, 0.3, alpha - 0.35)

        GL.glPolygonOffset(DepthOffset.FillMarkers, DepthOffset.FillMarkers)
        self.editor.drawConstructionCube(self.selectionBox(),
                                         color,
                                         texture=tex)

        if blockInfo:
            GL.glMatrixMode(GL.GL_TEXTURE)
            GL.glPopMatrix()

    @property
    def statusText(self):
        return "Press {hotkey} to choose a block. Press {R} to enter replace mode. Click Fill or press ENTER to confirm.".format(hotkey=self.hotkey, R=config.config.get("Keys", "Roll").upper())

    @property
    def worldTooltipText(self):
        if pygame.key.get_mods() & pygame.KMOD_ALT:
            try:
                if self.editor.blockFaceUnderCursor is None:
                    return
                pos = self.editor.blockFaceUnderCursor[0]
                blockID = self.editor.level.blockAt(*pos)
                blockdata = self.editor.level.blockDataAt(*pos)
                return "Click to use {0} ({1}:{2})".format(self.editor.level.materials.blockWithID(blockID, blockdata).name, blockID, blockdata)

            except Exception, e:
                return repr(e)

    def mouseUp(self, *args):
        return self.editor.selectionTool.mouseUp(*args)

    @alertException
    def mouseDown(self, evt, pos, dir):
        if pygame.key.get_mods() & pygame.KMOD_ALT:
            id = self.editor.level.blockAt(*pos)
            data = self.editor.level.blockDataAt(*pos)

            self.blockInfo = self.editor.level.materials.blockWithID(id, data)
        else:
            return self.editor.selectionTool.mouseDown(evt, pos, dir)
