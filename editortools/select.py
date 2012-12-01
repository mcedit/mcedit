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
from OpenGL import GL

from collections import defaultdict
import numpy
import pygame
from albow import Row, Label, Button, AttrRef, Column, ask
import config
from depths import DepthOffset
from editortools.editortool import EditorTool
from editortools.nudgebutton import NudgeButton
from editortools.tooloptions import ToolOptions
from glbackground import Panel
from mceutils import ChoiceButton, CheckBoxLabel, IntInputRow, alertException, drawCube, drawFace, drawTerrainCuttingWire, setWindowCaption, showProgress
import mcplatform
from operation import Operation
import pymclevel
from pymclevel.box import Vector, BoundingBox, FloatBox
from fill import  BlockFillOperation
import tempfile

SelectSettings = config.Settings("Selection")
SelectSettings.showPreviousSelection = SelectSettings("Show Previous Selection", True)
SelectSettings.color = SelectSettings("Color", "teal")

ColorSettings = config.Settings("Selection Colors")
ColorSettings.defaultColors = {}


class ColorSetting(config.Setting):
    def __init__(self, section, name, dtype, default):
        super(ColorSetting, self).__init__(section, name, dtype, default)
        ColorSettings.defaultColors[name] = self

    def set(self, val):
        values = str(tuple(val))[1:-1]
        super(ColorSetting, self).set(values)

    def get(self):
        colorValues = super(ColorSetting, self).get()
        return parseValues(colorValues)
ColorSettings.Setting = ColorSetting


def parseValues(colorValues):
    if colorValues is None:
        return 1., 1., 1.

    try:
        values = colorValues.split(",")
        values = [(min(max(float(x), 0.0), 1.0)) for x in values]
    except:
        values = (1.0, 1.0, 1.0)

    return tuple(values)

ColorSettings("white", (1.0, 1.0, 1.0))

ColorSettings("blue", (0.75, 0.75, 1.0))
ColorSettings("green", (0.75, 1.0, 0.75))
ColorSettings("red", (1.0, 0.75, 0.75))

ColorSettings("teal", (0.75, 1.0, 1.0))
ColorSettings("pink", (1.0, 0.75, 1.0))
ColorSettings("yellow", (1.0, 1.0, 0.75))

ColorSettings("grey", (0.6, 0.6, 0.6))
ColorSettings("black", (0.0, 0.0, 0.0))


def GetSelectionColor(colorWord=None):
    if colorWord is None:
        colorWord = SelectSettings.color.get()

    colorValues = config.config.get("Selection Colors", colorWord)
    return parseValues(colorValues)


class SelectionToolOptions(ToolOptions):
    def updateColors(self):
        names = [name.lower() for (name, value) in config.config.items("Selection Colors")]
        self.colorPopupButton.choices = [name.capitalize() for name in names]

        color = SelectSettings.color.get()

        self.colorPopupButton.choiceIndex = names.index(color.lower())

    def __init__(self, tool):
        Panel.__init__(self)
        self.tool = tool

        self.colorPopupButton = ChoiceButton([], choose=self.colorChanged)
        self.updateColors()

        colorRow = Row((Label("Color: ", align="r"), self.colorPopupButton))
        okButton = Button("OK", action=self.dismiss)
        showPreviousRow = CheckBoxLabel("Show Previous Selection", ref=AttrRef(tool, 'showPreviousSelection'))

        def set_colorvalue(ch):
            i = "RGB".index(ch)

            def _set(val):
                choice = self.colorPopupButton.selectedChoice
                values = GetSelectionColor(choice)
                values = values[:i] + (val / 255.0,) + values[i + 1:]
                setting = str(values)[1:-1]
                config.config.set("Selection Colors", choice, setting)
                self.colorChanged()

            return _set

        def get_colorvalue(ch):
            i = "RGB".index(ch)

            def _get():
                return int(GetSelectionColor()[i] * 255)
            return _get

        colorValuesInputs = [IntInputRow(ch + ":", get_value=get_colorvalue(ch),
                                              set_value=set_colorvalue(ch),
                                              min=0, max=255)
                             for ch in "RGB"]

        colorValuesRow = Row(colorValuesInputs)
        col = Column((Label("Selection Options"), colorRow, colorValuesRow, showPreviousRow, okButton))

        self.add(col)
        self.shrink_wrap()

    def colorChanged(self):
        SelectSettings.color.set(self.colorPopupButton.selectedChoice)
        self.tool.updateSelectionColor()


