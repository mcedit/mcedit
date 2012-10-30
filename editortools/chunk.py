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
from pymclevel.minecraft_server import MCServerChunkGenerator

from toolbasics import *
from albow.dialogs import Dialog


class ChunkToolPanel(Panel):

    def __init__(self, tool, *a, **kw):
        Panel.__init__(self, *a, **kw)

        self.tool = tool

        self.anchor = "whl"

        chunkToolLabel = Label("Selected Chunks:")

        self.chunksLabel = ValueDisplay(ref=AttrRef(self, 'chunkSizeText'), width=100)
        self.chunksLabel.align = "c"
        self.chunksLabel.tooltipText = "..."

        extractButton = Button("Extract")
        extractButton.tooltipText = "Extract these chunks to individual chunk files"
        extractButton.action = tool.extractChunks
        extractButton.highlight_color = (255, 255, 255)

        deselectButton = Button("Deselect",
            tooltipText=None,
            action=tool.editor.deselect,
        )

        createButton = Button("Create")
        createButton.tooltipText = "Create new, empty chunks within the selection."
        createButton.action = tool.createChunks
        createButton.highlight_color = (0, 255, 0)

        destroyButton = Button("Delete")
        destroyButton.tooltipText = "Delete the selected chunks from disk. Minecraft will recreate them the next time you are near."
        destroyButton.action = tool.destroyChunks

        pruneButton = Button("Prune")
        pruneButton.tooltipText = "Prune the world, leaving only the selected chunks. Any chunks outside of the selection will be removed, and empty region files will be deleted from disk"
        pruneButton.action = tool.pruneChunks

        relightButton = Button("Relight")
        relightButton.tooltipText = "Recalculate light values across the selected chunks"
        relightButton.action = tool.relightChunks
        relightButton.highlight_color = (255, 255, 255)

        repopButton = Button("Repop")
        repopButton.tooltipText = "Mark the selected chunks for repopulation. The next time you play Minecraft, the chunks will have trees, ores, and other features regenerated."
        repopButton.action = tool.repopChunks
        repopButton.highlight_color = (255, 200, 155)

        dontRepopButton = Button("Don't Repop")
        dontRepopButton.tooltipText = "Unmark the selected chunks. They will not repopulate the next time you play the game."
        dontRepopButton.action = tool.dontRepopChunks
        dontRepopButton.highlight_color = (255, 255, 255)

        col = Column((chunkToolLabel, self.chunksLabel, deselectButton, createButton, destroyButton, pruneButton, relightButton, extractButton, repopButton, dontRepopButton))
#        col.right = self.width - 10;
        self.width = col.width
        self.height = col.height
        #self.width = 120
        self.add(col)

    @property
    def chunkSizeText(self):
        return "{0} chunks".format(len(self.tool.selectedChunks()))

    def updateText(self):
        pass
        #self.chunksLabel.text = self.chunksLabelText()


