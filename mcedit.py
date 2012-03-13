#!/usr/bin/env python
# -*- coding: utf8 -*_
"""
mcedit.py

Startup, main menu, keyboard configuration, automatic updating.
"""
import os
import os.path
import sys
import config
import shutil
import functools
import traceback
import logging

import pygame
from pygame.constants import *
from pygame import key, display, rect

from albow.openglwidgets import GLViewport
from albow.root import RootWidget
from albow.dialogs import Dialog
from albow import *
from glbackground import Panel

from OpenGL import GL
from numpy import *

from pymclevel.mclevel import MCInfdevOldLevel, saveFileDir
from pymclevel.materials import *
MCInfdevOldLevel.loadedChunkLimit = 0

from release import release

import leveleditor
import mcplatform
from mceutils import *
from mcplatform import platform_open
from leveleditor import Settings, ControlSettings

ESCAPE = '\033'


class FileOpener(Widget):
    is_gl_container = True

    def __init__(self, mcedit, *args, **kwargs):
        kwargs['rect'] = mcedit.rect
        Widget.__init__(self, *args, **kwargs)
        self.anchor = 'tlbr'
        self.mcedit = mcedit

        helpColumn = []

        label = Label("{0} {1} {2} {3} {4} {5}".format(
            config.config.get('Keys', 'Forward'),
            config.config.get('Keys', 'Left'),
            config.config.get('Keys', 'Back'),
            config.config.get('Keys', 'Right'),
            config.config.get('Keys', 'Up'),
            config.config.get('Keys', 'Down'),
        ).upper() + " to move")
        label.anchor = 'whrt'
        label.align = 'r'
        helpColumn.append(label)

        def addHelp(text):
            label = Label(text)
            label.anchor = 'whrt'
            label.align = "r"
            helpColumn.append(label)

        addHelp("{0}".format(config.config.get('Keys', 'Brake').upper()) + " to slow down")
        addHelp("Right-click to toggle camera control")
        addHelp("Mousewheel to control tool distance")
        addHelp("Hold SHIFT to move along a major axis")
        addHelp("Hold ALT for details")

        helpColumn = Column(helpColumn, align="r")
        helpColumn.topright = self.topright
        helpColumn.anchor = "whrt"
        #helpColumn.is_gl_container = True
        self.add(helpColumn)

        keysColumn = [Label("")]
        buttonsColumn = [leveleditor.ControlPanel.getHeader()]

        shortnames = []
        for world in self.mcedit.recentWorlds():
            shortname = os.path.basename(world)
            try:
                if MCInfdevOldLevel.isLevel(world):
                    lev = MCInfdevOldLevel(world)
                    shortname = lev.LevelName
                    if lev.LevelName != lev.displayName:
                        shortname = u"{0} ({1})".format(lev.LevelName, lev.displayName)
            except Exception, e:
                logging.warning(
                    'Couldn\'t get name from recent world: {0!r}'.format(e))

            if shortname == "level.dat":
                shortname = os.path.basename(os.path.dirname(world))

            if len(shortname) > 40:
                shortname = shortname[:37] + "..."
            shortnames.append(shortname)

        hotkeys = ([('N', 'Create New World', self.createNewWorld),
            ('L', 'Load World...', self.mcedit.editor.askLoadWorld),
            ('O', 'Open a level...', self.promptOpenAndLoad)] + [
            ('F{0}'.format(i + 1), shortnames[i], self.createLoadButtonHandler(world))
            for i, world in enumerate(self.mcedit.recentWorlds())])

        commandRow = HotkeyColumn(hotkeys, keysColumn, buttonsColumn)
        commandRow.anchor = 'lrh'

        sideColumn = mcedit.makeSideColumn()
        sideColumn.anchor = 'wh'

        contentRow = Row((commandRow, sideColumn))
        contentRow.center = self.center
        contentRow.anchor = "rh"
        self.add(contentRow)
        self.sideColumn = sideColumn

    def gl_draw_self(self, root, offset):
        #self.mcedit.editor.mainViewport.setPerspective();
        self.mcedit.editor.drawStars()

    def idleevent(self, evt):
        self.mcedit.editor.doWorkUnit()
        #self.invalidate()

    def key_down(self, evt):
        keyname = key.name(evt.key)
        if keyname == 'f4' and (key.get_mods() & (KMOD_ALT | KMOD_LALT | KMOD_RALT)):
            raise SystemExit
        if keyname in ('f1', 'f2', 'f3', 'f4', 'f5'):
            self.mcedit.loadRecentWorldNumber(int(keyname[1]))
        if keyname is "o":
            self.promptOpenAndLoad()
        if keyname is "n":
            self.createNewWorld()
        if keyname is "l":
            self.mcedit.editor.askLoadWorld()

    def promptOpenAndLoad(self):
        try:
            filename = mcplatform.askOpenFile()
            if filename:
                self.mcedit.loadFile(filename)
        except Exception, e:
            logging.error('Error during proptOpenAndLoad: {0!r}'.format(e))

    def createNewWorld(self):
        self.parent.createNewWorld()

    def createLoadButtonHandler(self, filename):
        return lambda: self.mcedit.loadFile(filename)


