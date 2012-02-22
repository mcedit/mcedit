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
import urllib
from pymclevel.box import FloatBox


class PlayerMoveOperation(Operation):
    undoPos = None
    def __init__(self, tool, pos, player="Player", yp = (None, None)):
        self.tool, self.pos = tool, pos
        self.yp = yp
        self.player = player

    def perform(self, recordUndo=True):
        try:
            level = self.tool.editor.level
            try:
                self.undoPos = level.getPlayerPosition(self.player)
                self.undoDim = level.getPlayerDimension(self.player)
                self.undoYP = level.getPlayerOrientation(self.player)
            except Exception, e:
                info("Couldn't get player position! ({0!r})".format(e))

            yaw, pitch = self.yp
            if yaw is not None and pitch is not None:
                level.setPlayerOrientation((yaw, pitch), self.player)
            level.setPlayerPosition(self.pos, self.player)
            level.setPlayerDimension(level.dimNo, self.player)
            self.tool.markerList.invalidate()

        except PlayerNotFound, e:
            print "Player move failed: ", e

    def undo(self):
        if not (self.undoPos is None):
            level = self.tool.editor.level
            level.setPlayerPosition(self.undoPos, self.player)
            level.setPlayerDimension(self.undoDim, self.player)
            level.setPlayerOrientation(self.undoYP, self.player)
            self.tool.markerList.invalidate()

    def bufferSize(self):
        return 20


class SpawnPositionInvalid(Exception):
    pass


def okayAt63(level, pos):
    """blocks 63 or 64 must be occupied"""
    return level.blockAt(pos[0], 63, pos[2]) != 0 or level.blockAt(pos[0], 64, pos[2]) != 0


def okayAboveSpawn(level, pos):
    """3 blocks above spawn must be open"""
    return not any( [level.blockAt(pos[0], pos[1]+i, pos[2]) for i in range(1, 4)] )


def positionValid(level, pos):
    return okayAt63(level, pos) and okayAboveSpawn(level, pos)


class PlayerSpawnMoveOperation(PlayerMoveOperation):
    def perform(self, recordUndo=True):
        level = self.tool.editor.level
        if isinstance(level, MCInfdevOldLevel):
            if not positionValid(level, self.pos):
                if SpawnSettings.spawnProtection.get():
                    raise SpawnPositionInvalid("You cannot have two air blocks at Y=63 and Y=64 in your spawn point's column. Additionally, you cannot have a solid block in the three blocks above your spawn point. It's weird, I know.")

        self.undoPos = level.playerSpawnPosition()
        level.setPlayerSpawnPosition(self.pos)

        self.tool.markerList.invalidate()


class PlayerPositionPanel(Panel):
    def __init__(self, tool):
        Panel.__init__(self)
        self.tool = tool
        level = tool.editor.level
        if hasattr(level, 'players'):
            players = level.players or ["[No players]"]
        else:
            players = ["Player"]
        self.players = players
        tableview = TableView(columns=[
            TableColumn("Player Name", 200),
        ])
        tableview.index = 0
        tableview.num_rows = lambda: len(players)
        tableview.row_data = lambda i: (players[i],)
        tableview.row_is_selected = lambda x: x==tableview.index
        tableview.zebra_color = (0,0,0,48)
        def selectTableRow(i, evt):
            tableview.index = i

        tableview.click_row = selectTableRow
        self.table = tableview
        l = Label("Player: ")
        col = [l, tableview]

        gotoButton = Button("Goto Player", action=self.tool.gotoPlayer)
        gotoCameraButton = Button("Goto Player's View", action=self.tool.gotoPlayerCamera)
        moveButton = Button("Move Player", action=self.tool.movePlayer)
        moveToCameraButton = Button("Align Player to Camera", action=self.tool.movePlayerToCamera)
        col.extend([gotoButton, gotoCameraButton, moveButton, moveToCameraButton])

        col = Column(col)
        self.add(col)
        self.shrink_wrap()

    @property
    def selectedPlayer(self):
        return self.players[self.table.index]