class ChunkTool(EditorTool):
    toolIconName = "chunk"
    tooltipText = "Chunk Control"

    @property
    def statusText(self):
        return "Click and drag to select chunks. Hold ALT to deselect chunks. Hold SHIFT to select chunks."

    def toolEnabled(self):
        return isinstance(self.editor.level, ChunkedLevelMixin)

    _selectedChunks = None
    _displayList = None

    def drawToolMarkers(self):
        if self._displayList is None:
            self._displayList = DisplayList(self._drawToolMarkers)

        #print len(self._selectedChunks) if self._selectedChunks else None, "!=", len(self.editor.selectedChunks)

        if self._selectedChunks != self.editor.selectedChunks or True:  # xxx
            self._selectedChunks = set(self.editor.selectedChunks)
            self._displayList.invalidate()

        self._displayList.call()

    def _drawToolMarkers(self):

        lines = (
            ((-1, 0), (0, 0, 0, 1), []),
            ((1, 0),  (1, 0, 1, 1), []),
            ((0, -1), (0, 0, 1, 0), []),
            ((0, 1),  (0, 1, 1, 1), []),
        )
        for ch in self._selectedChunks:
            cx, cz = ch
            for (dx, dz), points, positions in lines:
                n = (cx + dx, cz + dz)
                if n not in self._selectedChunks:
                    positions.append([ch])

        color = self.editor.selectionTool.selectionColor + (0.3, )
        glColor(*color)
        with gl.glEnable(GL_BLEND):

            import renderer
            sizedChunks = renderer.chunkMarkers(self._selectedChunks)
            for size, chunks in sizedChunks.iteritems():
                if not len(chunks):
                    continue
                chunks = array(chunks, dtype='float32')

                chunkPosition = zeros(shape=(chunks.shape[0], 4, 3), dtype='float32')
                chunkPosition[..., (0, 2)] = array(((0, 0), (0, 1), (1, 1), (1, 0)), dtype='float32')
                chunkPosition[..., (0, 2)] *= size
                chunkPosition[..., (0, 2)] += chunks[:, newaxis, :]
                chunkPosition *= 16
                chunkPosition[..., 1] = self.editor.level.Height
                glVertexPointer(3, GL_FLOAT, 0, chunkPosition.ravel())
                #chunkPosition *= 8
                glDrawArrays(GL_QUADS, 0, len(chunkPosition) * 4)

        for d, points, positions in lines:
            if 0 == len(positions):
                continue
            vertexArray = zeros((len(positions), 4, 3), dtype='float32')
            vertexArray[..., [0, 2]] = positions
            vertexArray.shape = len(positions), 2, 2, 3

            vertexArray[..., 0, 0, 0] += points[0]
            vertexArray[..., 0, 0, 2] += points[1]
            vertexArray[..., 0, 1, 0] += points[2]
            vertexArray[..., 0, 1, 2] += points[3]
            vertexArray[..., 1, 0, 0] += points[2]
            vertexArray[..., 1, 0, 2] += points[3]
            vertexArray[..., 1, 1, 0] += points[0]
            vertexArray[..., 1, 1, 2] += points[1]

            vertexArray *= 16

            vertexArray[..., 1, :, 1] = self.editor.level.Height

            glVertexPointer(3, GL_FLOAT, 0, vertexArray)
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            glDrawArrays(GL_QUADS, 0, len(positions) * 4)
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
            with gl.glEnable(GL_BLEND, GL_DEPTH_TEST):
                glDepthMask(False)
                glDrawArrays(GL_QUADS, 0, len(positions) * 4)
                glDepthMask(True)

    @property
    def worldTooltipText(self):
        box = self.editor.selectionTool.selectionBoxInProgress()
        if box:
            box = box.chunkBox(self.editor.level)
            l, w = box.length // 16, box.width // 16
            return "%s x %s chunks" % (l, w)

    def toolSelected(self):

        self.editor.selectionToChunks()

        self.panel = ChunkToolPanel(self)

        self.panel.centery = self.editor.centery
        self.panel.left = 10

        self.editor.add(self.panel)

    def cancel(self):
        self.editor.remove(self.panel)

    def selectedChunks(self):
        return self.editor.selectedChunks

    @alertException
    def extractChunks(self):
        folder = mcplatform.askSaveFile(mcplatform.docsFolder,
                title='Export chunks to...',
                defaultName=self.editor.level.displayName + "_chunks",
                filetype='Folder\0*.*\0\0',
                suffix="",
                )
        if not folder:
            return

        # TODO: We need a third dimension, Scotty!
        for cx, cz in self.selectedChunks():
            if self.editor.level.containsChunk(cx, cz):
                self.editor.level.extractChunk(cx, cz, folder)

    @alertException
    def destroyChunks(self, chunks=None):
        if "No" == ask("Really delete these chunks? This cannot be undone.", ("Yes", "No")):
            return
        if chunks is None:
            chunks = self.selectedChunks()
        chunks = list(chunks)

        def _destroyChunks():
            i = 0
            chunkCount = len(chunks)

            for cx, cz in chunks:
                i += 1
                yield (i, chunkCount)
                if self.editor.level.containsChunk(cx, cz):
                    try:
                        self.editor.level.deleteChunk(cx, cz)
                    except Exception, e:
                        print "Error during chunk delete: ", e

        with setWindowCaption("DELETING - "):
            showProgress("Deleting chunks...", _destroyChunks())

        self.editor.renderer.invalidateChunkMarkers()
        self.editor.renderer.discardChunks(chunks)
        #self.editor.addUnsavedEdit()

    @alertException
    def pruneChunks(self):
        if "No" == ask("Save these chunks and remove the rest? This cannot be undone.", ("Yes", "No")):
            return
        self.editor.saveFile()

        def _pruneChunks():
            selectedChunks = self.selectedChunks()
            for i, cPos in enumerate(list(self.editor.level.allChunks)):
                if cPos not in selectedChunks:
                    try:
                        self.editor.level.deleteChunk(*cPos)

                    except Exception, e:
                        print "Error during chunk delete: ", e

                yield i, self.editor.level.chunkCount

        with setWindowCaption("PRUNING - "):
            showProgress("Pruning chunks...", _pruneChunks())

        self.editor.renderer.invalidateChunkMarkers()
        self.editor.discardAllChunks()

        #self.editor.addUnsavedEdit()

    @alertException
    def relightChunks(self):

        def _relightChunks():
            for i in self.editor.level.generateLightsIter(self.selectedChunks()):
                yield i

        with setWindowCaption("RELIGHTING - "):

            showProgress("Lighting {0} chunks...".format(len(self.selectedChunks())),
                                     _relightChunks(), cancel=True)

            self.editor.invalidateChunks(self.selectedChunks())
            self.editor.addUnsavedEdit()

    @alertException
    def createChunks(self):
        panel = GeneratorPanel()
        col = [panel]
        label = Label("Create chunks using the settings above? This cannot be undone.")
        col.append(Row([Label("")]))
        col.append(label)
        col = Column(col)
        if Dialog(client=col, responses=["OK", "Cancel"]).present() == "Cancel":
            return
        chunks = self.selectedChunks()

        createChunks = panel.generate(self.editor.level, chunks)

        try:
            with setWindowCaption("CREATING - "):
                showProgress("Creating {0} chunks...".format(len(chunks)), createChunks, cancel=True)
        finally:
            self.editor.renderer.invalidateChunkMarkers()
            self.editor.renderer.loadNearbyChunks()

    @alertException
    def repopChunks(self):
        for cpos in self.selectedChunks():
            try:
                chunk = self.editor.level.getChunk(*cpos)
                chunk.TerrainPopulated = False
            except ChunkNotPresent:
                continue
        self.editor.renderer.invalidateChunks(self.selectedChunks(), layers=["TerrainPopulated"])

    @alertException
    def dontRepopChunks(self):
        for cpos in self.selectedChunks():
            try:
                chunk = self.editor.level.getChunk(*cpos)
                chunk.TerrainPopulated = True
            except ChunkNotPresent:
                continue
        self.editor.renderer.invalidateChunks(self.selectedChunks(), layers=["TerrainPopulated"])

    def mouseDown(self, *args):
        return self.editor.selectionTool.mouseDown(*args)

    def mouseUp(self, evt, *args):
        self.editor.selectionTool.mouseUp(evt, *args)


