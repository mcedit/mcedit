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

"""
mcedit.py

Startup, main menu, keyboard configuration, automatic updating.
"""

print "Loading imports..."
import os
import sys

class SafeOutputStream(object):
    def __init__(self, oldStream):
        self.oldStream = oldStream
    def write(self, text):
        try:
            self.oldStream.write(text.decode("utf8", "replace").encode(self.oldStream.encoding or "utf8", "replace"))
        except Exception, e:
            pass

    def flush(self):
        self.oldStream.flush()

    def close(self):
        pass


class tee(object):
    def __init__(self, _fd1, _fd2) :
        self.fd1 = _fd1
        self.fd2 = _fd2

    def __del__(self) :
        if self.fd1 != sys.stdout and self.fd1 != sys.stderr :
            self.fd1.close()
        if self.fd2 != sys.stdout and self.fd2 != sys.stderr :
            self.fd2.close()


    def write(self, text) :
        self.fd1.write(text)
        self.fd2.write(text)

    def flush(self) :
        self.fd1.flush()
        self.fd2.flush()

print "Adding SafeOutputStream..."
sys.stdout = SafeOutputStream(sys.stdout)
sys.stderr = sys.stdout


try:
    from release import release
    print "Release: ", release

    import locale
    locale.setlocale(locale.LC_ALL, '')
    import traceback
    import logging
    from os.path import exists, isdir, join

    import tempfile
    import gc
    import functools
    import urllib
    import threading
    import tarfile
    import zipfile
    import shutil
    from cStringIO import StringIO
    import platform
    from datetime import timedelta

    from errorreporting import reportException

    if "-debug" in sys.argv and platform.architecture()[0] == "32bit":
        os.environ['PATH'] = "C:\\Program Files (x86)\\GLIntercept_1_0_Beta01" + os.pathsep + os.environ['PATH']
    try:
        print "Loading OpenGL..."
        import OpenGL
    except ImportError:
        print "***"
        print "***   REQUIRED MODULE PyOpenGL not found!"
        print "***   Please install PyOpenGL from http://pyopengl.sourceforge.net"
        print "***   Or use the command 'easy_install PyOpenGL'"
        print "***"
        raise SystemExit


    loglevel = logging.INFO
    if "-debug" in sys.argv:
        loglevel = logging.DEBUG
    if "-gldebug" in sys.argv:
        print "GL Debug mode - All errors raise exceptions"
        OpenGL.ERROR_ON_COPY = True
        if "-full" in sys.argv:
            OpenGL.FULL_LOGGING = True

    else:
        OpenGL.ERROR_CHECKING = False
    logging.basicConfig(format=u'%(levelname)s:%(message)s')
    logging.getLogger().level = logging.WARN

    from OpenGL import GL
    logging.getLogger().level = loglevel

    try:
        print "Loading numpy..."
        import numpy
    except ImportError:
        print "***"
        print "***   REQUIRED MODULE numpy not found!"
        print "***   Please install numpy from http://numpy.scipy.org"
        print "***   Or use the command 'easy_install numpy'"
        print "***"
        raise SystemExit
    try:
        print "Loading pygame..."
        import pygame
    except ImportError:
        print "***"
        print "***   REQUIRED MODULE pygame not found!"
        print "***   Please install pygame from http://pygame.sourceforge.net"
        print "***   Or use the command 'easy_install pygame'"
        print "***"
        raise SystemExit

    import mcplatform
    try:
        logfile = file(mcplatform.dataDir + os.path.sep + "mcedit.log", "w")

        logfile = SafeOutputStream(logfile)

        sys.stdout = tee(sys.stdout, logfile)
        sys.stderr = sys.stdout
    except Exception as e:
        print "Error opening logfile", repr(e)






    #from OpenGL.GLUT import glutBitmapCharacter, glutInit


    print "Loading albow..."

    from albow.openglwidgets import GLViewport
    from albow.root import RootWidget
    from albow.dialogs import Dialog
    from albow import *
    #from bresenham import bresenham
    from glbackground import Panel

    from depths import DepthOffset
    import config
    from mceutils import *
    from glutils import gl, Texture
    #Label = GLLabel
    import leveleditor

    print "Loading pymclevel..."
    from pymclevel.mclevel import MCLevel, MCSchematic, MCInfdevOldLevel, saveFileDir
    from pymclevel.materials import *
    MCInfdevOldLevel.loadedChunkLimit = 0



    print "Initializing pygame..."
    import pygame
    from pygame import key, display, rect
    def initDisplay():
        try:
            display.init()
        except pygame.error:
            os.environ['SDL_VIDEODRIVER'] = "directx"
            try:
                display.init()
            except pygame.error:
                os.environ['SDL_VIDEODRIVER'] = "windib"
                display.init()
        #print "pygame.init:", pygame.init()


    from pygame.constants import *
    pygame.font.init()




    from numpy import *
    #from math import sin, cos, radians


    #raise ValueError, "OH SHIT"