class KeyConfigPanel(Dialog):
    keyConfigKeys = [
        "<Movement Controls>",
        "Forward",
        "Back",
        "Left",
        "Right",
        "Up",
        "Down",
        "Brake",
        "",
        "<Camera Controls>",
        "Pan Left",
        "Pan Right",
        "Pan Up",
        "Pan Down",
        "",
        "<Tool Controls>",
        "Rotate",
        "Roll",
        "Flip",
        "Mirror",
        "Swap",
        "Increase Reach",
        "Decrease Reach",
        "Reset Reach",
    ]

    presets = {"WASD": [
        ("Forward", "w"),
        ("Back", "s"),
        ("Left", "a"),
        ("Right", "d"),
        ("Up", "q"),
        ("Down", "z"),
        ("Brake", "space"),

        ("Rotate", "e"),
        ("Roll", "r"),
        ("Flip", "f"),
        ("Mirror", "g"),
        ("Swap", "x"),
        ("Increase Reach", "mouse4"),
        ("Decrease Reach", "mouse5"),
        ("Reset Reach", "mouse3"),
    ],
    "Arrows": [
        ("Forward", "up"),
        ("Back", "down"),
        ("Left", "left"),
        ("Right", "right"),
        ("Up", "page up"),
        ("Down", "page down"),
        ("Brake", "space"),

        ("Rotate", "home"),
        ("Roll", "end"),
        ("Flip", "insert"),
        ("Mirror", "delete"),
        ("Swap", "\\"),
        ("Increase Reach", "mouse4"),
        ("Decrease Reach", "mouse5"),
        ("Reset Reach", "mouse3"),
    ],
    "Numpad": [
        ("Forward", "[8]"),
        ("Back", "[5]"),
        ("Left", "[4]"),
        ("Right", "[6]"),
        ("Up", "[9]"),
        ("Down", "[3]"),
        ("Brake", "[0]"),

        ("Rotate", "[-]"),
        ("Roll", "[+]"),
        ("Flip", "[/]"),
        ("Mirror", "[*]"),
        ("Swap", "[.]"),
        ("Increase Reach", "mouse4"),
        ("Decrease Reach", "mouse5"),
        ("Reset Reach", "mouse3"),
    ]}

    selectedKeyIndex = 0

    def __init__(self):
        Dialog.__init__(self)
        keyConfigTable = TableView(columns=[TableColumn("Command", 400, "l"), TableColumn("Assigned Key", 150, "r")])
        keyConfigTable.num_rows = lambda: len(self.keyConfigKeys)
        keyConfigTable.row_data = self.getRowData
        keyConfigTable.row_is_selected = lambda x: x == self.selectedKeyIndex
        keyConfigTable.click_row = self.selectTableRow
        tableWidget = Widget()
        tableWidget.add(keyConfigTable)
        tableWidget.shrink_wrap()

        self.keyConfigTable = keyConfigTable

        buttonRow = (Button("Assign Key...", action=self.askAssignSelectedKey),
                     Button("Done", action=self.dismiss))

        buttonRow = Row(buttonRow)

        choiceButton = ChoiceButton(["WASD", "Arrows", "Numpad"], choose=self.choosePreset)
        if config.config.get("Keys", "Forward") == "up":
            choiceButton.selectedChoice = "Arrows"
        if config.config.get("Keys", "Forward") == "[8]":
            choiceButton.selectedChoice = "Numpad"

        choiceRow = Row((Label("Presets: "), choiceButton))
        self.choiceButton = choiceButton

        col = Column((tableWidget, choiceRow, buttonRow))
        self.add(col)
        self.shrink_wrap()

    def choosePreset(self):
        preset = self.choiceButton.selectedChoice
        keypairs = self.presets[preset]
        for configKey, key in keypairs:
            config.config.set("Keys", configKey, key)

    def getRowData(self, i):
        configKey = self.keyConfigKeys[i]
        if self.isConfigKey(configKey):
            key = config.config.get("Keys", configKey)
        else:
            key = ""
        return configKey, key

    def isConfigKey(self, configKey):
        return not (len(configKey) == 0 or configKey[0] == "<")

    def selectTableRow(self, i, evt):
        self.selectedKeyIndex = i
        if evt.num_clicks == 2:
            self.askAssignSelectedKey()

    def askAssignSelectedKey(self):
        self.askAssignKey(self.keyConfigKeys[self.selectedKeyIndex])

    def askAssignKey(self, configKey, labelString=None):
        if not self.isConfigKey(configKey):
            return

        panel = Panel()
        panel.bg_color = (0.5, 0.5, 0.6, 1.0)

        if labelString is None:
            labelString = "Press a key to assign to the action \"{0}\"\n\nPress ESC to cancel.".format(configKey)
        label = Label(labelString)
        panel.add(label)
        panel.shrink_wrap()

        def panelKeyDown(evt):
            keyname = key.name(evt.key)
            panel.dismiss(keyname)

        def panelMouseDown(evt):
            button = leveleditor.remapMouseButton(evt.button)
            if button > 2:
                keyname = "mouse{0}".format(button)
                panel.dismiss(keyname)

        panel.key_down = panelKeyDown
        panel.mouse_down = panelMouseDown

        keyname = panel.present()
        if keyname != "escape":
            occupiedKeys = [(v, k) for (k, v) in config.config.items("Keys") if v == keyname]
            oldkey = config.config.get("Keys", configKey)
            config.config.set("Keys", configKey, keyname)
            for keyname, setting in occupiedKeys:
                if self.askAssignKey(setting,
                                     "The key {0} is no longer bound to {1}.\n"
                                     "Press a new key for the action \"{1}\"\n\n"
                                     "Press ESC to cancel."
                                     .format(keyname, setting)):
                    config.config.set("Keys", configKey, oldkey)
                    return True
        else:
            return True