class PlayerPositionTool(EditorTool):
    surfaceBuild = True
    toolIconName = "player"
    tooltipText = "Move Player"
    movingPlayer = None

    def reloadTextures(self):
        self.charTex = loadPNGTexture('char.png')

    @alertException
    def movePlayer(self):
        self.movingPlayer = self.panel.selectedPlayer

    @alertException
    def movePlayerToCamera(self):
        player = self.panel.selectedPlayer
        pos = self.editor.mainViewport.cameraPosition
        y = self.editor.mainViewport.yaw
        p = self.editor.mainViewport.pitch
        d = self.editor.level.dimNo

        op = PlayerMoveOperation(self, pos, player, (y,p))
        self.movingPlayer = None
        op.perform()
        self.editor.addOperation(op)
        self.editor.addUnsavedEdit()

    def gotoPlayerCamera(self):
        player = self.panel.selectedPlayer
        try:
            pos = self.editor.level.getPlayerPosition(player)
            y, p = self.editor.level.getPlayerOrientation(player)
            self.editor.gotoDimension(self.editor.level.getPlayerDimension(player))

            self.editor.mainViewport.cameraPosition = pos
            self.editor.mainViewport.yaw = y
            self.editor.mainViewport.pitch = p
            self.editor.mainViewport.stopMoving()
            self.editor.mainViewport.invalidate()
        except PlayerNotFound:
            pass;

    def gotoPlayer(self):
        player = self.panel.selectedPlayer

        try:
            if self.editor.mainViewport.pitch < 0:
                self.editor.mainViewport.pitch = -self.editor.mainViewport.pitch
                self.editor.mainViewport.cameraVector = self.editor.mainViewport._cameraVector()
            cv = self.editor.mainViewport.cameraVector

            pos = self.editor.level.getPlayerPosition(player)
            pos = map(lambda p, c:p - c * 5, pos, cv)
            self.editor.gotoDimension(self.editor.level.getPlayerDimension(player))

            self.editor.mainViewport.cameraPosition = pos
            self.editor.mainViewport.stopMoving()
        except PlayerNotFound:
            pass;

    def __init__(self, *args):
        EditorTool.__init__(self, *args)
        self.reloadTextures()

        textureVertices = numpy.array(
            (
                24, 16,
                24, 8,
                32, 8,
                32, 16,

                8, 16,
                8, 8,
                16, 8,
                16, 16,

                24, 0,
                16, 0,
                16, 8,
                24, 8,

                16, 0,
                16, 8,
                8, 8,
                8, 0,

                8, 8,
                0, 8,
                0, 16,
                8, 16,

                16, 16,
                24, 16,
                24, 8,
                16, 8,

            ), dtype='f4')

        textureVertices.shape = (24, 2)

        textureVertices *= 4
        textureVertices[:, 1] *= 2

        self.texVerts = textureVertices

        self.markerList = DisplayList()

    panel = None
    def showPanel(self):
        if not self.panel:
            self.panel = PlayerPositionPanel(self)

        self.panel.left = self.editor.left
        self.panel.centery = self.editor.centery

        self.editor.add(self.panel)

    def hidePanel(self):
        if self.panel and self.panel.parent:
            self.panel.parent.remove(self.panel)
        self.panel = None

    def drawToolReticle(self):
        if self.movingPlayer is None: return

        pos, direction = self.editor.blockFaceUnderCursor
        pos = (pos[0], pos[1] + 2, pos[2])

        x, y, z = pos

        #x,y,z=map(lambda p,d:p+d, pos, direction)
        glEnable(GL_BLEND)
        glColor(1.0, 1.0, 1.0, 0.5)
        self.drawCharacterHead(x + 0.5, y + 0.75, z + 0.5)
        glDisable(GL_BLEND)

        glEnable(GL_DEPTH_TEST)
        self.drawCharacterHead(x + 0.5, y + 0.75, z + 0.5)
        drawTerrainCuttingWire(BoundingBox((x, y, z), (1, 1, 1)))
        drawTerrainCuttingWire(BoundingBox((x, y - 1, z), (1, 1, 1)))
        #drawTerrainCuttingWire( BoundingBox((x,y-2,z), (1,1,1)) )
        glDisable(GL_DEPTH_TEST)

    markerLevel = None

    def drawToolMarkers(self):
        if self.markerLevel != self.editor.level:
            self.markerList.invalidate()
            self.markerLevel = self.editor.level
        self.markerList.call(self._drawToolMarkers)

    def _drawToolMarkers(self):
        glColor(1.0, 1.0, 1.0, 0.5)

        glEnable(GL_DEPTH_TEST)
        glMatrixMode(GL_MODELVIEW)

        for player in self.editor.level.players:
            try:
                pos = self.editor.level.getPlayerPosition(player)
                yaw,pitch = self.editor.level.getPlayerOrientation(player)
                dim = self.editor.level.getPlayerDimension(player)
                if dim != self.editor.level.dimNo: continue;
                x, y, z = pos
                glPushMatrix()
                glTranslate(x, y, z)
                glRotate(-yaw, 0, 1, 0)
                glRotate(pitch, 1, 0, 0)
                glColor(1, 1, 1, 1)
                self.drawCharacterHead(0, 0, 0)
                glPopMatrix()
                #glEnable(GL_BLEND)
                drawTerrainCuttingWire(FloatBox((x-.5, y-.5, z-.5), (1,1,1)),
                                       c0=(0.3, 0.9, 0.7, 1.0),
                                       c1=(0,0,0,0),
                                       )

                #glDisable(GL_BLEND)

            except Exception, e:
                print repr(e)
                continue

        glDisable(GL_DEPTH_TEST)

    def drawCharacterHead(self, x, y, z):
        glEnable(GL_CULL_FACE)
        box = FloatBox()
        box.origin = (x - 0.25, y - 0.25, z - 0.25)
        box.size = (0.5, 0.5, 0.5)

        drawCube(box,
                 texture=self.charTex, textureVertices=self.texVerts)
        glDisable(GL_CULL_FACE)

    @property
    def statusText(self):
        if not self.panel: return ""
        player = self.panel.selectedPlayer
        if player == "Player":
            return "Click to move the player"

        return "Click to move the player \"{0}\"".format(player)

    @alertException
    def mouseDown(self, evt, pos, direction):
        if self.movingPlayer is None: return

        pos = (pos[0] + 0.5, pos[1] + 2.75, pos[2] + 0.5)

        op = PlayerMoveOperation(self, pos, self.movingPlayer)
        self.movingPlayer = None
        op.perform()
        self.editor.addOperation(op)
        self.editor.addUnsavedEdit()

    def levelChanged(self):
        self.markerList.invalidate()

    @alertException
    def toolSelected(self):
        self.showPanel()
        self.movingPlayer = None

    @alertException
    def toolReselected(self):
        if self.panel:
            self.gotoPlayer()