class SelectionToolPanel(Panel):
    def __init__(self, tool):
        Panel.__init__(self)
        self.tool = tool

        nudgeBlocksButton = NudgeButton()
        nudgeBlocksButton.nudge = tool.nudgeBlocks
        nudgeBlocksButton.bg_color = (0.3, 1.0, 0.3, 0.35)
        self.nudgeBlocksButton = nudgeBlocksButton

        nudgeSelectionButton = NudgeButton()
        nudgeSelectionButton.nudge = tool.nudgeSelection
        nudgeSelectionButton.bg_color = tool.selectionColor + (0.7,)

        deleteBlocksButton = Button("Delete Blocks", action=self.tool.deleteBlocks)
        deleteBlocksButton.tooltipText = "Fill the selection with Air. Shortcut: DELETE"
        deleteEntitiesButton = Button("Delete Entities", action=self.tool.deleteEntities)
        deleteEntitiesButton.tooltipText = "Remove all entities within the selection"
        # deleteTileEntitiesButton = Button("Delete TileEntities", action=self.tool.deleteTileEntities)
        analyzeButton = Button("Analyze", action=self.tool.analyzeSelection)
        analyzeButton.tooltipText = "Count the different blocks and entities in the selection and display the totals."
        cutButton = Button("Cut", action=self.tool.cutSelection)
        cutButton.tooltipText = "Take a copy of all blocks and entities within the selection, then delete everything within the selection. Shortcut: {0}-X".format(mcplatform.cmd_name)
        copyButton = Button("Copy", action=self.tool.copySelection)
        copyButton.tooltipText = "Take a copy of all blocks and entities within the selection. Shortcut: {0}-C".format(mcplatform.cmd_name)
        pasteButton = Button("Paste", action=self.tool.editor.pasteSelection)
        pasteButton.tooltipText = "Import the last item taken by Cut or Copy. Shortcut: {0}-V".format(mcplatform.cmd_name)
        exportButton = Button("Export", action=self.tool.exportSelection)
        exportButton.tooltipText = "Export the selection to a .schematic file. Shortcut: {0}-E".format(mcplatform.cmd_name)

        selectButton = Button("Select Chunks")
        selectButton.tooltipText = "Expand the selection to the edges of the chunks within"
        selectButton.action = tool.selectChunks
        selectButton.highlight_color = (0, 255, 0)

        deselectButton = Button("Deselect")
        deselectButton.tooltipText = "Remove the selection. Shortcut: {0}-D".format(mcplatform.cmd_name)
        deselectButton.action = tool.deselect
        deselectButton.highlight_color = (0, 255, 0)

        nudgeRow = Row((nudgeBlocksButton, nudgeSelectionButton))
        buttonsColumn = (
            nudgeRow,
            deselectButton,
            selectButton,
            deleteBlocksButton,
            deleteEntitiesButton,
            analyzeButton,
            cutButton,
            copyButton,
            pasteButton,
            exportButton,
        )

        buttonsColumn = Column(buttonsColumn)

        self.add(buttonsColumn)
        self.shrink_wrap()


class NudgeBlocksOperation(Operation):
    def __init__(self, editor, level, sourceBox, direction):
        super(NudgeBlocksOperation, self).__init__(editor, level)

        self.sourceBox = sourceBox
        self.destBox = BoundingBox(sourceBox.origin + direction, sourceBox.size)
        self.nudgeSelection = NudgeSelectionOperation(editor.selectionTool, direction)

    def dirtyBox(self):
        return self.sourceBox.union(self.destBox)

    def perform(self, recordUndo=True):
        level = self.editor.level
        tempSchematic = level.extractSchematic(self.sourceBox)
        if tempSchematic:
            dirtyBox = self.dirtyBox()
            if recordUndo:
                self.undoLevel = self.extractUndo(level, dirtyBox)

            level.fillBlocks(self.sourceBox, level.materials.Air)
            level.removeTileEntitiesInBox(self.sourceBox)
            level.removeTileEntitiesInBox(self.destBox)

            level.removeEntitiesInBox(self.sourceBox)
            level.removeEntitiesInBox(self.destBox)
            level.copyBlocksFrom(tempSchematic, tempSchematic.bounds, self.destBox.origin)
            self.editor.invalidateBox(dirtyBox)

            self.nudgeSelection.perform(recordUndo)

    def undo(self):
        super(NudgeBlocksOperation, self).undo()
        self.nudgeSelection.undo()