class GraphicsPanel(Panel):
    def __init__(self, mcedit):
        Panel.__init__(self)

        self.mcedit = mcedit

        def getPacks():
            return ["[Default]", "[Current]"] + mcplatform.getTexturePacks()

        def packChanged():
            self.texturePack = self.texturePackChoice.selectedChoice
            packs = getPacks()
            if self.texturePack not in packs:
                self.texturePack = "[Default]"
            self.texturePackChoice.selectedChoice = self.texturePack
            self.texturePackChoice.choices = packs

        self.texturePackChoice = texturePackChoice = ChoiceButton(getPacks(), choose=packChanged)
        if self.texturePack in self.texturePackChoice.choices:
            self.texturePackChoice.selectedChoice = self.texturePack

        texturePackRow = Row((Label("Skin: "), texturePackChoice))

        fieldOfViewRow = FloatInputRow("Field of View: ",
            ref=Settings.fov.propertyRef(), width=100, min=25, max=120)

        targetFPSRow = IntInputRow("Target FPS: ",
            ref=Settings.targetFPS.propertyRef(), width=100, min=1, max=60)

        bufferLimitRow = IntInputRow("Vertex Buffer Limit (MB): ",
            ref=Settings.vertexBufferLimit.propertyRef(), width=100, min=0)

        fastLeavesRow = CheckBoxLabel("Fast Leaves",
            ref=Settings.fastLeaves.propertyRef(),
            tooltipText="Leaves are solid, like Minecraft's 'Fast' graphics")

        roughGraphicsRow = CheckBoxLabel("Rough Graphics",
            ref=Settings.roughGraphics.propertyRef(),
            tooltipText="All blocks are drawn the same way (overrides 'Fast Leaves')")

        enableMouseLagRow = CheckBoxLabel("Enable Mouse Lag",
            ref=Settings.enableMouseLag.propertyRef(),
            tooltipText="Enable choppy mouse movement for faster loading.")

        settingsColumn = Column((fastLeavesRow,
                                  roughGraphicsRow,
                                  enableMouseLagRow,
                                  texturePackRow,
                                  fieldOfViewRow,
                                  targetFPSRow,
                                  bufferLimitRow,
                                  ), align='r')

        settingsColumn = Column((Label("Settings"),
                                 settingsColumn))

        settingsRow = Row((settingsColumn,))

        optionsColumn = Column((settingsRow, Button("OK", action=mcedit.removeGraphicOptions)))
        self.add(optionsColumn)
        self.shrink_wrap()

    def _reloadTextures(self, pack):
        if hasattr(alphaMaterials, "terrainTexture"):
            self.mcedit.displayContext.loadTextures()

    texturePack = Settings.skin.configProperty(_reloadTextures)