except Exception, e:

    traceback.print_exc()
    print "Startup failed."
    print "Please send a copy or screenshot of this error to codewarrior0@gmail.com"
    try:
        reportException(e)
    except:
        pass
    import sys
    sys.exit(1)

#from Font import Font
ESCAPE = '\033'

from mcplatform import platform_open

from leveleditor import Settings, ControlSettings



class FileOpener(Widget):
    is_gl_container = True

    def __init__(self, mcedit, *args, **kwargs):
        kwargs['rect'] = mcedit.rect
        Widget.__init__(self, *args, **kwargs)
        self.anchor = 'tlbr'
        self.mcedit = mcedit

        helpCursor = 100
        helpColumn = []

        label = Label("{0} {1} {2} {3} {4} {5}".format(config.config.get('Keys', 'Forward'),
                                       config.config.get('Keys', 'Left'),
                                       config.config.get('Keys', 'Back'),
                                       config.config.get('Keys', 'Right'),
                                       config.config.get('Keys', 'Up'),
                                       config.config.get('Keys', 'Down'),
                                       ).upper() + " to move")
        #label.fg_color = (242, 244, 255);
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

        helpColumn = Column(helpColumn , align="r")
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
                print repr(e)

            if shortname == "level.dat":
                shortname = os.path.basename(os.path.dirname(world))

            if len(shortname) > 40:
                shortname = shortname[:37] + "..."
            shortnames.append(shortname)


        hotkeys = ([ ('N', 'Create New World', self.createNewWorld),
            ('L', 'Load World...', self.mcedit.editor.askLoadWorld),
            ('O', 'Open a level...', self.promptOpenAndLoad)  ] + [
            ('F{0}'.format(i + 1), shortnames[i] , self.createLoadButtonHandler(world))
            for i, world in enumerate(self.mcedit.recentWorlds()) ])

        commandRow = HotkeyColumn(hotkeys, keysColumn, buttonsColumn)


        #buttonEnable(world)
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
            if filename: self.mcedit.loadFile(filename);
        except Exception, e:
            print "Error during promptOpen: ", e

    def createNewWorld(self):
        self.parent.createNewWorld()

    def createLoadButtonHandler(self, filename):
        return lambda:self.mcedit.loadFile(filename)