def GeneratorPanel():
    panel = Widget()
    panel.chunkHeight = 64
    panel.grass = True
    panel.simulate = False

    jarStorage = MCServerChunkGenerator.getDefaultJarStorage()
    if jarStorage:
        jarStorage.reloadVersions()

    generatorChoice = ChoiceButton(["Minecraft Server", "Flatland"])
    panel.generatorChoice = generatorChoice
    col = [Row((Label("Generator:"), generatorChoice))]
    noVersionsRow = Label("Will automatically download and use the latest version")
    versionContainer = Widget()

    heightinput = IntInputRow("Height: ", ref=AttrRef(panel, "chunkHeight"), min=0, max=128)
    grassinput = CheckBoxLabel("Grass", ref=AttrRef(panel, "grass"))

    flatPanel = Column([heightinput, grassinput], align="l")

    def generatorChoiceChanged():
        serverPanel.visible = generatorChoice.selectedChoice == "Minecraft Server"
        flatPanel.visible = not serverPanel.visible

    generatorChoice.choose = generatorChoiceChanged

    versionChoice = None

    if len(jarStorage.versions):
        def checkForUpdates():
            def _check():
                yield
                jarStorage.downloadCurrentServer()
                yield

            showProgress("Checking for server updates...", _check())
            versionChoice.choices = sorted(jarStorage.versions, reverse=True)
            versionChoice.choiceIndex = 0

        versionChoice = ChoiceButton(sorted(jarStorage.versions, reverse=True))
        versionChoiceRow = (Row((
            Label("Server version:"),
            versionChoice,
            Label("or"),
            Button("Check for Updates", action=checkForUpdates))))
        panel.versionChoice = versionChoice
        versionContainer.add(versionChoiceRow)
    else:
        versionContainer.add(noVersionsRow)

    versionContainer.shrink_wrap()

    menu = Menu("Advanced", [
        ("Open Server Storage", "revealStorage"),
        ("Reveal World Cache", "revealCache"),
        ("Delete World Cache", "clearCache")
        ])

    def presentMenu():
        i = menu.present(advancedButton.parent, advancedButton.topleft)
        if i != -1:
            (revealStorage, revealCache, clearCache)[i]()

    advancedButton = Button("Advanced...", presentMenu)

    @alertException
    def revealStorage():
        mcplatform.platform_open(jarStorage.cacheDir)

    @alertException
    def revealCache():
        mcplatform.platform_open(MCServerChunkGenerator.worldCacheDir)

    #revealCacheRow = Row((Label("Minecraft Server Storage: "), Button("Open Folder", action=revealCache, tooltipText="Click me to install your own minecraft_server.jar if you have any.")))

    @alertException
    def clearCache():
        MCServerChunkGenerator.clearWorldCache()

    simRow = CheckBoxLabel("Simulate world", ref=AttrRef(panel, "simulate"), tooltipText="Simulate the world for a few seconds after generating it. Reduces the save file size by processing all of the TileTicks.")

    simRow = Row((simRow, advancedButton), anchor="lrh")
    #deleteCacheRow = Row((Label("Delete Temporary World File Cache?"), Button("Delete Cache!", action=clearCache, tooltipText="Click me if you think your chunks are stale.")))

    serverPanel = Column([versionContainer, simRow, ], align="l")

    col.append(serverPanel)
    col = Column(col, align="l")
    col.add(flatPanel)
    flatPanel.topleft = serverPanel.topleft
    flatPanel.visible = False
    panel.add(col)

    panel.shrink_wrap()

    def generate(level, arg):
        useServer = generatorChoice.selectedChoice == "Minecraft Server"

        if useServer:
            def _createChunks():
                try:
                    if versionChoice:
                        version = versionChoice.selectedChoice
                    else:
                        version = None
                    gen = MCServerChunkGenerator(version=version)
                except Exception, e:
                    traceback.print_exc()
                    alert("Failed to start the chunk generator. {0!r}".format(e))
                    yield "Failed"
                    return

                if isinstance(arg, BoundingBox):
                    for i in gen.createLevelIter(level, arg, simulate=panel.simulate):
                        yield i
                else:
                    for i in gen.generateChunksInLevelIter(level, arg, simulate=panel.simulate):
                        yield i

        else:
            def _createChunks():
                height = panel.chunkHeight
                grass = panel.grass and alphaMaterials.Grass.ID or alphaMaterials.Dirt.ID
                if isinstance(arg, BoundingBox):
                    chunks = list(arg.chunkPositions)
                else:
                    chunks = arg

                if level.dimNo in (-1, 1):
                    maxskylight = 0
                else:
                    maxskylight = 15

                for i, (cx, cz) in enumerate(chunks):

                    yield i, len(chunks)
                    #surface = blockInput.blockInfo

                    #for cx, cz in :
                    try:
                        level.createChunk(cx, cz)
                    except ValueError, e:  # chunk already present
                        print e
                        continue
                    else:
                        ch = level.getChunk(cx, cz)
                        if height > 0:
                            stoneHeight = max(0, height - 5)
                            grassHeight = max(0, height - 1)

                            ch.Blocks[:, :, grassHeight] = grass
                            ch.Blocks[:, :, stoneHeight:grassHeight] = alphaMaterials.Dirt.ID
                            ch.Blocks[:, :, :stoneHeight] = alphaMaterials.Stone.ID

                            ch.Blocks[:, :, 0] = alphaMaterials.Bedrock.ID
                            ch.SkyLight[:, :, height:] = maxskylight
                            if maxskylight:
                                ch.HeightMap[:] = height

                        else:
                            ch.SkyLight[:] = maxskylight

                        ch.needsLighting = False
                        ch.dirty = True
                        ch.save()

        return _createChunks()

    panel.generate = generate
    return panel