class OptionsPanel(Dialog):
    anchor = 'wh'

    def __init__(self, mcedit):
        Dialog.__init__(self)

        self.mcedit = mcedit

        autoBrakeRow = CheckBoxLabel("Autobrake",
            ref=ControlSettings.autobrake.propertyRef(),
            tooltipText="Apply brake when not pressing movement keys")

        swapAxesRow = CheckBoxLabel("Swap Axes Looking Down",
            ref=ControlSettings.swapAxes.propertyRef(),
            tooltipText="Change the direction of the Forward and Backward keys when looking down")

        cameraAccelRow = FloatInputRow("Camera Acceleration: ",
            ref=ControlSettings.cameraAccel.propertyRef(), width=100, min=5.0)

        cameraDragRow = FloatInputRow("Camera Drag: ",
            ref=ControlSettings.cameraDrag.propertyRef(), width=100, min=1.0)

        cameraMaxSpeedRow = FloatInputRow("Camera Max Speed: ",
            ref=ControlSettings.cameraMaxSpeed.propertyRef(), width=100, min=1.0)

        cameraBrakeSpeedRow = FloatInputRow("Camera Braking Speed: ",
            ref=ControlSettings.cameraBrakingSpeed.propertyRef(), width=100, min=1.0)

        mouseSpeedRow = FloatInputRow("Mouse Speed: ",
            ref=ControlSettings.mouseSpeed.propertyRef(), width=100, min=0.1, max=20.0)

        invertRow = CheckBoxLabel("Invert Mouse",
            ref=ControlSettings.invertMousePitch.propertyRef(),
            tooltipText="Reverse the up and down motion of the mouse.")

        spaceHeightRow = IntInputRow("Low Detail Height",
            ref=Settings.spaceHeight.propertyRef(),
            tooltipText="When you are this far above the top of the world, move fast and use low-detail mode.")

        blockBufferRow = IntInputRow("Block Buffer",
            ref=Settings.blockBuffer.propertyRef(), min=1,
            tooltipText="Amount of memory used for temporary storage.  When more than this is needed, the disk is used instead.")

        setWindowPlacementRow = CheckBoxLabel("Set Window Placement",
            ref=Settings.setWindowPlacement.propertyRef(),
            tooltipText="Try to save and restore the window position.")

        windowSizeRow = CheckBoxLabel("Window Resize Alert",
            ref=Settings.shouldResizeAlert.propertyRef(),
            tooltipText="Reminds you that the cursor won't work correctly after resizing the window.")

        visibilityCheckRow = CheckBoxLabel("Visibility Check",
            ref=Settings.visibilityCheck.propertyRef(),
            tooltipText="Do a visibility check on chunks while loading. May cause a crash.")

        longDistanceRow = CheckBoxLabel("Long-Distance Mode",
            ref=Settings.longDistanceMode.propertyRef(),
            tooltipText="Always target the farthest block under the cursor, even in mouselook mode. Shortcut: ALT-Z")

        flyModeRow = CheckBoxLabel("Fly Mode",
            ref=Settings.flyMode.propertyRef(),
            tooltipText="Moving forward and backward will not change your altitude in Fly Mode.")

        self.goPortableButton = goPortableButton = Button("Change", action=self.togglePortable)

        goPortableButton.tooltipText = self.portableButtonTooltip()
        goPortableRow = Row((ValueDisplay(ref=AttrRef(self, 'portableLabelText'), width=250, align='r'), goPortableButton))

        reportRow = CheckBoxLabel("Report Crashes",
            ref=Settings.reportCrashes.propertyRef(),
            tooltipText="Automatically report fatal errors to the author.")

        inputs = (
            spaceHeightRow,
            cameraAccelRow,
            cameraDragRow,
            cameraMaxSpeedRow,
            cameraBrakeSpeedRow,
            blockBufferRow,
            mouseSpeedRow,
        )

        options = (
            longDistanceRow,
            flyModeRow,
            autoBrakeRow,
            swapAxesRow,
            invertRow,
            visibilityCheckRow,
            ) + (
            ((sys.platform == "win32" and pygame.version.vernum == (1, 9, 1)) and (windowSizeRow,) or ())
            ) + (
            reportRow,
            ) + (
            (sys.platform == "win32") and (setWindowPlacementRow,) or ()
            ) + (
            goPortableRow,
        )

        rightcol = Column(options, align='r')
        leftcol = Column(inputs, align='r')

        optionsColumn = Column((Label("Options"),
                                Row((leftcol, rightcol), align="t")))

        settingsRow = Row((optionsColumn,))

        optionsColumn = Column((settingsRow, Button("OK", action=self.dismiss)))

        self.add(optionsColumn)
        self.shrink_wrap()

    @property
    def blockBuffer(self):
        return Settings.blockBuffer.get() / 1048576

    @blockBuffer.setter
    def blockBuffer(self, val):
        Settings.blockBuffer.set(int(val * 1048576))

    def portableButtonTooltip(self):
        return ("Click to make your MCEdit install self-contained by moving the settings and schematics into the program folder",
                "Click to make your MCEdit install persistent by moving the settings and schematics into your Documents folder")[mcplatform.portable]

    @property
    def portableLabelText(self):
        return ("Install Mode: Portable", "Install Mode: Fixed")[1 - mcplatform.portable]

    def togglePortable(self):
        textChoices = [
             "This will make your MCEdit \"portable\" by moving your settings and schematics into the same folder as {0}. Continue?".format((sys.platform == "darwin" and "the MCEdit application" or "MCEditData")),
             "This will move your settings and schematics to your Documents folder. Continue?",
        ]
        if sys.platform == "darwin":
            textChoices[1] = "This will move your schematics to your Documents folder and your settings to your Preferences folder. Continue?"

        alertText = textChoices[mcplatform.portable]
        if ask(alertText) == "OK":
            try:
                [mcplatform.goPortable, mcplatform.goFixed][mcplatform.portable]()
            except Exception, e:
                traceback.print_exc()
                alert(u"Error while moving files: {0}".format(repr(e)))

        self.goPortableButton.tooltipText = self.portableButtonTooltip()