class PlayerSpawnPositionOptions(ToolOptions):
    def __init__(self, tool):
        Panel.__init__(self)
        self.tool = tool
        self.spawnProtectionCheckBox = CheckBox(ref=AttrRef(tool, "spawnProtection"))
        self.spawnProtectionLabel = Label("Spawn Position Safety")
        self.spawnProtectionLabel.mouse_down = self.spawnProtectionCheckBox.mouse_down

        tooltipText = "Minecraft will randomly move your spawn point if you try to respawn in a column where there are no blocks at Y=63 and Y=64. Only uncheck this box if Minecraft is changed."
        self.spawnProtectionLabel.tooltipText = self.spawnProtectionCheckBox.tooltipText = tooltipText

        row = Row((self.spawnProtectionCheckBox, self.spawnProtectionLabel))
        col = Column((Label("Spawn Point Options"), row, Button("OK", action=self.dismiss)))

        self.add(col)
        self.shrink_wrap()

SpawnSettings = config.Settings("Spawn")
SpawnSettings.spawnProtection = SpawnSettings("Spawn Protection", True)


class PlayerSpawnPositionTool(PlayerPositionTool):
    surfaceBuild = True
    toolIconName = "playerspawn"
    tooltipText = "Move Spawn Point"

    def __init__(self, *args):
        PlayerPositionTool.__init__(self, *args)
        self.optionsPanel = PlayerSpawnPositionOptions(self)

    def toolEnabled(self):
        return self.editor.level.dimNo == 0
    def showPanel(self):
        self.panel = Panel()
        button = Button("Goto Spawn", action=self.gotoSpawn)
        self.panel.add(button)
        self.panel.shrink_wrap()

        self.panel.left = self.editor.left
        self.panel.centery = self.editor.centery
        self.editor.add(self.panel)

    def gotoSpawn(self):
        cv = self.editor.mainViewport.cameraVector

        pos = self.editor.level.playerSpawnPosition()
        pos = map(lambda p, c:p - c * 5, pos, cv)

        self.editor.mainViewport.cameraPosition = pos
        self.editor.mainViewport.stopMoving()

    @property
    def statusText(self):
        return "Click to set the spawn position."

    spawnProtection = SpawnSettings.spawnProtection.configProperty()

    def drawToolReticle(self):
        pos, direction = self.editor.blockFaceUnderCursor
        x, y, z = map(lambda p, d:p + d, pos, direction)

        color = (1.0, 1.0, 1.0, 0.5)
        if isinstance(self.editor.level, MCInfdevOldLevel) and self.spawnProtection:
            if not positionValid(self.editor.level, (x,y,z)):
                color = (1.0, 0.0, 0.0, 0.5)

        glColor(*color)
        glEnable(GL_BLEND)
        self.drawCage(x, y, z)
        self.drawCharacterHead(x + 0.5, y + 0.5, z + 0.5)
        glDisable(GL_BLEND)

        glEnable(GL_DEPTH_TEST)
        self.drawCage(x, y, z)
        self.drawCharacterHead(x + 0.5, y + 0.5, z + 0.5)
        color2 = map(lambda a:a * 0.4, color)
        drawTerrainCuttingWire(BoundingBox((x, y, z), (1, 1, 1)), color2, color)
        glDisable(GL_DEPTH_TEST)

    def _drawToolMarkers(self):
        x, y, z = self.editor.level.playerSpawnPosition()
        glColor(1.0, 1.0, 1.0, 1.0)
        glEnable(GL_DEPTH_TEST)
        self.drawCage(x, y, z)
        self.drawCharacterHead(x + 0.5, y + 0.5 + 0.125 * sin(self.editor.frames * 0.05), z + 0.5)
        glDisable(GL_DEPTH_TEST)

    def drawCage(self, x, y, z):
        cageTexVerts = MCInfdevOldLevel.materials.blockTextures[52, 0]
        cageTexVerts = array([((tx, ty), (tx + 16, ty), (tx + 16, ty + 16), (tx, ty + 16)) for (tx, ty) in cageTexVerts], dtype='float32')
        glEnable(GL_ALPHA_TEST)

        drawCube(BoundingBox((x, y, z), (1, 1, 1)), texture=alphaMaterials.terrainTexture, textureVertices=cageTexVerts)
        glDisable(GL_ALPHA_TEST)

    @alertException
    def mouseDown(self, evt, pos, direction):
        pos = map(lambda p, d:p + d, pos, direction)
        op = PlayerSpawnMoveOperation(self, pos)
        try:
            op.perform()

            self.editor.addOperation(op)
            self.editor.addUnsavedEdit()
            self.markerList.invalidate()

        except SpawnPositionInvalid, e:
            if "Okay" != ask(str(e), responses=["Okay", "Fix it for me!"]):
                level = self.editor.level
                status = ""
                if not okayAt63(level, pos):
                    level.setBlockAt(pos[0], 63, pos[2], 1)
                    status += "Block added at y=63.\n"

                if 59 < pos[1] < 63:
                    pos[1] = 63
                    status += "Spawn point moved upward to y=63.\n"

                if not okayAboveSpawn(level, pos):
                    if pos[1] > 63 or pos[1] < 59:
                        lpos = (pos[0], pos[1]-1, pos[2])
                        if level.blockAt(*pos) == 0 and level.blockAt(*lpos) != 0 and okayAboveSpawn(level, lpos):
                            pos = lpos
                            status += "Spawn point shifted down by one block.\n"
                    if not okayAboveSpawn(level, pos):
                        for i in range(1,4):
                            level.setBlockAt(pos[0], pos[1]+i, pos[2], 0)

                            status += "Blocks above spawn point cleared.\n"

                self.editor.invalidateChunks([(pos[0] // 16, pos[2] // 16)])
                op = PlayerSpawnMoveOperation(self, pos)
                try:
                    op.perform()
                except SpawnPositionInvalid, e:
                    alert(str(e))
                    return

                self.editor.addOperation(op)
                self.editor.addUnsavedEdit()
                self.markerList.invalidate()
                if len(status):
                    alert("Spawn point fixed. Changes: \n\n" + status)
    @alertException
    def toolReselected(self):
        self.gotoSpawn()