class SelectionTool(EditorTool):
    # selectionColor = (1.0, .9, .9)
    color = (0.7, 0., 0.7)
    surfaceBuild = False
    toolIconName = "selection"
    tooltipText = "Select\nRight-click for options"

    bottomLeftPoint = topRightPoint = None

    bottomLeftColor = (0., 0., 1.)
    bottomLeftSelectionColor = (0.75, 0.62, 1.0)

    topRightColor = (0.89, 0.89, 0.35)
    topRightSelectionColor = (1, 0.99, 0.65)

    nudgePanel = None

    def __init__(self, editor):
        self.editor = editor
        editor.selectionTool = self
        self.selectionPoint = None

        self.optionsPanel = SelectionToolOptions(self)

        self.updateSelectionColor()

    # --- Tooltips ---

    def describeBlockAt(self, pos):
        blockID = self.editor.level.blockAt(*pos)
        blockdata = self.editor.level.blockDataAt(*pos)
        text = "X: {pos[0]}\nY: {pos[1]}\nZ: {pos[2]}\n".format(pos=pos)
        text += "L: {0} S: {1}\n".format(self.editor.level.blockLightAt(*pos), self.editor.level.skylightAt(*pos))
        text += "{name} ({bid}:{bdata})\n".format(name=self.editor.level.materials.names[blockID][blockdata], bid=blockID, pos=pos, bdata=blockdata)
        t = self.editor.level.tileEntityAt(*pos)
        if t:
            text += "TileEntity:\n"
            try:
                text += "{id}: {pos}\n".format(id=t["id"].value, pos=[t[a].value for a in "xyz"])
            except Exception, e:
                text += repr(e)
            if "Items" not in t:
                text += str(t)
        return text

    @property
    def worldTooltipText(self):
        pos, face = self.editor.blockFaceUnderCursor
        if pos is None:
            return
        try:

            size = None
            box = self.selectionBoxInProgress()
            if box:
                size = "{s[0]} W x {s[2]} L x {s[1]} H".format(s=box.size)
                text = size
            if pygame.key.get_mods() & pygame.KMOD_ALT:
                if size:
                    return size
                elif self.dragResizeFace is not None:
                    return None
                else:

                    return self.describeBlockAt(pos)

                return text.strip()

            else:

                return self.worldTooltipForBlock(pos) or size

        except Exception, e:
            return repr(e)

    def worldTooltipForBlock(self, pos):

        x, y, z = pos
        cx, cz = x / 16, z / 16
        if isinstance(self.editor.level, pymclevel.MCInfdevOldLevel):

            if y == 0:
                try:
                    chunk = self.editor.level.getChunk(cx, cz)
                except pymclevel.ChunkNotPresent:
                    return "Chunk not present."
                if not chunk.HeightMap.any():
                    if self.editor.level.blockAt(x, y, z):
                        return "Chunk HeightMap is incorrect! Please relight this chunk as soon as possible!"
                    else:
                        return "Chunk is present and filled with air."

        block = self.editor.level.blockAt(*pos)
        if block in (pymclevel.alphaMaterials.Chest.ID,
                     pymclevel.alphaMaterials.Furnace.ID,
                     pymclevel.alphaMaterials.LitFurnace.ID,
                     pymclevel.alphaMaterials.Dispenser.ID):
            t = self.editor.level.tileEntityAt(*pos)
            if t:
                containerID = t["id"].value
                if "Items" in t:
                    items = t["Items"]
                    d = defaultdict(int)
                    for item in items:
                        if "id" in item and "Count" in item:
                            d[item["id"].value] += item["Count"].value

                    if len(d):
                        items = sorted((v, k) for (k, v) in d.iteritems())
                        try:
                            top = pymclevel.items.items.findItem(items[0][1]).name
                        except Exception, e:
                            top = repr(e)
                        return "{0} contains {len} items. (Mostly {top}) \n\nDouble-click to edit {0}.".format(containerID, len=len(d), top=top)
                    else:
                        return "Empty {0}. \n\nDouble-click to edit {0}.".format(containerID)
            else:
                return "Double-click to initialize the {0}.".format(pymclevel.alphaMaterials.names[block][0])
        if block == pymclevel.alphaMaterials.MonsterSpawner.ID:

            t = self.editor.level.tileEntityAt(*pos)
            if t:
                id = t["EntityId"].value
            else:
                id = "[Undefined]"

            return "{id} spawner. \n\nDouble-click to edit spawner.".format(id=id)

        if block in (pymclevel.alphaMaterials.Sign.ID,
                     pymclevel.alphaMaterials.WallSign.ID):
            t = self.editor.level.tileEntityAt(*pos)
            if t:
                signtext = u"\n".join(t["Text" + str(x)].value for x in range(1, 5))
            else:
                signtext = "Undefined"
            return "Sign text: \n" + signtext + "\n\n" + "Double-click to edit sign."

        absentTexture = (self.editor.level.materials.blockTextures[block, 0, 0] == pymclevel.materials.NOTEX).all()
        if absentTexture:
            return self.describeBlockAt(pos)

    @alertException
    def selectChunks(self):
        box = self.selectionBox()
        newBox = BoundingBox((box.mincx << 4, 0, box.mincz << 4), (box.maxcx - box.mincx << 4, self.editor.level.Height, box.maxcz - box.mincz << 4))
        self.editor.selectionTool.setSelection(newBox)

    def updateSelectionColor(self):

        self.selectionColor = GetSelectionColor()
        from albow import theme
        theme.root.sel_color = tuple(int(x * 112) for x in self.selectionColor)

    # --- Nudge functions ---

    @alertException
    def nudgeBlocks(self, dir):
        if pygame.key.get_mods() & pygame.KMOD_SHIFT:
            dir = dir * (16, 16, 16)
        op = NudgeBlocksOperation(self.editor, self.editor.level, self.selectionBox(), dir)

        self.performWithRetry(op)
        self.editor.addOperation(op)
        self.editor.addUnsavedEdit()

    def nudgeSelection(self, dir):
        if pygame.key.get_mods() & pygame.KMOD_SHIFT:
            dir = dir * (16, 16, 16)

        points = self.getSelectionPoints()
        bounds = self.editor.level.bounds

        if not all((p + dir) in bounds for p in points):
            return

        op = NudgeSelectionOperation(self, dir)
        self.performWithRetry(op)
        # self.editor.addOperation(op)

    def nudgePoint(self, p, n):
        if self.selectionBox() is None:
            return
        if pygame.key.get_mods() & pygame.KMOD_SHIFT:
            n = n * (16, 16, 16)
        self.setSelectionPoint(p, self.getSelectionPoint(p) + n)

    def nudgeBottomLeft(self, n):
        return self.nudgePoint(0, n)

    def nudgeTopRight(self, n):
        return self.nudgePoint(1, n)

    # --- Panel functions ---
    def sizeLabelText(self):
        size = self.selectionSize()
        if self.dragResizeFace is not None:
            size = self.draggingSelectionBox().size

        return "{0}W x {2}L x {1}H".format(*size)

    def showPanel(self):
        if self.selectionBox() is None:
            return

        if self.nudgePanel is None:
            self.nudgePanel = Panel()

            self.nudgePanel.bg_color = map(lambda x: x * 0.5, self.selectionColor) + [0.5, ]

            self.bottomLeftNudge = bottomLeftNudge = NudgeButton()
            bottomLeftNudge.nudge = self.nudgeBottomLeft
            bottomLeftNudge.anchor = "brwh"

            bottomLeftNudge.bg_color = self.bottomLeftColor + (0.33,)

            self.topRightNudge = topRightNudge = NudgeButton()
            topRightNudge.nudge = self.nudgeTopRight
            topRightNudge.anchor = "blwh"

            topRightNudge.bg_color = self.topRightColor + (0.33,)

            self.nudgeRow = Row((bottomLeftNudge, topRightNudge))
            self.nudgeRow.anchor = "blrh"
            self.nudgePanel.add(self.nudgeRow)

            self.editor.add(self.nudgePanel)

        if hasattr(self, 'sizeLabel'):
            self.nudgePanel.remove(self.sizeLabel)
        self.sizeLabel = Label(self.sizeLabelText())
        self.sizeLabel.anchor = "twh"
        self.sizeLabel.tooltipText = "{0:n} blocks".format(self.selectionBox().volume)

        # self.nudgePanelColumn = Column( (self.sizeLabel, self.nudgeRow) )
        self.nudgePanel.top = self.nudgePanel.left = 0

        self.nudgePanel.add(self.sizeLabel)
        self.nudgeRow.top = self.sizeLabel.bottom

        self.nudgePanel.shrink_wrap()
        self.sizeLabel.centerx = self.nudgePanel.centerx
        self.nudgeRow.centerx = self.nudgePanel.centerx

        self.nudgePanel.bottom = self.editor.toolbar.top
        self.nudgePanel.centerx = self.editor.centerx

        self.nudgePanel.anchor = "bwh"

        if self.panel is None and self.editor.currentTool in (self, None):
            if self.bottomLeftPoint is not None and self.topRightPoint is not None:
                self.panel = SelectionToolPanel(self)
                self.panel.left = self.editor.left
                self.panel.centery = self.editor.centery
                self.editor.add(self.panel)

    def hidePanel(self):
        self.editor.remove(self.panel)
        self.panel = None

    def hideNudgePanel(self):
        self.editor.remove(self.nudgePanel)
        self.nudgePanel = None

    selectionInProgress = False
    dragStartPoint = None

    # --- Event handlers ---

    def toolReselected(self):
        self.selectOtherCorner()

    def toolSelected(self):
        # if self.clearSelectionImmediately:
        #    self.setSelectionPoints(None)
        self.showPanel()

    def clampPos(self, pos):
        x, y, z = pos
        w, h, l = self.editor.level.Width, self.editor.level.Height, self.editor.level.Length

        if w > 0:
            if x >= w:
                x = w - 1
            if x < 0:
                x = 0
        if l > 0:
            if z >= l:
                z = l - 1
            if z < 0:
                z = 0

        if y >= h:
            y = h - 1
        if y < 0:
            y = 0

        pos = [x, y, z]
        return pos

    @property
    def currentCornerName(self):
        return ("Blue", "Yellow")[self.currentCorner]

    @property
    def statusText(self):
        # return "selectionInProgress {0} clickSelectionInProgress {1}".format(self.selectionInProgress, self.clickSelectionInProgress)
        if self.selectionInProgress:
            pd = self.editor.blockFaceUnderCursor
            if pd:
                p, d = pd
                if self.dragStartPoint == p:
                    if self.clickSelectionInProgress:

                        return "Click the mouse button again to place the {0} selection corner. Press {1} to switch corners.".format(self.currentCornerName, self.hotkey)
                    else:
                        return "Release the mouse button here to place the {0} selection corner. Press {1} to switch corners.".format(self.currentCornerName, self.hotkey)

            if self.clickSelectionInProgress:
                return "Click the mouse button again to place the other selection corner."

            return "Release the mouse button to finish the selection"

        return "Click or drag to make a selection. Drag the selection walls to resize. Click near the edge to drag the opposite wall.".format(self.currentCornerName, self.hotkey)

    clickSelectionInProgress = False

    def endSelection(self):
        self.selectionInProgress = False
        self.clickSelectionInProgress = False
        self.dragResizeFace = None
        self.dragStartPoint = None

    def cancel(self):
        self.endSelection()
        EditorTool.cancel(self)

    dragResizeFace = None
    dragResizeDimension = None
    dragResizePosition = None

    def mouseDown(self, evt, pos, direction):
        # self.selectNone()

        pos = self.clampPos(pos)
        if self.selectionBox() and not self.selectionInProgress:
            face, point = self.boxFaceUnderCursor(self.selectionBox())

            if face is not None:
                self.dragResizeFace = face
                self.dragResizeDimension = self.findBestTrackingPlane(face)

                # point = map(int, point)
                self.dragResizePosition = point[self.dragResizeDimension]

                return

        if self.selectionInProgress is False:
            self.dragStartPoint = pos
        self.selectionInProgress = True

    def mouseUp(self, evt, pos, direction):
        pos = self.clampPos(pos)
        if self.dragResizeFace is not None:
            box = self.selectionBox()
            if box is not None:
                o, m = self.selectionPointsFromDragResize()

                op = SelectionOperation(self, (o, m))
                self.performWithRetry(op)
                self.editor.addOperation(op)

            self.dragResizeFace = None
            return

        if self.editor.viewMode == "Chunk":
            self.clickSelectionInProgress = True

        if self.dragStartPoint is None and not self.clickSelectionInProgress:
            return

        if self.dragStartPoint != pos or self.clickSelectionInProgress:
            op = SelectionOperation(self, (self.dragStartPoint, pos))
            self.performWithRetry(op)
            self.editor.addOperation(op)
            self.selectionInProgress = False
            self.currentCorner = 1
            self.clickSelectionInProgress = False

        else:
            points = self.getSelectionPoints()
            if not all(points):
                points = (pos, pos)  # set both points on the first click
            else:
                points[self.currentCorner] = pos

            if not self.clickSelectionInProgress:
                self.clickSelectionInProgress = True
            else:
                op = SelectionOperation(self, points)
                self.performWithRetry(op)
                self.editor.addOperation(op)

                self.selectOtherCorner()
                self.selectionInProgress = False
                self.clickSelectionInProgress = False

        if self.chunkMode:
            self.editor.selectionToChunks(remove=evt.alt, add=evt.shift)
            self.editor.toolbar.selectTool(8)

    @property
    def chunkMode(self):
        return self.editor.viewMode == "Chunk" or self.editor.currentTool is self.editor.toolbar.tools[8]

    def selectionBoxInProgress(self):
        if self.editor.blockFaceUnderCursor is None:
            return
        pos = self.editor.blockFaceUnderCursor[0]
        if self.selectionInProgress or self.clickSelectionInProgress:
            return self.selectionBoxForCorners(pos, self.dragStartPoint)