UPDATES_URL = "http://company.com/mceditupdates/"


class MCEdit(GLViewport):
    debug_resize = True

    def __init__(self, displayContext, *args):
        ws = displayContext.getWindowSize()
        r = rect.Rect(0, 0, ws[0], ws[1])
        GLViewport.__init__(self, r)
        self.displayContext = displayContext
        self.bg_color = (0, 0, 0, 1)
        self.anchor = 'tlbr'

        if not config.config.has_section("Recent Worlds"):
            config.config.add_section("Recent Worlds")
            self.setRecentWorlds([""] * 5)

        self.optionsPanel = OptionsPanel(self)
        self.graphicOptionsPanel = GraphicsPanel(self)

        self.keyConfigPanel = KeyConfigPanel()

        self.droppedLevel = None
        self.reloadEditor()

        """
        check command line for files dropped from explorer
        """
        if len(sys.argv) > 1:
            for arg in sys.argv[1:]:
                f = arg.decode(sys.getfilesystemencoding())
                if os.path.isdir(os.path.join(saveFileDir, f)):
                    f = os.path.join(saveFileDir, f)
                    self.droppedLevel = f
                    break
                if os.path.exists(f):
                    self.droppedLevel = f
                    break

        self.fileOpener = FileOpener(self)
        self.add(self.fileOpener)

        self.fileOpener.focus()

    editor = None

    def reloadEditor(self):
        reload(leveleditor)
        level = None

        pos = None

        if self.editor:
            level = self.editor.level
            self.remove(self.editor)
            c = self.editor.mainViewport
            pos, yaw, pitch = c.position, c.yaw, c.pitch

        self.editor = leveleditor.LevelEditor(self)
        self.editor.anchor = 'tlbr'
        if level:
            self.add(self.editor)
            self.editor.gotoLevel(level)
            self.focus_switch = self.editor

            if pos is not None:
                c = self.editor.mainViewport

                c.position, c.yaw, c.pitch = pos, yaw, pitch

    def removeGraphicOptions(self):
        self.removePanel(self.graphicOptionsPanel)

    def removePanel(self, panel):
        if panel.parent:
            panel.set_parent(None)
            if self.editor.parent:
                self.focus_switch = self.editor
            elif self.fileOpener.parent:
                self.focus_switch = self.fileOpener

    def add_right(self, widget):
        w, h = self.size
        widget.centery = h // 2
        widget.right = w
        self.add(widget)

    def showPanel(self, optionsPanel):
        if optionsPanel.parent:
            optionsPanel.set_parent(None)

        optionsPanel.anchor = "whr"
        self.add_right(optionsPanel)
        self.editor.mouseLookOff()

    def showOptions(self):
        self.optionsPanel.present()

    def showGraphicOptions(self):
        self.showPanel(self.graphicOptionsPanel)

    def showKeyConfig(self):
        self.keyConfigPanel.present()

    def loadRecentWorldNumber(self, i):
        worlds = list(self.recentWorlds())
        if i - 1 < len(worlds):
            self.loadFile(worlds[i - 1])

    numRecentWorlds = 5

    def removeLevelDat(self, filename):
        if filename.endswith("level.dat"):
            filename = os.path.dirname(filename)
        return filename

    def recentWorlds(self):
        worlds = []
        for i in range(self.numRecentWorlds):
            if config.config.has_option("Recent Worlds", str(i)):
                try:
                    filename = (config.config.get("Recent Worlds", str(i)).decode('utf-8'))
                    worlds.append(self.removeLevelDat(filename))
                except Exception, e:
                    logging.error(repr(e))

        return list((f for f in worlds if f and os.path.exists(f)))

    def addRecentWorld(self, filename):
        filename = self.removeLevelDat(filename)
        rw = list(self.recentWorlds())
        if filename in rw:
            return
        rw = [filename] + rw[:self.numRecentWorlds - 1]
        self.setRecentWorlds(rw)

    def setRecentWorlds(self, worlds):
        for i, filename in enumerate(worlds):
            config.config.set("Recent Worlds", str(i), filename.encode('utf-8'))

    def makeSideColumn(self):
        def showhistory():
            try:
                with file(os.path.join(mcplatform.dataDir), 'history.txt') as f:
                    history = f.read()

                history = "\n".join(history.split("\n")[:16])

                history += "\n ... see history.txt for more ... "
            except Exception, e:
                history = "Exception while reading history.txt: {0}".format(e)

            if ask(history, ["Show history.txt", "OK"]) == "Show history.txt":
                platform_open(os.path.join(mcplatform.dataDir), "history.txt")

        def showLicense():
            platform_open(os.path.join(mcplatform.dataDir, "LICENSE.txt"))

        readmePath = os.path.join(mcplatform.dataDir, "README.html")

        hotkeys = ([("",
                  "Keys",
                  self.showKeyConfig),
                  ("",
                  "Graphics",
                  self.showGraphicOptions),
                  ("",
                  "Options",
                  self.showOptions),
                  ("",
                  "Source Code",
                  lambda: platform_open("http://www.github.com/mcedit/mcedit")),
                  ("",
                  "View Readme",
                  lambda: platform_open(readmePath)),
                  ("",
                  "Recent Changes",
                  showhistory),
                  ("",
                  "License",
                  showLicense),
                  ])

        c = HotkeyColumn(hotkeys)

        return c

    def resized(self, dw, dh):
        """
        Handle window resizing events.
        """
        GLViewport.resized(self, dw, dh)

        (w, h) = self.size
        if w == 0 and h == 0:
            # The window has been minimized, no need to draw anything.
            self.editor.renderer.render = False
            return

        if not self.editor.renderer.render:
            self.editor.renderer.render = True

        surf = pygame.display.get_surface()
        assert isinstance(surf, pygame.Surface)
        dw, dh = surf.get_size()

        if w > 0 and h > 0:
            Settings.windowWidth.set(w)
            Settings.windowHeight.set(h)
            config.saveConfig()

        if pygame.version.vernum == (1, 9, 1):
            if sys.platform == "win32":
                if w - dw > 20 or h - dh > 20:
                    if not hasattr(self, 'resizeAlert'):
                        self.resizeAlert = self.shouldResizeAlert
                    if self.resizeAlert:
                        alert("Window size increased. You may have problems using the cursor until MCEdit is restarted.")
                        self.resizeAlert = False

    shouldResizeAlert = Settings.shouldResizeAlert.configProperty()

    def loadFile(self, filename):
        self.removeGraphicOptions()
        if os.path.exists(filename):
            try:
                self.editor.loadFile(filename)
            except Exception, e:
                logging.error('Failed to load file {0}: {1!r}'.format(
                    filename, e))
                return None

            self.remove(self.fileOpener)
            self.fileOpener = None
            if self.editor.level:
                self.editor.size = self.size
                self.add(self.editor)
                self.focus_switch = self.editor

    def createNewWorld(self):
        level = self.editor.createNewLevel()
        if level:
            self.remove(self.fileOpener)
            self.editor.size = self.size

            self.add(self.editor)

            self.focus_switch = self.editor
            alert("World created. To expand this infinite world, explore the world in Minecraft or use the Chunk Control tool to add or delete chunks.")

    def removeEditor(self):
        self.remove(self.editor)
        self.fileOpener = FileOpener(self)
        self.add(self.fileOpener)
        self.focus_switch = self.fileOpener

    def confirm_quit(self):
        if self.editor.unsavedEdits:
            result = ask("There are {0} unsaved changes.".format(self.editor.unsavedEdits),
                     responses=["Save and Quit", "Quit", "Cancel"])
            if result == "Save and Quit":
                self.saveAndQuit()
            elif result == "Quit":
                self.justQuit()
            elif result == "Cancel":
                return False
        else:
            raise SystemExit

    def saveAndQuit(self):
        self.editor.saveFile()
        raise SystemExit

    def justQuit(self):
        raise SystemExit

    closeMinecraftWarning = Settings.closeMinecraftWarning.configProperty()

    @classmethod
    def main(self):
        displayContext = GLDisplayContext()

        rootwidget = RootWidget(displayContext.display)
        mcedit = MCEdit(displayContext)
        rootwidget.displayContext = displayContext
        rootwidget.confirm_quit = mcedit.confirm_quit
        rootwidget.mcedit = mcedit

        rootwidget.add(mcedit)
        rootwidget.focus_switch = mcedit
        if 0 == len(alphaMaterials.yamlDatas):
            alert("Failed to load minecraft.yaml. Check the console window for details.")

        if mcedit.droppedLevel:
            mcedit.loadFile(mcedit.droppedLevel)

        if mcedit.closeMinecraftWarning:
            answer = ask("Warning: You must close Minecraft completely before editing. Save corruption may result. Get Satisfaction to learn more.", ["Get Satisfaction", "Don't remind me again.", "OK"], default=1, cancel=1)
            if answer == "Get Satisfaction":
                mcplatform.platform_open("http://getsatisfaction.com/mojang/topics/region_file_cache_interferes_with_map_editors_risking_save_corruption")
            if answer == "Don't remind me again.":
                mcedit.closeMinecraftWarning = False

        config.saveConfig()

        while True:
            try:
                rootwidget.run()
            except SystemExit:
                if sys.platform == "win32" and Settings.setWindowPlacement.get():
                    (flags, showCmd, ptMin, ptMax, rect) = mcplatform.win32gui.GetWindowPlacement(display.get_wm_info()['window'])
                    X, Y, r, b = rect
                    #w = r-X
                    #h = b-Y
                    if (showCmd == mcplatform.win32con.SW_MINIMIZE or
                       showCmd == mcplatform.win32con.SW_SHOWMINIMIZED):
                        showCmd = mcplatform.win32con.SW_SHOWNORMAL

                    Settings.windowX.set(X)
                    Settings.windowY.set(Y)
                    Settings.windowShowCmd.set(showCmd)

                config.saveConfig()
                mcedit.editor.renderer.discardAllChunks()
                mcedit.editor.deleteAllCopiedSchematics()
                raise
            except MemoryError:
                traceback.print_exc()
                mcedit.editor.handleMemoryError()