import pymclevel

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

    presets = { "WASD": [
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
        keyConfigTable.num_rows = lambda : len(self.keyConfigKeys)
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

    def askAssignKey(self, configKey, labelString = None):
        if not self.isConfigKey(configKey): return

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
            occupiedKeys = [(v,k) for (k,v) in config.config.items("Keys") if v == keyname]
            oldkey = config.config.get("Keys", configKey)#save key before recursive call
            config.config.set("Keys", configKey, keyname)
            for keyname, setting in occupiedKeys:
                if self.askAssignKey(setting,
                                     "The key {0} is no longer bound to {1}.\n"
                                     "Press a new key for the action \"{1}\"\n\n"
                                     "Press ESC to cancel."
                                     .format(keyname, setting)):
                    config.config.set("Keys", configKey, oldkey) #revert
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

        settingsColumn = Column(( fastLeavesRow,
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
            ((sys.platform == "win32" and pygame.version.vernum == (1,9,1)) and (windowSizeRow,) or ())
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
            print "Moving files..."
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

            self.setRecentWorlds([""]*5)



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
                if isdir(join(saveFileDir, f)):
                    f = join(saveFileDir, f)
                    self.droppedLevel = f
                    break
                if exists(f):
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
                    print repr(e)

        return list((f for f in worlds if f and os.path.exists(f)))

    def addRecentWorld(self, filename):
        filename = self.removeLevelDat(filename)
        rw = list(self.recentWorlds())
        if filename in rw: return
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
        GLViewport.resized(self, dw, dh)

        (w, h) = self.size
        if w == 0 and h == 0: # we got minimized?
            print "Minimized!", w, h
            self.editor.renderer.render = False
            return
        if not self.editor.renderer.render:
            print "Restored!", w, h
            self.editor.renderer.render = True

        surf=pygame.display.get_surface()
        assert isinstance(surf, pygame.Surface)
        dw, dh = surf.get_size()
        print "Resized!", w, h, "d", dw-w, dh-h

        if w > 0 and h > 0:
            Settings.windowWidth.set(w)
            Settings.windowHeight.set(h)
            config.saveConfig()

        if pygame.version.vernum == (1,9,1):
            if sys.platform == "win32":
                if w-dw > 20 or h-dh > 20:
                    if not hasattr(self, 'resizeAlert'):
                        self.resizeAlert = self.shouldResizeAlert
                    if self.resizeAlert:
                        alert("Window size increased. You may have problems using the cursor until MCEdit is restarted.")
                        self.resizeAlert = False

    shouldResizeAlert = Settings.shouldResizeAlert.configProperty()


        #self.size = (w,h)


    def loadFile(self, filename):
        self.removeGraphicOptions()
        if os.path.exists(filename):

            try:
                self.editor.loadFile(filename)
            except Exception, e:
                print u"Failed to load file ", filename, e
                traceback.print_exc()
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
                     responses = ["Save and Quit", "Quit", "Cancel"] )
            if result == "Save and Quit":self.saveAndQuit()
            elif result == "Quit":       self.justQuit()
            elif result == "Cancel": return False;
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
        print "MCEdit.main()"
        #MCEdit.extractReadmes();


        displayContext = GLDisplayContext()


        #mcedit.size = displayContext.getWindowSize()
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
                print "Disabled warning"




        print "saveConfig()"
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
            except MemoryError, e:
                traceback.print_exc()
                mcedit.editor.handleMemoryError()


def main():

    #mcplatform.findDirectories();
    try:
        if not os.path.exists(mcplatform.schematicsDir):
            shutil.copytree(os.path.join(mcplatform.dataDir, u"stock-schematics"), mcplatform.schematicsDir)
    except Exception, e:
        print "Error copying bundled schematics: ", e
        try:
            os.mkdir(mcplatform.schematicsDir)
        except Exception, e:
            print "Error creating schematics dir: ", e

    try:
        print "dataDir is ", mcplatform.dataDir
        print "docsFolder is ", mcplatform.docsFolder
    except:
        pass

    MCEdit.profiling = "-profile" in sys.argv
    if MCEdit.profiling:
        print "-- Profiling Enabled --"
        _profilemain()
    else:
        _main()

if os.environ.get("MCEDIT_LOWMEMTEST", None):
    hog = zeros((1024 * 1024 * 1024), dtype='uint8')
    pig = zeros((1 * 1024 * 1024), dtype='uint8')

def _main():
    try:

        #global mv
        #mv = MCEdit()
        #raise ValueError, "Programmer requested error"
        MCEdit.main()
    except SystemExit:
        raise
    except Exception, e:
        print "An error has been found!  Please send the following to codewarrior0@gmail.com."

        reportException(e)

        display.quit()

        if not mcplatform.runningInEditor:
            raw_input("Press ENTER to dismiss...")
        sys.exit(1)


import cProfile
def _profilemain():

    cProfile.run("_main()", mcplatform.dataDir + os.path.sep + "mcedit.profile")
    # p = Stats("mcedit.profile");
    # p.sort_stats('cum');
    # p.print_stats(15);
    # #system("c:\program files (x86)\graphviz\")
    if mcplatform.runningInEditor:
        del os.environ["PYTHONPATH"]
        os.system("python gprof2dot.py -f pstats mcedit.profile > mcedit.dot ")
        os.system("dot -Tpng mcedit.dot -o mcedit.png")
        os.startfile("mcedit.png")

class GLDisplayContext(object):
    def __init__(self):
        self.reset()

    def getWindowSize(self):
        w, h = (Settings.windowWidth.get(),
                Settings.windowHeight.get(),
                )

        return max(20, w), max(20, h)

    def displayMode(self):
        if Settings.doubleBuffer.get():
            print "Double-buffered surface"
            displayMode = OPENGL | DOUBLEBUF | RESIZABLE
        else:
            print "Single-buffered surface"
            displayMode = OPENGL | RESIZABLE

        return displayMode

    def reset(self):
        initDisplay()

        pygame.key.set_repeat(500, 100)

        try:
            display.gl_set_attribute(GL_SWAP_CONTROL, Settings.vsync.get())
        except Exception, e:
            print("Failed to set vertical sync: {0!r}".format(e))

        d = display.set_mode(self.getWindowSize(), self.displayMode())
        try:
            pygame.scrap.init()
        except:
            print "scrap not available"
        display.set_caption("MCEdit " + release.release)
        print "Display: ", d
        if sys.platform == "win32" and Settings.setWindowPlacement.get():
            print "Attempting SetWindowPlacement..."
            Settings.setWindowPlacement.set(False)
            config.saveConfig()
            X, Y = Settings.windowX.get(), Settings.windowY.get()

            if X:
                w, h = self.getWindowSize()
                hwndOwner = display.get_wm_info()['window']

                flags, showCmd, ptMin, ptMax, rect = mcplatform.win32gui.GetWindowPlacement(hwndOwner)
                realW = rect[2] - rect[0]
                realH = rect[3] - rect[1]

                print "GetWindowPlacement", ptMin, ptMax, rect
                showCmd = Settings.windowShowCmd.get()
                rect = (X, Y, X+realW, Y+realH) #left, top, right, bottom


                mcplatform.win32gui.SetWindowPlacement(hwndOwner , (0, showCmd, ptMin, ptMax, rect))

            Settings.setWindowPlacement.set(True)
            config.saveConfig()

        try:
            iconpath = os.path.join(mcplatform.dataDir, "favicon.png")
            iconfile = file(iconpath, "rb")
            icon = image.load(iconfile, "favicon.png")
            display.set_icon(icon)
        except Exception, e:
            print "Error setting icon:", repr(e)

        self.display = d

        #glutInit();
        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glAlphaFunc(GL.GL_NOTEQUAL, 0)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

        "textures are 256x256, so with this we can specify pixel coordinates"
        GL.glMatrixMode(GL.GL_TEXTURE)
        GL.glScale(1 / 256., 1 / 256., 1 / 256.)

        self.loadTextures()

    def getTerrainTexture(self, level):
        return self.terrainTextures.get(level.materials.name, self.terrainTextures["Alpha"])

    def loadTextures(self):
        print "Loading terrain textures..."
        self.terrainTextures = {}

        def makeTerrainTexture(mats):
            w, h = 1, 1
            teximage = zeros((w, h, 4), dtype='uint8')
            teximage[:] = 127, 127, 127, 255

            GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA8,
                     w, h, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, teximage)

        for mats, matFile in ( (classicMaterials, "terrain-classic.png"),
                               (indevMaterials, "terrain-classic.png"),
                               (alphaMaterials,   "terrain.png"),
                               (pocketMaterials,  "terrain-pocket.png") ):
            matName = mats.name
            try:
                if matName=="Alpha":
                    tex = loadAlphaTerrainTexture()
                else:
                    tex = loadPNGTexture(matFile)

                self.terrainTextures[matName] = tex

            except Exception, e:
                print repr(e), "while loading Classic terrain texture from {0}. Using flat colors.".format(matFile)
                self.terrainTextures[matName] = Texture(functools.partial(makeTerrainTexture, mats))
            mats.terrainTexture = self.terrainTextures[matName]







import editortools

def weird_fix():
    #weird fix to make opengl include all files, found online
    from ctypes import util
    try:
        from OpenGL.platform import win32
        win32
    except Exception, e:
        pass

if __name__ == "__main__":
    try:
        main()
    except Exception, e:
        traceback.print_exc()
        print("An error occured. Please post the above exception as an issue"
                "on https://github.com/mcedit/mcedit/issues/new")
        raw_input("Press ENTER to dismiss...")