# requires a selection
    def dragResizePoint(self):
        # returns a point representing the intersection between the mouse ray
        # and an imaginary plane perpendicular to the dragged face

        pos = self.editor.mainViewport.cameraPosition
        dim = self.dragResizeDimension
        distance = self.dragResizePosition - pos[dim]

        mouseVector = self.editor.mainViewport.mouseVector
        scale = distance / (mouseVector[dim] or 0.0001)
        point = map(lambda a, b: a * scale + b, mouseVector, pos)
        return point

    def draggingSelectionBox(self):
        p1, p2 = self.selectionPointsFromDragResize()
        box = self.selectionBoxForCorners(p1, p2)
        return box

    def selectionPointsFromDragResize(self):
        point = self.dragResizePoint()
#        glColor(1.0, 1.0, 0.0, 1.0)
#        glPointSize(9.0)
#        glBegin(GL_POINTS)
#        glVertex3f(*point)
#        glEnd()
#

#        facebox = BoundingBox(box.origin, box.size)
#        facebox.origin[dim] = self.dragResizePosition
#        facebox.size[dim] = 0
#        glEnable(GL_BLEND)
#
#        drawFace(facebox, dim * 2)
#
#        glDisable(GL_BLEND)
#
        side = self.dragResizeFace & 1
        dragdim = self.dragResizeFace >> 1
        box = self.selectionBox()

        o, m = list(box.origin), list(box.maximum)
        (m, o)[side][dragdim] = int(numpy.floor(point[dragdim] + 0.5))
        m = map(lambda a: a - 1, m)
        return o, m

    def option1(self):
        self.selectOtherCorner()

    _currentCorner = 0

    @property
    def currentCorner(self):
        return self._currentCorner

    @currentCorner.setter
    def currentCorner(self, value):
        self._currentCorner = value & 1
        self.toolIconName = ("selection", "selection2")[self._currentCorner]
        self.editor.toolbar.toolTextureChanged()

    def selectOtherCorner(self):
        self.currentCorner = 1 - self.currentCorner

    showPreviousSelection = SelectSettings.showPreviousSelection.configProperty()
    alpha = 0.25

    def drawToolMarkers(self):

        selectionBox = self.selectionBox()
        if(selectionBox):
            widg = self.editor.find_widget(pygame.mouse.get_pos())

            # these corners stay even while using the chunk tool.
            GL.glPolygonOffset(DepthOffset.SelectionCorners, DepthOffset.SelectionCorners)
            lineWidth = 3
            for t, c, n in ((self.bottomLeftPoint, self.bottomLeftColor, self.bottomLeftNudge), (self.topRightPoint, self.topRightColor, self.topRightNudge)):
                if t != None:
                    (sx, sy, sz) = t
                    if self.selectionInProgress:
                        if t == self.getSelectionPoint(self.currentCorner):
                            blockFace = self.editor.blockFaceUnderCursor
                            if blockFace:
                                p, d = blockFace
                                (sx, sy, sz) = p
                        else:
                            sx, sy, sz = self.dragStartPoint

                    # draw a blue or yellow wireframe box at the selection corner
                    r, g, b = c
                    alpha = 0.4
                    try:
                        bt = self.editor.level.blockAt(sx, sy, sz)
                        if(bt):
                            alpha = 0.2
                    except pymclevel.ChunkNotPresent:
                        pass

                    GL.glLineWidth(lineWidth)
                    lineWidth += 1

                    # draw highlighted block faces when nudging
                    if (widg.parent == n or widg == n):
                        GL.glEnable(GL.GL_BLEND)
                        # drawCube(BoundingBox((sx, sy, sz), (1,1,1)))
                        nudgefaces = numpy.array([
                               selectionBox.minx, selectionBox.miny, selectionBox.minz,
                               selectionBox.minx, selectionBox.maxy, selectionBox.minz,
                               selectionBox.minx, selectionBox.maxy, selectionBox.maxz,
                               selectionBox.minx, selectionBox.miny, selectionBox.maxz,
                               selectionBox.minx, selectionBox.miny, selectionBox.minz,
                               selectionBox.maxx, selectionBox.miny, selectionBox.minz,
                               selectionBox.maxx, selectionBox.miny, selectionBox.maxz,
                               selectionBox.minx, selectionBox.miny, selectionBox.maxz,
                               selectionBox.minx, selectionBox.miny, selectionBox.minz,
                               selectionBox.minx, selectionBox.maxy, selectionBox.minz,
                               selectionBox.maxx, selectionBox.maxy, selectionBox.minz,
                               selectionBox.maxx, selectionBox.miny, selectionBox.minz,
                               ], dtype='float32')

                        if sx != selectionBox.minx:
                            nudgefaces[0:12:3] = selectionBox.maxx
                        if sy != selectionBox.miny:
                            nudgefaces[13:24:3] = selectionBox.maxy
                        if sz != selectionBox.minz:
                            nudgefaces[26:36:3] = selectionBox.maxz

                        GL.glColor(r, g, b, 0.3)
                        GL.glVertexPointer(3, GL.GL_FLOAT, 0, nudgefaces)
                        GL.glEnable(GL.GL_DEPTH_TEST)
                        GL.glDrawArrays(GL.GL_QUADS, 0, 12)
                        GL.glDisable(GL.GL_DEPTH_TEST)

                        GL.glDisable(GL.GL_BLEND)

                    GL.glColor(r, g, b, alpha)
                    drawCube(BoundingBox((sx, sy, sz), (1, 1, 1)), GL.GL_LINE_STRIP)

            if not (not self.showPreviousSelection and self.selectionInProgress):
                # draw the current selection as a white box.  hangs around when you use other tools.
                GL.glPolygonOffset(DepthOffset.Selection, DepthOffset.Selection)
                color = self.selectionColor + (self.alpha,)
                if self.dragResizeFace is not None:
                    box = self.draggingSelectionBox()
                else:
                    box = selectionBox

                if self.panel and (widg is self.panel.nudgeBlocksButton or widg.parent is self.panel.nudgeBlocksButton):
                    color = (0.3, 1.0, 0.3, self.alpha)
                self.editor.drawConstructionCube(box, color)

                # highlight the face under the cursor, or the face being dragged
                if self.dragResizeFace is None:
                    if self.selectionInProgress or self.clickSelectionInProgress:
                        pass
                    else:
                        face, point = self.boxFaceUnderCursor(box)

                        if face is not None:
                            GL.glEnable(GL.GL_BLEND)
                            GL.glColor(*color)

                            # Shrink the highlighted face to show the click-through edges

                            offs = [s * self.edge_factor for s in box.size]
                            offs[face >> 1] = 0
                            origin = [o + off for o, off in zip(box.origin, offs)]
                            size = [s - off * 2 for s, off in zip(box.size, offs)]

                            cv = self.editor.mainViewport.cameraVector
                            for i in range(3):
                                if cv[i] > 0:
                                    origin[i] -= offs[i]
                                    size[i] += offs[i]
                                else:
                                    size[i] += offs[i]

                            smallbox = FloatBox(origin, size)

                            drawFace(smallbox, face)

                            GL.glColor(0.9, 0.6, 0.2, 0.8)
                            GL.glLineWidth(2.0)
                            drawFace(box, face, type=GL.GL_LINE_STRIP)
                            GL.glDisable(GL.GL_BLEND)
                else:
                    face = self.dragResizeFace
                    point = self.dragResizePoint()
                    dim = face >> 1
                    pos = point[dim]

                    side = face & 1
                    o, m = selectionBox.origin, selectionBox.maximum
                    otherFacePos = (m, o)[side ^ 1][dim]  # ugly
                    direction = (-1, 1)[side]
                    # print "pos", pos, "otherFace", otherFacePos, "dir", direction
                    # print "m", (pos - otherFacePos) * direction
                    if (pos - otherFacePos) * direction > 0:
                        face ^= 1

                    GL.glColor(0.9, 0.6, 0.2, 0.5)
                    drawFace(box, face, type=GL.GL_LINE_STRIP)
                    GL.glEnable(GL.GL_BLEND)
                    GL.glEnable(GL.GL_DEPTH_TEST)

                    drawFace(box, face)
                    GL.glDisable(GL.GL_BLEND)
                    GL.glDisable(GL.GL_DEPTH_TEST)

        selectionColor = map(lambda a: a * a * a * a, self.selectionColor)

        # draw a colored box representing the possible selection
        otherCorner = self.dragStartPoint
        if self.dragResizeFace is not None:
            self.showPanel()  # xxx do this every frame while dragging because our UI kit is bad

        if ((self.selectionInProgress or self.clickSelectionInProgress) and otherCorner != None):
            GL.glPolygonOffset(DepthOffset.PotentialSelection, DepthOffset.PotentialSelection)

            pos, direction = self.editor.blockFaceUnderCursor
            if pos is not None:
                box = self.selectionBoxForCorners(otherCorner, pos)
                if self.chunkMode:
                    box = box.chunkBox(self.editor.level)
                    if pygame.key.get_mods() & pygame.KMOD_ALT:
                        selectionColor = [1., 0., 0.]
                self.editor.drawConstructionCube(box, selectionColor + [self.alpha, ])
        else:
            # don't draw anything at the mouse cursor if we're resizing the box
            if self.dragResizeFace is None:
                box = self.selectionBox()
                if box:
                    face, point = self.boxFaceUnderCursor(box)
                    if face is not None:
                        return
            else:
                return

    def drawToolReticle(self):
        GL.glPolygonOffset(DepthOffset.SelectionReticle, DepthOffset.SelectionReticle)
        pos, direction = self.editor.blockFaceUnderCursor

        # draw a selection-colored box for the cursor reticle
        selectionColor = map(lambda a: a * a * a * a, self.selectionColor)
        r, g, b = selectionColor
        alpha = 0.3

        try:
            bt = self.editor.level.blockAt(*pos)
            if(bt):