def main(argv):
    """
    Setup logging, display, bundled schematics. Handle unclean
    shutdowns.
    """
    logging.basicConfig(
        format=u'[%(levelname)s][%(lineno)d][%(module)s]:%(message)s')
    logging.getLogger().level = logging.INFO

    try:
        display.init()
    except pygame.error, e:
        os.environ['SDL_VIDEODRIVER'] = 'directx'
        try:
            display.init()
        except pygame.error:
            os.environ['SDL_VIDEODRIVER'] = 'windib'
            display.init()

    pygame.font.init()

    try:
        if not os.path.exists(mcplatform.schematicsDir):
            shutil.copytree(
                os.path.join(mcplatform.dataDir, u'stock-schematics'),
                mcplatform.schematicsDir
            )
    except Exception, e:
        logging.warning('Error copying bundled schematics: {0!r}'.format(e))
        try:
            os.mkdir(mcplatform.schematicsDir)
        except Exception, e:
            logging.warning('Error creating schematics folder: {0!r}'.format(e))

    try:
        MCEdit.main()
    except SystemExit:
        return 0
    except Exception, e:
        logging.error('An unhandled error occured.', exc_info=True)
        display.quit()
        return 1
    return 0


class GLDisplayContext(object):
    def __init__(self):
        self.reset()

    def getWindowSize(self):
        w, h = (Settings.windowWidth.get(), Settings.windowHeight.get())
        return max(20, w), max(20, h)

    def displayMode(self):
        displayMode = OPENGL | RESIZABLE
        if Settings.doubleBuffer.get():
            displayMode |= DOUBLEBUF
        return displayMode

    def reset(self):
        pygame.key.set_repeat(500, 100)

        try:
            display.gl_set_attribute(GL_SWAP_CONTROL, Settings.vsync.get())
        except Exception, e:
            logging.warning('Unable to set vertical sync: {0!r}'.format(e))

        d = display.set_mode(self.getWindowSize(), self.displayMode())
        try:
            pygame.scrap.init()
        except:
            logging.warning('PyGame clipboard integration disabled.')

        display.set_caption('MCEdit ~ ' + release.release, 'MCEdit')
        if sys.platform == 'win32' and Settings.setWindowPlacement.get():
            Settings.setWindowPlacement.set(False)
            config.saveConfig()
            X, Y = Settings.windowX.get(), Settings.windowY.get()

            if X:
                w, h = self.getWindowSize()
                hwndOwner = display.get_wm_info()['window']

                flags, showCmd, ptMin, ptMax, rect = mcplatform.win32gui.GetWindowPlacement(hwndOwner)
                realW = rect[2] - rect[0]
                realH = rect[3] - rect[1]

                showCmd = Settings.windowShowCmd.get()
                rect = (X, Y, X + realW, Y + realH)

                mcplatform.win32gui.SetWindowPlacement(hwndOwner, (0, showCmd, ptMin, ptMax, rect))

            Settings.setWindowPlacement.set(True)
            config.saveConfig()

        try:
            iconpath = os.path.join(mcplatform.dataDir, 'favicon.png')
            iconfile = file(iconpath, 'rb')
            icon = image.load(iconfile, 'favicon.png')
            display.set_icon(icon)
        except Exception, e:
            logging.warning('Unable to set icon: {0!r}'.format(e))

        self.display = d

        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glAlphaFunc(GL.GL_NOTEQUAL, 0)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

        # textures are 256x256, so with this we can specify pixel coordinates
        GL.glMatrixMode(GL.GL_TEXTURE)
        GL.glScale(1 / 256., 1 / 256., 1 / 256.)

        self.loadTextures()

    def getTerrainTexture(self, level):
        return self.terrainTextures.get(level.materials.name, self.terrainTextures["Alpha"])

    def loadTextures(self):
        self.terrainTextures = {}

        def makeTerrainTexture(mats):
            w, h = 1, 1
            teximage = zeros((w, h, 4), dtype='uint8')
            teximage[:] = 127, 127, 127, 255

            GL.glTexImage2D(
                GL.GL_TEXTURE_2D,
                0,
                GL.GL_RGBA8,
                w,
                h,
                0,
                GL.GL_RGBA,
                GL.GL_UNSIGNED_BYTE,
                teximage
            )

        textures = (
            (classicMaterials, 'terrain-classic.png'),
            (indevMaterials, 'terrain-classic.png'),
            (alphaMaterials, 'terrain.png'),
            (pocketMaterials, 'terrain-pocket.png')
        )

        for mats, matFile in textures:
            try:
                if mats.name == 'Alpha':
                    tex = loadAlphaTerrainTexture()
                else:
                    tex = loadPNGTexture(matFile)
                self.terrainTextures[mats.name] = tex
            except Exception, e:
                logging.warning(
                    'Unable to load terrain from {0}, using flat colors.'
                    'Error was: {1!r}'.format(matFile, e)
                )
                self.terrainTextures[mats.name] = Texture(
                    functools.partial(makeTerrainTexture, mats)
                )
            mats.terrainTexture = self.terrainTextures[mats.name]


def weird_fix():
    try:
        from OpenGL.platform import win32
        win32
    except Exception:
        pass

if __name__ == "__main__":
    sys.exit(main(sys.argv))