##                textureCoords = materials[bt][0]
                alpha = 0.12
        except pymclevel.ChunkNotPresent:
            pass

        # cube sides
        GL.glColor(r, g, b, alpha)
        GL.glDepthMask(False)
        GL.glEnable(GL.GL_BLEND)
        GL.glEnable(GL.GL_DEPTH_TEST)
        drawCube(BoundingBox(pos, (1, 1, 1)))
        GL.glDepthMask(True)
        GL.glDisable(GL.GL_DEPTH_TEST)

        drawTerrainCuttingWire(BoundingBox(pos, (1, 1, 1)),
                               (r, g, b, 0.4),
                               (1., 1., 1., 1.0)
                               )

        GL.glDisable(GL.GL_BLEND)

    def setSelection(self, box):
        if box is None:
            self.selectNone()
        else:
            self.setSelectionPoints(self.selectionPointsFromBox(box))

    def selectionPointsFromBox(self, box):
        return (box.origin, map(lambda x: x - 1, box.maximum))

    def selectNone(self):
        self.setSelectionPoints(None)

    def selectAll(self):
        box = self.editor.level.bounds
        op = SelectionOperation(self, self.selectionPointsFromBox(box))
        self.performWithRetry(op)
        self.editor.addOperation(op)

    def deselect(self):
        op = SelectionOperation(self, None)
        self.performWithRetry(op)
        self.editor.addOperation(op)

    def setSelectionPoint(self, pointNumber, newPoint):
        points = self.getSelectionPoints()
        points[pointNumber] = newPoint
        self.setSelectionPoints(points)

    def setSelectionPoints(self, points):
        if points:
            self.bottomLeftPoint, self.topRightPoint = [Vector(*p) if p else None for p in points]
        else:
            self.bottomLeftPoint = self.topRightPoint = None

        self._selectionChanged()
        self.editor.selectionChanged()

    def _selectionChanged(self):
        if self.selectionBox():
            self.showPanel()
        else:
            self.hidePanel()
            self.hideNudgePanel()

    def getSelectionPoint(self, pointNumber):
        return (self.bottomLeftPoint, self.topRightPoint)[pointNumber]  # lisp programmers think this doesn't evaluate 'self.topRightPoint' - lol!

    def getSelectionPoints(self):
        return [self.bottomLeftPoint, self.topRightPoint]

    @alertException
    def deleteBlocks(self):
        box = self.selectionBox()
        if None is box:
            return
        if box == box.chunkBox(self.editor.level):
            resp = ask("You are deleting a chunk-shaped selection. Fill the selection with Air, or delete the chunks themselves?", responses=["Fill with Air", "Delete Chunks", "Cancel"])
            if resp == "Delete Chunks":
                self.editor.toolbar.tools[8].destroyChunks(box.chunkPositions)
            elif resp == "Fill with Air":
                self._deleteBlocks()
        else:
            self._deleteBlocks()

    def _deleteBlocks(self, recordUndo=True):
        box = self.selectionBox()
        if None is box:
            return
        op = BlockFillOperation(self.editor, self.editor.level, box, self.editor.level.materials.Air, [])
        with setWindowCaption("DELETING - "):
            self.editor.freezeStatus("Deleting {0} blocks".format(box.volume))
            self.performWithRetry(op, recordUndo)

            self.editor.addOperation(op)
            self.editor.invalidateBox(box)
            self.editor.addUnsavedEdit()

    @alertException
    def deleteEntities(self, recordUndo=True):
        box = self.selectionBox()

        with setWindowCaption("WORKING - "):
            self.editor.freezeStatus("Removing entities...")
            level = self.editor.level
            editor = self.editor

            class DeleteEntitiesOperation(Operation):
                def perform(self, recordUndo=True):
                    self.undoEntities = level.getEntitiesInBox(box)
                    level.removeEntitiesInBox(box)
                    editor.renderer.invalidateEntitiesInBox(box)

                def undo(self):
                    level.removeEntitiesInBox(box)
                    level.addEntities(self.undoEntities)
                    editor.renderer.invalidateEntitiesInBox(box)

            op = DeleteEntitiesOperation(self.editor, self.editor.level)
            self.performWithRetry(op, recordUndo)
            if recordUndo:
                self.editor.addOperation(op)
            self.editor.addUnsavedEdit()

    @alertException
    def analyzeSelection(self):
        box = self.selectionBox()
        self.editor.analyzeBox(self.editor.level, box)

    @alertException
    def cutSelection(self):
        self.copySelection()
        self.deleteBlocks()
        self.deleteEntities(False)

    @alertException
    def copySelection(self):
        schematic = self._copySelection()
        if schematic:
            self.editor.addCopiedSchematic(schematic)

    def _copySelection(self):
        box = self.selectionBox()
        if not box:
            return

        shape = box.size

        self.editor.mouseLookOff()

        print "Clipping: ", shape

        fileFormat = "schematic"
        if box.volume > self.maxBlocks:
            fileFormat = "schematic.zip"

        if fileFormat == "schematic.zip":
            missingChunks = filter(lambda x: not self.editor.level.containsChunk(*x), box.chunkPositions)
            if len(missingChunks):
                if not ((box.origin[0] & 0xf == 0) and (box.origin[2] & 0xf == 0)):
                    if ask("This is an uneven selection with missing chunks. Expand the selection to chunk edges, or copy air within the missing chunks?", ["Expand Selection", "Copy Air"]) == "Expand Selection":
                        self.selectChunks()
                        box = self.selectionBox()

        with setWindowCaption("Copying - "):
            filename = tempfile.mkdtemp(".zip", "mceditcopy")
            os.rmdir(filename)

            status = "Copying {0:n} blocks...".format(box.volume)
            if fileFormat == "schematic":
                schematic = showProgress(status,
                            self.editor.level.extractSchematicIter(box), cancel=True)
            else:
                schematic = showProgress(status,
                            self.editor.level.extractZipSchematicIter(box, filename), cancel=True)
            if schematic == "Canceled":
                return None

            return schematic

    @alertException
    def exportSelection(self):
        schematic = self._copySelection()
        if schematic:
            self.editor.exportSchematic(schematic)


class SelectionOperation(Operation):
    changedLevel = False

    def __init__(self, selectionTool, points):
        super(SelectionOperation, self).__init__(selectionTool.editor, selectionTool.editor.level)
        self.selectionTool = selectionTool
        self.points = points

    def perform(self, recordUndo=True):
        self.undoPoints = self.selectionTool.getSelectionPoints()
        self.selectionTool.setSelectionPoints(self.points)

    def undo(self):
        points = self.points
        self.points = self.undoPoints
        self.perform()
        self.points = points


class NudgeSelectionOperation(Operation):
    changedLevel = False

    def __init__(self, selectionTool, direction):
        super(NudgeSelectionOperation, self).__init__(selectionTool.editor, selectionTool.editor.level)
        self.selectionTool = selectionTool
        self.direction = direction
        self.oldPoints = selectionTool.getSelectionPoints()
        self.newPoints = [p + direction for p in self.oldPoints]

    def perform(self, recordUndo=True):
        self.selectionTool.setSelectionPoints(self.newPoints)

    oldSelection = None

    def undo(self):
        self.selectionTool.setSelectionPoints(self.oldPoints)
