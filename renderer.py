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
renderer.py

What is going on in this file?

Here is an attempt to show the relationships between classes and
their responsibilities

MCRenderer:
    has "position", "origin", optionally "viewFrustum"
    Loads chunks near position+origin, draws chunks offset by origin
    Calls visible on viewFrustum to exclude chunks


    (+) ChunkRenderer
        Has "chunkPosition", "invalidLayers", "lists"
        One per chunk and detail level.
        Creates display lists from BlockRenderers

        (*) BlockRenderer
            Has "vertexArrays"
            One per block type, plus one for low detail and one for Entity

"""

from collections import defaultdict, deque
from datetime import datetime, timedelta
from depths import DepthOffset
from glutils import gl, Texture
import logging
import numpy
from OpenGL import GL
import pymclevel
import sys
#import time


def chunkMarkers(chunkSet):
    """ Returns a mapping { size: [position, ...] } for different powers of 2
    as size.
    """

    sizedChunks = defaultdict(list)
    size = 1

    def all4(cx, cz):
        cx &= ~size
        cz &= ~size
        return [(cx, cz), (cx + size, cz), (cx + size, cz + size), (cx, cz + size)]

    # lastsize = 6
    size = 1
    while True:
        nextsize = size << 1
        chunkSet = set(chunkSet)
        while len(chunkSet):
            cx, cz = chunkSet.pop()
            chunkSet.add((cx, cz))
            o = all4(cx, cz)
            others = set(o).intersection(chunkSet)
            if len(others) == 4:
                sizedChunks[nextsize].append(o[0])
                for c in others:
                    chunkSet.discard(c)
            else:
                for c in others:
                    sizedChunks[size].append(c)
                    chunkSet.discard(c)

        if len(sizedChunks[nextsize]):
            chunkSet = set(sizedChunks[nextsize])
            sizedChunks[nextsize] = []
            size <<= 1
        else:
            break
    return sizedChunks


class ChunkRenderer(object):
    maxlod = 2
    minlod = 0

    def __init__(self, renderer, chunkPosition):
        self.renderer = renderer
        self.blockRenderers = []
        self.detailLevel = 0
        self.invalidLayers = set(Layer.AllLayers)

        self.chunkPosition = chunkPosition
        self.bufferSize = 0
        self.renderstateLists = None

    @property
    def visibleLayers(self):
        return self.renderer.visibleLayers

    def forgetDisplayLists(self, states=None):
        if self.renderstateLists is not None:
            # print "Discarded {0}, gained {1} bytes".format(self.chunkPosition,self.bufferSize)

            for k in states or self.renderstateLists.iterkeys():
                a = self.renderstateLists.get(k, [])
                # print a
                for i in a:
                    gl.glDeleteLists(i, 1)

            if states:
                del self.renderstateLists[states]
            else:
                self.renderstateLists = None

            self.needsRedisplay = True
            self.renderer.discardMasterList()

    def debugDraw(self):
        for blockRenderer in self.blockRenderers:
            blockRenderer.drawArrays(self.chunkPosition, False)

    def makeDisplayLists(self):
        if not self.needsRedisplay:
            return
        self.forgetDisplayLists()
        if not self.blockRenderers:
            return

        lists = defaultdict(list)

        showRedraw = self.renderer.showRedraw

        if not (showRedraw and self.needsBlockRedraw):
            GL.glEnableClientState(GL.GL_COLOR_ARRAY)

        renderers = self.blockRenderers

        for blockRenderer in renderers:
            if self.detailLevel not in blockRenderer.detailLevels:
                continue
            if blockRenderer.layer not in self.visibleLayers:
                continue

            l = blockRenderer.makeArrayList(self.chunkPosition, self.needsBlockRedraw and showRedraw)
            lists[blockRenderer.renderstate].append(l)

        if not (showRedraw and self.needsBlockRedraw):
            GL.glDisableClientState(GL.GL_COLOR_ARRAY)

        self.needsRedisplay = False
        self.renderstateLists = lists

    @property
    def needsBlockRedraw(self):
        return Layer.Blocks in self.invalidLayers

    def invalidate(self, layers=None):
        if layers is None:
            layers = Layer.AllLayers

        if layers:
            layers = set(layers)
            self.invalidLayers.update(layers)
            blockRenderers = [br for br in self.blockRenderers
                              if br.layer is Layer.Blocks
                              or br.layer not in layers]
            if len(blockRenderers) < len(self.blockRenderers):
                self.forgetDisplayLists()
            self.blockRenderers = blockRenderers

            if self.renderer.showRedraw and Layer.Blocks in layers:
                self.needsRedisplay = True

    def calcFaces(self):
        minlod = self.renderer.detailLevelForChunk(self.chunkPosition)

        minlod = min(minlod, self.maxlod)
        if self.detailLevel != minlod:
            self.forgetDisplayLists()
            self.detailLevel = minlod
            self.invalidLayers.add(Layer.Blocks)

            # discard the standard detail renderers
            if minlod > 0:
                blockRenderers = []
                for br in self.blockRenderers:
                    if br.detailLevels != (0,):
                        blockRenderers.append(br)

                self.blockRenderers = blockRenderers

        if self.renderer.chunkCalculator:
            for i in self.renderer.chunkCalculator.calcFacesForChunkRenderer(self):
                yield

        else:
            raise StopIteration
            yield

    def vertexArraysDone(self):
        bufferSize = 0
        for br in self.blockRenderers:
            bufferSize += br.bufferSize()
            if self.renderer.alpha != 0xff:
                br.setAlpha(self.renderer.alpha)
        self.bufferSize = bufferSize
        self.invalidLayers = set()
        self.needsRedisplay = True
        self.renderer.invalidateMasterList()

    needsRedisplay = False

    @property
    def done(self):
        return len(self.invalidLayers) == 0

_XYZ = numpy.s_[..., 0:3]
_ST = numpy.s_[..., 3:5]
_XYZST = numpy.s_[..., :5]
_RGBA = numpy.s_[..., 20:24]
_RGB = numpy.s_[..., 20:23]
_A = numpy.s_[..., 23]


def makeVertexTemplates(xmin=0, ymin=0, zmin=0, xmax=1, ymax=1, zmax=1):
        return numpy.array([

             # FaceXIncreasing:
                              [[xmax, ymin, zmax, (zmin * 16), 16 - (ymin * 16), 0x0b],
                               [xmax, ymin, zmin, (zmax * 16), 16 - (ymin * 16), 0x0b],
                               [xmax, ymax, zmin, (zmax * 16), 16 - (ymax * 16), 0x0b],
                               [xmax, ymax, zmax, (zmin * 16), 16 - (ymax * 16), 0x0b],
                               ],

             # FaceXDecreasing:
                              [[xmin, ymin, zmin, (zmin * 16), 16 - (ymin * 16), 0x0b],
                               [xmin, ymin, zmax, (zmax * 16), 16 - (ymin * 16), 0x0b],
                               [xmin, ymax, zmax, (zmax * 16), 16 - (ymax * 16), 0x0b],
                               [xmin, ymax, zmin, (zmin * 16), 16 - (ymax * 16), 0x0b]],


             # FaceYIncreasing:
                              [[xmin, ymax, zmin, xmin * 16, 16 - (zmax * 16), 0x11],  # ne
                               [xmin, ymax, zmax, xmin * 16, 16 - (zmin * 16), 0x11],  # nw
                               [xmax, ymax, zmax, xmax * 16, 16 - (zmin * 16), 0x11],  # sw
                               [xmax, ymax, zmin, xmax * 16, 16 - (zmax * 16), 0x11]],  # se

             # FaceYDecreasing:
                              [[xmin, ymin, zmin, xmin * 16, 16 - (zmax * 16), 0x08],
                               [xmax, ymin, zmin, xmax * 16, 16 - (zmax * 16), 0x08],
                               [xmax, ymin, zmax, xmax * 16, 16 - (zmin * 16), 0x08],
                               [xmin, ymin, zmax, xmin * 16, 16 - (zmin * 16), 0x08]],

             # FaceZIncreasing:
                              [[xmin, ymin, zmax, xmin * 16, 16 - (ymin * 16), 0x0d],
                               [xmax, ymin, zmax, xmax * 16, 16 - (ymin * 16), 0x0d],
                               [xmax, ymax, zmax, xmax * 16, 16 - (ymax * 16), 0x0d],
                               [xmin, ymax, zmax, xmin * 16, 16 - (ymax * 16), 0x0d]],

             # FaceZDecreasing:
                              [[xmax, ymin, zmin, xmin * 16, 16 - (ymin * 16), 0x0d],
                               [xmin, ymin, zmin, xmax * 16, 16 - (ymin * 16), 0x0d],
                               [xmin, ymax, zmin, xmax * 16, 16 - (ymax * 16), 0x0d],
                               [xmax, ymax, zmin, xmin * 16, 16 - (ymax * 16), 0x0d],
                              ],

        ])

elementByteLength = 24


def createPrecomputedVertices():
    height = 16
    precomputedVertices = [numpy.zeros(shape=(16, 16, height, 4, 6),  # x,y,z,s,t,rg, ba
                                  dtype='float32') for d in faceVertexTemplates]

    xArray = numpy.arange(16)[:, numpy.newaxis, numpy.newaxis, numpy.newaxis]
    zArray = numpy.arange(16)[numpy.newaxis, :, numpy.newaxis, numpy.newaxis]
    yArray = numpy.arange(height)[numpy.newaxis, numpy.newaxis, :, numpy.newaxis]

    for dir in range(len(faceVertexTemplates)):
        precomputedVertices[dir][_XYZ][..., 0] = xArray
        precomputedVertices[dir][_XYZ][..., 1] = yArray
        precomputedVertices[dir][_XYZ][..., 2] = zArray
        precomputedVertices[dir][_XYZ] += faceVertexTemplates[dir][..., 0:3]  # xyz

        precomputedVertices[dir][_ST] = faceVertexTemplates[dir][..., 3:5]  # s
        precomputedVertices[dir].view('uint8')[_RGB] = faceVertexTemplates[dir][..., 5, numpy.newaxis]
        precomputedVertices[dir].view('uint8')[_A] = 0xff

    return precomputedVertices

faceVertexTemplates = makeVertexTemplates()


class ChunkCalculator (object):
    cachedTemplate = None
    cachedTemplateHeight = 0

    whiteLight = numpy.array([[[15] * 16] * 16] * 16, numpy.uint8)
    precomputedVertices = createPrecomputedVertices()

    def __init__(self, level):
        self.makeRenderstates(level.materials)

            # del xArray, zArray, yArray
        self.nullVertices = numpy.zeros((0,) * len(self.precomputedVertices[0].shape), dtype=self.precomputedVertices[0].dtype)
        from leveleditor import Settings

        Settings.fastLeaves.addObserver(self)
        Settings.roughGraphics.addObserver(self)

    class renderstatePlain(object):
        @classmethod
        def bind(self):
            pass

        @classmethod
        def release(self):
            pass

    class renderstateVines(object):
        @classmethod
        def bind(self):
            GL.glDisable(GL.GL_CULL_FACE)
            GL.glEnable(GL.GL_ALPHA_TEST)

        @classmethod
        def release(self):
            GL.glEnable(GL.GL_CULL_FACE)
            GL.glDisable(GL.GL_ALPHA_TEST)

    class renderstateLowDetail(object):
        @classmethod
        def bind(self):
            GL.glDisable(GL.GL_CULL_FACE)
            GL.glDisable(GL.GL_TEXTURE_2D)

        @classmethod
        def release(self):
            GL.glEnable(GL.GL_CULL_FACE)
            GL.glEnable(GL.GL_TEXTURE_2D)

    class renderstateAlphaTest(object):
        @classmethod
        def bind(self):
            GL.glEnable(GL.GL_ALPHA_TEST)

        @classmethod
        def release(self):
            GL.glDisable(GL.GL_ALPHA_TEST)

    class _renderstateAlphaBlend(object):
        @classmethod
        def bind(self):
            GL.glEnable(GL.GL_BLEND)

        @classmethod
        def release(self):
            GL.glDisable(GL.GL_BLEND)

    class renderstateWater(_renderstateAlphaBlend):
        pass

    class renderstateIce(_renderstateAlphaBlend):
        pass

    class renderstateEntity(object):
        @classmethod
        def bind(self):
            GL.glDisable(GL.GL_DEPTH_TEST)
            # GL.glDisable(GL.GL_CULL_FACE)
            GL.glDisable(GL.GL_TEXTURE_2D)
            GL.glEnable(GL.GL_BLEND)

        @classmethod
        def release(self):
            GL.glEnable(GL.GL_DEPTH_TEST)
            # GL.glEnable(GL.GL_CULL_FACE)
            GL.glEnable(GL.GL_TEXTURE_2D)
            GL.glDisable(GL.GL_BLEND)

    renderstates = (
        renderstatePlain,
        renderstateVines,
        renderstateLowDetail,
        renderstateAlphaTest,
        renderstateIce,
        renderstateWater,
        renderstateEntity,
    )

    def makeRenderstates(self, materials):
        self.blockRendererClasses = [
            GenericBlockRenderer,
            LeafBlockRenderer,
            PlantBlockRenderer,
            TorchBlockRenderer,
            WaterBlockRenderer,
            SlabBlockRenderer,
        ]
        if materials.name in ("Alpha", "Pocket"):
            self.blockRendererClasses += [
                RailBlockRenderer,
                LadderBlockRenderer,
                SnowBlockRenderer,
                RedstoneBlockRenderer,
                IceBlockRenderer,
                FeatureBlockRenderer,
                StairBlockRenderer,
                VineBlockRenderer,
            # button, floor plate, door -> 1-cube features
            # lever, sign, wall sign, stairs -> 2-cube features

            # repeater
            # fence

            # bed
            # cake
            # portal
            ]

        self.materialMap = materialMap = numpy.zeros((pymclevel.materials.id_limit,), 'uint8')
        materialMap[1:] = 1  # generic blocks

        materialCount = 2

        for br in self.blockRendererClasses[1:]:  # skip generic blocks
            materialMap[br.getBlocktypes(materials)] = materialCount
            br.materialIndex = materialCount
            materialCount += 1

        self.exposedMaterialMap = numpy.array(materialMap)
        self.addTransparentMaterials(self.exposedMaterialMap, materialCount)

    def addTransparentMaterials(self, mats, materialCount):
        transparentMaterials = [
            pymclevel.materials.alphaMaterials.Glass,
            pymclevel.materials.alphaMaterials.GlassPane,
            pymclevel.materials.alphaMaterials.IronBars,
            pymclevel.materials.alphaMaterials.MonsterSpawner,
            pymclevel.materials.alphaMaterials.Vines,
            pymclevel.materials.alphaMaterials.Fire,
            pymclevel.materials.alphaMaterials.Trapdoor,
            pymclevel.materials.alphaMaterials.Lever,
            pymclevel.materials.alphaMaterials.BrewingStand,

        ]
        for b in transparentMaterials:
            mats[b.ID] = materialCount
            materialCount += 1

    hiddenOreMaterials = numpy.arange(pymclevel.materials.id_limit, dtype='uint8')
    hiddenOreMaterials[2] = 1  # don't show boundaries between dirt,grass,sand,gravel,stone
    hiddenOreMaterials[3] = 1
    hiddenOreMaterials[12] = 1
    hiddenOreMaterials[13] = 1

    roughMaterials = numpy.ones((pymclevel.materials.id_limit,), dtype='uint8')
    roughMaterials[0] = 0
    addTransparentMaterials(None, roughMaterials, 2)

    def calcFacesForChunkRenderer(self, cr):
        if 0 == len(cr.invalidLayers):
#            layers = set(br.layer for br in cr.blockRenderers)
#            assert set() == cr.visibleLayers.difference(layers)

            return

        lod = cr.detailLevel
        cx, cz = cr.chunkPosition
        level = cr.renderer.level
        try:
            chunk = level.getChunk(cx, cz)
        except Exception, e:
            logging.warn(u"Error reading chunk: %s", e)
            yield
            return

        yield
        brs = []
        classes = [
            TileEntityRenderer,
            MonsterRenderer,
            ItemRenderer,
            TileTicksRenderer,
            TerrainPopulatedRenderer,
            LowDetailBlockRenderer,
            OverheadBlockRenderer,
        ]
        existingBlockRenderers = dict(((type(b), b) for b in cr.blockRenderers))

        for blockRendererClass in classes:
            if cr.detailLevel not in blockRendererClass.detailLevels:
                continue
            if blockRendererClass.layer not in cr.visibleLayers:
                continue
            if blockRendererClass.layer not in cr.invalidLayers:
                if blockRendererClass in existingBlockRenderers:
                    brs.append(existingBlockRenderers[blockRendererClass])

                continue

            br = blockRendererClass(self)
            br.detailLevel = cr.detailLevel

            for _ in br.makeChunkVertices(chunk):
                yield
            brs.append(br)

        blockRenderers = []

        # Recalculate high detail blocks if needed, otherwise retain the high detail renderers
        if lod == 0 and Layer.Blocks in cr.invalidLayers:
            for _ in self.calcHighDetailFaces(cr, blockRenderers):
                yield
        else:
            blockRenderers.extend(br for br in cr.blockRenderers if type(br) not in classes)

        # Add the layer renderers
        blockRenderers.extend(brs)
        cr.blockRenderers = blockRenderers

        cr.vertexArraysDone()
        raise StopIteration

    def getNeighboringChunks(self, chunk):
        cx, cz = chunk.chunkPosition
        level = chunk.world

        neighboringChunks = {}
        for dir, dx, dz in ((pymclevel.faces.FaceXDecreasing, -1, 0),
                           (pymclevel.faces.FaceXIncreasing, 1, 0),
                           (pymclevel.faces.FaceZDecreasing, 0, -1),
                           (pymclevel.faces.FaceZIncreasing, 0, 1)):
            if not level.containsChunk(cx + dx, cz + dz):
                neighboringChunks[dir] = pymclevel.infiniteworld.ZeroChunk(level.Height)
            else:
                # if not level.chunkIsLoaded(cx+dx,cz+dz):
                #    raise StopIteration
                try:
                    neighboringChunks[dir] = level.getChunk(cx + dx, cz + dz)
                except (EnvironmentError, pymclevel.mclevelbase.ChunkNotPresent, pymclevel.mclevelbase.ChunkMalformed):
                    neighboringChunks[dir] = pymclevel.infiniteworld.ZeroChunk(level.Height)
        return neighboringChunks

    def getAreaBlocks(self, chunk, neighboringChunks):
        chunkWidth, chunkLength, chunkHeight = chunk.Blocks.shape

        areaBlocks = numpy.zeros((chunkWidth + 2, chunkLength + 2, chunkHeight + 2), numpy.uint16)
        areaBlocks[1:-1, 1:-1, 1:-1] = chunk.Blocks
        areaBlocks[:1, 1:-1, 1:-1] = neighboringChunks[pymclevel.faces.FaceXDecreasing].Blocks[-1:, :chunkLength, :chunkHeight]
        areaBlocks[-1:, 1:-1, 1:-1] = neighboringChunks[pymclevel.faces.FaceXIncreasing].Blocks[:1, :chunkLength, :chunkHeight]
        areaBlocks[1:-1, :1, 1:-1] = neighboringChunks[pymclevel.faces.FaceZDecreasing].Blocks[:chunkWidth, -1:, :chunkHeight]
        areaBlocks[1:-1, -1:, 1:-1] = neighboringChunks[pymclevel.faces.FaceZIncreasing].Blocks[:chunkWidth, :1, :chunkHeight]
        return areaBlocks

    def getFacingBlockIndices(self, areaBlocks, areaBlockMats):
        facingBlockIndices = [None] * 6

        exposedFacesX = (areaBlockMats[:-1, 1:-1, 1:-1] != areaBlockMats[1:, 1:-1, 1:-1])

        facingBlockIndices[pymclevel.faces.FaceXDecreasing] = exposedFacesX[:-1]
        facingBlockIndices[pymclevel.faces.FaceXIncreasing] = exposedFacesX[1:]

        exposedFacesZ = (areaBlockMats[1:-1, :-1, 1:-1] != areaBlockMats[1:-1, 1:, 1:-1])

        facingBlockIndices[pymclevel.faces.FaceZDecreasing] = exposedFacesZ[:, :-1]
        facingBlockIndices[pymclevel.faces.FaceZIncreasing] = exposedFacesZ[:, 1:]

        exposedFacesY = (areaBlockMats[1:-1, 1:-1, :-1] != areaBlockMats[1:-1, 1:-1, 1:])

        facingBlockIndices[pymclevel.faces.FaceYDecreasing] = exposedFacesY[:, :, :-1]
        facingBlockIndices[pymclevel.faces.FaceYIncreasing] = exposedFacesY[:, :, 1:]
        return facingBlockIndices

    def getAreaBlockLights(self, chunk, neighboringChunks):
        chunkWidth, chunkLength, chunkHeight = chunk.Blocks.shape
        lights = chunk.BlockLight
        skyLight = chunk.SkyLight
        finalLight = self.whiteLight

        if lights != None:
            finalLight = lights
        if skyLight != None:
            finalLight = numpy.maximum(skyLight, lights)

        areaBlockLights = numpy.ones((chunkWidth + 2, chunkLength + 2, chunkHeight + 2), numpy.uint8)
        areaBlockLights[:] = 15

        areaBlockLights[1:-1, 1:-1, 1:-1] = finalLight

        nc = neighboringChunks[pymclevel.faces.FaceXDecreasing]
        numpy.maximum(nc.SkyLight[-1:, :chunkLength, :chunkHeight],
                nc.BlockLight[-1:, :chunkLength, :chunkHeight],
                areaBlockLights[0:1, 1:-1, 1:-1])

        nc = neighboringChunks[pymclevel.faces.FaceXIncreasing]
        numpy.maximum(nc.SkyLight[:1, :chunkLength, :chunkHeight],
                nc.BlockLight[:1, :chunkLength, :chunkHeight],
                areaBlockLights[-1:, 1:-1, 1:-1])

        nc = neighboringChunks[pymclevel.faces.FaceZDecreasing]
        numpy.maximum(nc.SkyLight[:chunkWidth, -1:, :chunkHeight],
                nc.BlockLight[:chunkWidth, -1:, :chunkHeight],
                areaBlockLights[1:-1, 0:1, 1:-1])

        nc = neighboringChunks[pymclevel.faces.FaceZIncreasing]
        numpy.maximum(nc.SkyLight[:chunkWidth, :1, :chunkHeight],
                nc.BlockLight[:chunkWidth, :1, :chunkHeight],
                areaBlockLights[1:-1, -1:, 1:-1])

        minimumLight = 4
        # areaBlockLights[areaBlockLights<minimumLight]=minimumLight
        numpy.clip(areaBlockLights, minimumLight, 16, areaBlockLights)

        return areaBlockLights

    def calcHighDetailFaces(self, cr, blockRenderers):  # ForChunk(self, chunkPosition = (0,0), level = None, alpha = 1.0):
        """ calculate the geometry for a chunk renderer from its blockMats, data,
        and lighting array. fills in the cr's blockRenderers with verts
        for each block facing and material"""

        # chunkBlocks and chunkLights shall be indexed [x,z,y] to follow infdev's convention
        cx, cz = cr.chunkPosition
        level = cr.renderer.level

        chunk = level.getChunk(cx, cz)
        neighboringChunks = self.getNeighboringChunks(chunk)

        areaBlocks = self.getAreaBlocks(chunk, neighboringChunks)
        yield

        areaBlockLights = self.getAreaBlockLights(chunk, neighboringChunks)
        yield

        slabs = areaBlocks == pymclevel.materials.alphaMaterials.StoneSlab.ID
        if slabs.any():
            areaBlockLights[slabs] = areaBlockLights[:, :, 1:][slabs[:, :, :-1]]
        yield

        showHiddenOres = cr.renderer.showHiddenOres
        if showHiddenOres:
            facingMats = self.hiddenOreMaterials[areaBlocks]
        else:
            facingMats = self.exposedMaterialMap[areaBlocks]

        yield

        if self.roughGraphics:
            areaBlockMats = self.roughMaterials[areaBlocks]
        else:
            areaBlockMats = self.materialMap[areaBlocks]

        facingBlockIndices = self.getFacingBlockIndices(areaBlocks, facingMats)
        yield

        for i in self.computeGeometry(chunk, areaBlockMats, facingBlockIndices, areaBlockLights, cr, blockRenderers):
            yield

    def computeGeometry(self, chunk, areaBlockMats, facingBlockIndices, areaBlockLights, chunkRenderer, blockRenderers):
        blocks, blockData = chunk.Blocks, chunk.Data
        blockData = blockData & 0xf
        blockMaterials = areaBlockMats[1:-1, 1:-1, 1:-1]
        if self.roughGraphics:
            blockMaterials.clip(0, 1, blockMaterials)

        sx = sz = slice(0, 16)
        asx = asz = slice(0, 18)

        for y in range(0, chunk.world.Height, 16):
            sy = slice(y, y + 16)
            asy = slice(y, y + 18)

            for _i in self.computeCubeGeometry(
                    y,
                    blockRenderers,
                    blocks[sx, sz, sy],
                    blockData[sx, sz, sy],
                    chunk.materials,
                    blockMaterials[sx, sz, sy],
                    [f[sx, sz, sy] for f in facingBlockIndices],
                    areaBlockLights[asx, asz, asy],
                    chunkRenderer):
                yield

    def computeCubeGeometry(self, y, blockRenderers, blocks, blockData, materials, blockMaterials, facingBlockIndices, areaBlockLights, chunkRenderer):
        materialCounts = numpy.bincount(blockMaterials.ravel())

        def texMap(blocks, blockData=0, direction=slice(None)):
            return materials.blockTextures[blocks, blockData, direction]  # xxx slow

        for blockRendererClass in self.blockRendererClasses:
            mi = blockRendererClass.materialIndex
            if mi >= len(materialCounts) or materialCounts[mi] == 0:
                continue

            blockRenderer = blockRendererClass(self)
            blockRenderer.y = y
            blockRenderer.materials = materials
            for _ in blockRenderer.makeVertices(facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
                yield
            blockRenderers.append(blockRenderer)

            yield

    def makeTemplate(self, direction, blockIndices):
        return self.precomputedVertices[direction][blockIndices]


class Layer:
    Blocks = "Blocks"
    Entities = "Entities"
    Monsters = "Monsters"
    Items = "Items"
    TileEntities = "TileEntities"
    TileTicks = "TileTicks"
    TerrainPopulated = "TerrainPopulated"
    AllLayers = (Blocks, Entities, Monsters, Items, TileEntities, TileTicks, TerrainPopulated)


class BlockRenderer(object):
    # vertexArrays = None
    detailLevels = (0,)
    layer = Layer.Blocks
    directionOffsets = {
        pymclevel.faces.FaceXDecreasing: numpy.s_[:-2, 1:-1, 1:-1],
        pymclevel.faces.FaceXIncreasing: numpy.s_[2:, 1:-1, 1:-1],
        pymclevel.faces.FaceYDecreasing: numpy.s_[1:-1, 1:-1, :-2],
        pymclevel.faces.FaceYIncreasing: numpy.s_[1:-1, 1:-1, 2:],
        pymclevel.faces.FaceZDecreasing: numpy.s_[1:-1, :-2, 1:-1],
        pymclevel.faces.FaceZIncreasing: numpy.s_[1:-1, 2:, 1:-1],
    }
    renderstate = ChunkCalculator.renderstateAlphaTest

    def __init__(self, cc):
        self.makeTemplate = cc.makeTemplate
        self.chunkCalculator = cc
        self.vertexArrays = []

        pass

    @classmethod
    def getBlocktypes(cls, mats):
        return cls.blocktypes

    def setAlpha(self, alpha):
        "alpha is an unsigned byte value"
        for a in self.vertexArrays:
            a.view('uint8')[_RGBA][..., 3] = alpha

    def bufferSize(self):
        return sum(a.size for a in self.vertexArrays) * 4

    def getMaterialIndices(self, blockMaterials):
        return blockMaterials == self.materialIndex

    def makeVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        arrays = []
        materialIndices = self.getMaterialIndices(blockMaterials)
        yield

        blockLight = areaBlockLights[1:-1, 1:-1, 1:-1]

        for (direction, exposedFaceIndices) in enumerate(facingBlockIndices):
            facingBlockLight = areaBlockLights[self.directionOffsets[direction]]
            vertexArray = self.makeFaceVertices(direction, materialIndices, exposedFaceIndices, blocks, blockData, blockLight, facingBlockLight, texMap)
            yield
            if len(vertexArray):
                arrays.append(vertexArray)
        self.vertexArrays = arrays

    def makeArrayList(self, chunkPosition, showRedraw):
        l = gl.glGenLists(1)
        GL.glNewList(l, GL.GL_COMPILE)
        self.drawArrays(chunkPosition, showRedraw)
        GL.glEndList()
        return l

    def drawArrays(self, chunkPosition, showRedraw):
        cx, cz = chunkPosition
        y = 0
        if hasattr(self, 'y'):
            y = self.y
        with gl.glPushMatrix(GL.GL_MODELVIEW):
            GL.glTranslate(cx << 4, y, cz << 4)

            if showRedraw:
                GL.glColor(1.0, 0.25, 0.25, 1.0)

            self.drawVertices()

    def drawVertices(self):
        if self.vertexArrays:
            for buf in self.vertexArrays:
                self.drawFaceVertices(buf)

    def drawFaceVertices(self, buf):
        if 0 == len(buf):
            return
        stride = elementByteLength

        GL.glVertexPointer(3, GL.GL_FLOAT, stride, (buf.ravel()))
        GL.glTexCoordPointer(2, GL.GL_FLOAT, stride, (buf.ravel()[3:]))
        GL.glColorPointer(4, GL.GL_UNSIGNED_BYTE, stride, (buf.view(dtype=numpy.uint8).ravel()[20:]))

        GL.glDrawArrays(GL.GL_QUADS, 0, len(buf) * 4)


class EntityRendererGeneric(BlockRenderer):
    renderstate = ChunkCalculator.renderstateEntity
    detailLevels = (0, 1, 2)

    def drawFaceVertices(self, buf):
        if 0 == len(buf):
            return
        stride = elementByteLength

        GL.glVertexPointer(3, GL.GL_FLOAT, stride, (buf.ravel()))
        GL.glTexCoordPointer(2, GL.GL_FLOAT, stride, (buf.ravel()[3:]))
        GL.glColorPointer(4, GL.GL_UNSIGNED_BYTE, stride, (buf.view(dtype=numpy.uint8).ravel()[20:]))

        GL.glDepthMask(False)

        GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_LINE)

        GL.glLineWidth(2.0)
        GL.glDrawArrays(GL.GL_QUADS, 0, len(buf) * 4)

        GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)

        GL.glPolygonOffset(DepthOffset.TerrainWire, DepthOffset.TerrainWire)
        with gl.glEnable(GL.GL_POLYGON_OFFSET_FILL, GL.GL_DEPTH_TEST):
            GL.glDrawArrays(GL.GL_QUADS, 0, len(buf) * 4)
        GL.glDepthMask(True)

    def _computeVertices(self, positions, colors, offset=False, chunkPosition=(0, 0)):
        cx, cz = chunkPosition
        x = cx << 4
        z = cz << 4

        vertexArray = numpy.zeros(shape=(len(positions), 6, 4, 6), dtype='float32')
        if len(positions):
            positions = numpy.array(positions)
            positions[:, (0, 2)] -= (x, z)
            if offset:
                positions -= 0.5

            vertexArray.view('uint8')[_RGBA] = colors
            vertexArray[_XYZ] = positions[:, numpy.newaxis, numpy.newaxis, :]
            vertexArray[_XYZ] += faceVertexTemplates[_XYZ]
            vertexArray.shape = (len(positions) * 6, 4, 6)
        return vertexArray


class TileEntityRenderer(EntityRendererGeneric):
    layer = Layer.TileEntities

    def makeChunkVertices(self, chunk):
        tilePositions = []
        for i, ent in enumerate(chunk.TileEntities):
            if i % 10 == 0:
                yield
            if not 'x' in ent:
                continue
            tilePositions.append(pymclevel.TileEntity.pos(ent))
        tiles = self._computeVertices(tilePositions, (0xff, 0xff, 0x33, 0x44), chunkPosition=chunk.chunkPosition)
        yield
        self.vertexArrays = [tiles]


class BaseEntityRenderer(EntityRendererGeneric):
    pass


class MonsterRenderer(BaseEntityRenderer):
    layer = Layer.Entities  # xxx Monsters
    notMonsters = set(["Item", "XPOrb", "Painting"])

    def makeChunkVertices(self, chunk):
        monsterPositions = []
        for i, ent in enumerate(chunk.Entities):
            if i % 10 == 0:
                yield
            id = ent["id"].value
            if id in self.notMonsters:
                continue

            monsterPositions.append(pymclevel.Entity.pos(ent))

        monsters = self._computeVertices(monsterPositions,
                                         (0xff, 0x22, 0x22, 0x44),
                                         offset=True,
                                         chunkPosition=chunk.chunkPosition)
        yield
        self.vertexArrays = [monsters]


class EntityRenderer(BaseEntityRenderer):
    def makeChunkVertices(self, chunk):
        yield
#        entityPositions = []
#        for i, ent in enumerate(chunk.Entities):
#            if i % 10 == 0:
#                yield
#            entityPositions.append(pymclevel.Entity.pos(ent))
#
#        entities = self._computeVertices(entityPositions, (0x88, 0x00, 0x00, 0x66), offset=True, chunkPosition=chunk.chunkPosition)
#        yield
#        self.vertexArrays = [entities]


class ItemRenderer(BaseEntityRenderer):
    layer = Layer.Items

    def makeChunkVertices(self, chunk):
        entityPositions = []
        entityColors = []
        colorMap = {
            "Item": (0x22, 0xff, 0x22, 0x5f),
            "XPOrb": (0x88, 0xff, 0x88, 0x5f),
            "Painting": (134, 96, 67, 0x5f),
        }
        for i, ent in enumerate(chunk.Entities):
            if i % 10 == 0:
                yield
            color = colorMap.get(ent["id"].value)
            if color is None:
                continue

            entityPositions.append(pymclevel.Entity.pos(ent))
            entityColors.append(color)

        entities = self._computeVertices(entityPositions, numpy.array(entityColors, dtype='uint8')[:, numpy.newaxis, numpy.newaxis], offset=True, chunkPosition=chunk.chunkPosition)
        yield
        self.vertexArrays = [entities]


class TileTicksRenderer(EntityRendererGeneric):
    layer = Layer.TileTicks

    def makeChunkVertices(self, chunk):
        if chunk.root_tag and "Level" in chunk.root_tag and "TileTicks" in chunk.root_tag["Level"]:
            ticks = chunk.root_tag["Level"]["TileTicks"]
            if len(ticks):
                self.vertexArrays.append(self._computeVertices([[t[i].value for i in "xyz"] for t in ticks],
                                                               (0xff, 0xff, 0xff, 0x44),
                                                               chunkPosition=chunk.chunkPosition))

        yield


class TerrainPopulatedRenderer(EntityRendererGeneric):
    layer = Layer.TerrainPopulated
    vertexTemplate = numpy.zeros((6, 4, 6), 'float32')
    vertexTemplate[_XYZ] = faceVertexTemplates[_XYZ]
    vertexTemplate[_XYZ] *= (16, 128, 16)
    color = (255, 200, 155)
    vertexTemplate.view('uint8')[_RGBA] = color + (72,)

    def drawFaceVertices(self, buf):
        if 0 == len(buf):
            return
        stride = elementByteLength

        GL.glVertexPointer(3, GL.GL_FLOAT, stride, (buf.ravel()))
        GL.glTexCoordPointer(2, GL.GL_FLOAT, stride, (buf.ravel()[3:]))
        GL.glColorPointer(4, GL.GL_UNSIGNED_BYTE, stride, (buf.view(dtype=numpy.uint8).ravel()[20:]))

        GL.glDepthMask(False)

        # GL.glDrawArrays(GL.GL_QUADS, 0, len(buf) * 4)
        GL.glDisable(GL.GL_CULL_FACE)

        with gl.glEnable(GL.GL_DEPTH_TEST):
            GL.glDrawArrays(GL.GL_QUADS, 0, len(buf) * 4)

        GL.glEnable(GL.GL_CULL_FACE)

        GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_LINE)

        GL.glLineWidth(1.0)
        GL.glDrawArrays(GL.GL_QUADS, 0, len(buf) * 4)
        GL.glLineWidth(2.0)
        with gl.glEnable(GL.GL_DEPTH_TEST):
            GL.glDrawArrays(GL.GL_QUADS, 0, len(buf) * 4)
        GL.glLineWidth(1.0)

        GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)
        GL.glDepthMask(True)

#        GL.glPolygonOffset(DepthOffset.TerrainWire, DepthOffset.TerrainWire)
#        with gl.glEnable(GL.GL_POLYGON_OFFSET_FILL, GL.GL_DEPTH_TEST):
#            GL.glDrawArrays(GL.GL_QUADS, 0, len(buf) * 4)
#

    def makeChunkVertices(self, chunk):
        neighbors = self.chunkCalculator.getNeighboringChunks(chunk)

        def getpop(ch):
            return getattr(ch, "TerrainPopulated", True)

        pop = getpop(chunk)
        yield
        if pop:
            return

        visibleFaces = [
            getpop(neighbors[pymclevel.faces.FaceXIncreasing]),
            getpop(neighbors[pymclevel.faces.FaceXDecreasing]),
            True,
            True,
            getpop(neighbors[pymclevel.faces.FaceZIncreasing]),
            getpop(neighbors[pymclevel.faces.FaceZDecreasing]),
        ]
        visibleFaces = numpy.array(visibleFaces, dtype='bool')
        verts = self.vertexTemplate[visibleFaces]
        self.vertexArrays.append(verts)

        yield


class LowDetailBlockRenderer(BlockRenderer):
    renderstate = ChunkCalculator.renderstateLowDetail
    detailLevels = (1,)

    def drawFaceVertices(self, buf):
        if not len(buf):
            return
        stride = 16

        GL.glVertexPointer(3, GL.GL_FLOAT, stride, numpy.ravel(buf.ravel()))
        GL.glColorPointer(4, GL.GL_UNSIGNED_BYTE, stride, (buf.view(dtype='uint8').ravel()[12:]))

        GL.glDisableClientState(GL.GL_TEXTURE_COORD_ARRAY)
        GL.glDrawArrays(GL.GL_QUADS, 0, len(buf) * 4)
        GL.glEnableClientState(GL.GL_TEXTURE_COORD_ARRAY)

    def setAlpha(self, alpha):
        for va in self.vertexArrays:
            va.view('uint8')[..., -1] = alpha

    def makeChunkVertices(self, ch):
        step = 1

        level = ch.world
        vertexArrays = []
        blocks = ch.Blocks
        heightMap = ch.HeightMap

        heightMap = heightMap[::step, ::step]
        blocks = blocks[::step, ::step]

        if 0 in blocks.shape:
            return

        chunkWidth, chunkLength, chunkHeight = blocks.shape
        blockIndices = numpy.zeros((chunkWidth, chunkLength, chunkHeight), bool)

        gridaxes = list(numpy.indices((chunkWidth, chunkLength)))
        h = numpy.swapaxes(heightMap - 1, 0, 1)[:chunkWidth, :chunkLength]
        numpy.clip(h, 0, chunkHeight - 1, out=h)

        gridaxes = [gridaxes[0], gridaxes[1], h]

        depths = numpy.zeros((chunkWidth, chunkLength), dtype='uint16')
        depths[1:-1, 1:-1] = reduce(numpy.minimum, (h[1:-1, :-2], h[1:-1, 2:], h[:-2, 1:-1]), h[2:, 1:-1])
        yield

        try:
            topBlocks = blocks[gridaxes]
            nonAirBlocks = (topBlocks != 0)
            blockIndices[gridaxes] = nonAirBlocks
            h += 1
            numpy.clip(h, 0, chunkHeight - 1, out=h)
            overblocks = blocks[gridaxes][nonAirBlocks].ravel()

        except ValueError, e:
            raise ValueError(str(e.args) + "Chunk shape: {0}".format(blockIndices.shape), sys.exc_info()[-1])

        if nonAirBlocks.any():
            blockTypes = blocks[blockIndices]

            flatcolors = level.materials.flatColors[blockTypes, ch.Data[blockIndices] & 0xf][:, numpy.newaxis, :]
            # flatcolors[:,:,:3] *= (0.6 + (h * (0.4 / float(chunkHeight-1)))) [topBlocks != 0][:, numpy.newaxis, numpy.newaxis]
            x, z, y = blockIndices.nonzero()

            yield
            vertexArray = numpy.zeros((len(x), 4, 4), dtype='float32')
            vertexArray[_XYZ][..., 0] = x[:, numpy.newaxis]
            vertexArray[_XYZ][..., 1] = y[:, numpy.newaxis]
            vertexArray[_XYZ][..., 2] = z[:, numpy.newaxis]

            va0 = numpy.array(vertexArray)

            va0[..., :3] += faceVertexTemplates[pymclevel.faces.FaceYIncreasing, ..., :3]

            overmask = overblocks > 0
            flatcolors[overmask] = level.materials.flatColors[:, 0][overblocks[overmask]][:, numpy.newaxis]

            if self.detailLevel == 2:
                heightfactor = (y / float(2.0 * ch.world.Height)) + 0.5
                flatcolors[..., :3] *= heightfactor[:, numpy.newaxis, numpy.newaxis]

            _RGBA = numpy.s_[..., 12:16]
            va0.view('uint8')[_RGBA] = flatcolors

            va0[_XYZ][:, :, 0] *= step
            va0[_XYZ][:, :, 2] *= step

            yield
            if self.detailLevel == 2:
                self.vertexArrays = [va0]
                return

            va1 = numpy.array(vertexArray)
            va1[..., :3] += faceVertexTemplates[pymclevel.faces.FaceXIncreasing, ..., :3]

            va1[_XYZ][:, (0, 1), 1] = depths[nonAirBlocks].ravel()[:, numpy.newaxis]  # stretch to floor
            va1[_XYZ][:, (1, 2), 0] -= 1.0  # turn diagonally
            va1[_XYZ][:, (2, 3), 1] -= 0.5  # drop down to prevent intersection pixels

            va1[_XYZ][:, :, 0] *= step
            va1[_XYZ][:, :, 2] *= step

            flatcolors *= 0.8

            va1.view('uint8')[_RGBA] = flatcolors
            grassmask = topBlocks[nonAirBlocks] == 2
            # color grass sides with dirt's color
            va1.view('uint8')[_RGBA][grassmask] = level.materials.flatColors[:, 0][[3]][:, numpy.newaxis]

            va2 = numpy.array(va1)
            va2[_XYZ][:, (1, 2), 0] += step
            va2[_XYZ][:, (0, 3), 0] -= step

            vertexArrays = [va1, va2, va0]

        self.vertexArrays = vertexArrays


class OverheadBlockRenderer(LowDetailBlockRenderer):
    detailLevels = (2,)


class GenericBlockRenderer(BlockRenderer):
    renderstate = ChunkCalculator.renderstateAlphaTest

    materialIndex = 1

    def makeGenericVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        vertexArrays = []
        materialIndices = self.getMaterialIndices(blockMaterials)
        yield

        for (direction, exposedFaceIndices) in enumerate(facingBlockIndices):
            facingBlockLight = areaBlockLights[self.directionOffsets[direction]]
            blockIndices = materialIndices & exposedFaceIndices

            theseBlocks = blocks[blockIndices]
            bdata = blockData[blockIndices]

            vertexArray = self.makeTemplate(direction, blockIndices)
            if not len(vertexArray):
                continue

            def setTexture():
                vertexArray[_ST] += texMap(theseBlocks, bdata, direction)[:, numpy.newaxis, 0:2]
            setTexture()

            def setGrassColors():
                grass = theseBlocks == pymclevel.materials.alphaMaterials.Grass.ID
                vertexArray.view('uint8')[_RGB][grass] *= self.grassColor

            def getBlockLight():
                return facingBlockLight[blockIndices]

            def setColors():
                vertexArray.view('uint8')[_RGB] *= getBlockLight()[..., numpy.newaxis, numpy.newaxis]
                if self.materials.name in ("Alpha", "Pocket"):
                    if direction == pymclevel.faces.FaceYIncreasing:
                        setGrassColors()
                # leaves = theseBlocks == pymclevel.materials.alphaMaterials.Leaves.ID
                # vertexArray.view('uint8')[_RGBA][leaves] *= [0.15, 0.88, 0.15, 1.0]
#                snow = theseBlocks == pymclevel.materials.alphaMaterials.SnowLayer.ID
#                if direction == pymclevel.faces.FaceYIncreasing:
#                    vertexArray[_XYZ][snow, ...,1] -= 0.875
#
#                if direction != pymclevel.faces.FaceYIncreasing and direction != pymclevel.faces.FaceYDecreasing:
#                    vertexArray[_XYZ][snow, ...,2:4,1] -= 0.875
#                    vertexArray[_ST][snow, ...,2:4,1] += 14
#
            setColors()
            yield

            vertexArrays.append(vertexArray)

        self.vertexArrays = vertexArrays

    grassColor = grassColorDefault = [0.39, 0.77, 0.23]  # 62C743

    makeVertices = makeGenericVertices


class LeafBlockRenderer(BlockRenderer):
    blocktypes = [18]

    @property
    def renderstate(self):
        if self.chunkCalculator.fastLeaves:
            return ChunkCalculator.renderstatePlain
        else:
            return ChunkCalculator.renderstateAlphaTest

    def makeLeafVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        arrays = []
        materialIndices = self.getMaterialIndices(blockMaterials)
        yield

        if self.materials.name in ("Alpha", "Pocket"):
            if not self.chunkCalculator.fastLeaves:
                blockIndices = materialIndices
                data = blockData[blockIndices]
                data &= 0x3  # ignore decay states
                leaves = (data == 0) | (data == 3)
                pines = (data == pymclevel.materials.alphaMaterials.PineLeaves.blockData)
                birches = (data == pymclevel.materials.alphaMaterials.BirchLeaves.blockData)
                texes = texMap(18, data, 0)
        else:
            blockIndices = materialIndices
            texes = texMap(18, [0], 0)

        for (direction, exposedFaceIndices) in enumerate(facingBlockIndices):
            if self.materials.name in ("Alpha", "Pocket"):
                if self.chunkCalculator.fastLeaves:
                    blockIndices = materialIndices & exposedFaceIndices
                    data = blockData[blockIndices]
                    data &= 0x3  # ignore decay states
                    leaves = (data == 0)
                    pines = (data == pymclevel.materials.alphaMaterials.PineLeaves.blockData)
                    birches = (data == pymclevel.materials.alphaMaterials.BirchLeaves.blockData)
                    type3 = (data == 3)
                    leaves |= type3

                    texes = texMap(18, data, 0)

            facingBlockLight = areaBlockLights[self.directionOffsets[direction]]
            vertexArray = self.makeTemplate(direction, blockIndices)
            if not len(vertexArray):
                continue

            vertexArray[_ST] += texes[:, numpy.newaxis]

            if not self.chunkCalculator.fastLeaves:
                vertexArray[_ST] -= (0x10, 0x0)

            vertexArray.view('uint8')[_RGB] *= facingBlockLight[blockIndices][..., numpy.newaxis, numpy.newaxis]
            if self.materials.name in ("Alpha", "Pocket"):
                vertexArray.view('uint8')[_RGB][leaves] *= self.leafColor
                vertexArray.view('uint8')[_RGB][pines] *= self.pineLeafColor
                vertexArray.view('uint8')[_RGB][birches] *= self.birchLeafColor

            yield
            arrays.append(vertexArray)

        self.vertexArrays = arrays

    leafColor = leafColorDefault = [0x48 / 255., 0xb5 / 255., 0x18 / 255.]  # 48b518
    pineLeafColor = pineLeafColorDefault = [0x61 / 255., 0x99 / 255., 0x61 / 255.]  # 0x619961
    birchLeafColor = birchLeafColorDefault = [0x80 / 255., 0xa7 / 255., 0x55 / 255.]  # 0x80a755

    makeVertices = makeLeafVertices


class PlantBlockRenderer(BlockRenderer):
    @classmethod
    def getBlocktypes(cls, mats):
        # blocktypes = [6, 37, 38, 39, 40, 59, 83]
        # if mats.name != "Classic": blocktypes += [31, 32]  # shrubs, tall grass
        # if mats.name == "Alpha": blocktypes += [115]  # nether wart
        blocktypes = [b.ID for b in mats if b.type in ("DECORATION_CROSS", "NETHER_WART", "CROPS", "STEM")]

        return blocktypes

    renderstate = ChunkCalculator.renderstateAlphaTest

    def makePlantVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        arrays = []
        blockIndices = self.getMaterialIndices(blockMaterials)
        yield

        theseBlocks = blocks[blockIndices]

        bdata = blockData[blockIndices]
        bdata[theseBlocks == 6] &= 0x3  # xxx saplings only
        texes = texMap(blocks[blockIndices], bdata, 0)

        blockLight = areaBlockLights[1:-1, 1:-1, 1:-1]
        lights = blockLight[blockIndices][..., numpy.newaxis, numpy.newaxis]

        colorize = None
        if self.materials.name == "Alpha":
            colorize = (theseBlocks == pymclevel.materials.alphaMaterials.TallGrass.ID) & (bdata != 0)

        for direction in (pymclevel.faces.FaceXIncreasing, pymclevel.faces.FaceXDecreasing, pymclevel.faces.FaceZIncreasing, pymclevel.faces.FaceZDecreasing):
            vertexArray = self.makeTemplate(direction, blockIndices)
            if not len(vertexArray):
                return

            if direction == pymclevel.faces.FaceXIncreasing:
                vertexArray[_XYZ][..., 1:3, 0] -= 1
            if direction == pymclevel.faces.FaceXDecreasing:
                vertexArray[_XYZ][..., 1:3, 0] += 1
            if direction == pymclevel.faces.FaceZIncreasing:
                vertexArray[_XYZ][..., 1:3, 2] -= 1
            if direction == pymclevel.faces.FaceZDecreasing:
                vertexArray[_XYZ][..., 1:3, 2] += 1

            vertexArray[_ST] += texes[:, numpy.newaxis, 0:2]

            vertexArray.view('uint8')[_RGB] = 0xf  # ignore precomputed directional light
            vertexArray.view('uint8')[_RGB] *= lights
            if colorize is not None:
                vertexArray.view('uint8')[_RGB][colorize] *= LeafBlockRenderer.leafColor

            arrays.append(vertexArray)
            yield

        self.vertexArrays = arrays

    makeVertices = makePlantVertices


class TorchBlockRenderer(BlockRenderer):
    blocktypes = [50, 75, 76]
    renderstate = ChunkCalculator.renderstateAlphaTest
    torchOffsetsStraight = [
        [  # FaceXIncreasing
            (-7 / 16., 0, 0),
            (-7 / 16., 0, 0),
            (-7 / 16., 0, 0),
            (-7 / 16., 0, 0),
        ],
        [  # FaceXDecreasing
            (7 / 16., 0, 0),
            (7 / 16., 0, 0),
            (7 / 16., 0, 0),
            (7 / 16., 0, 0),
        ],
        [  # FaceYIncreasing
            (7 / 16., -6 / 16., 7 / 16.),
            (7 / 16., -6 / 16., -7 / 16.),
            (-7 / 16., -6 / 16., -7 / 16.),
            (-7 / 16., -6 / 16., 7 / 16.),
        ],
        [  # FaceYDecreasing
            (7 / 16., 0., 7 / 16.),
            (-7 / 16., 0., 7 / 16.),
            (-7 / 16., 0., -7 / 16.),
            (7 / 16., 0., -7 / 16.),
        ],

        [  # FaceZIncreasing
            (0, 0, -7 / 16.),
            (0, 0, -7 / 16.),
            (0, 0, -7 / 16.),
            (0, 0, -7 / 16.)
        ],
        [  # FaceZDecreasing
            (0, 0, 7 / 16.),
            (0, 0, 7 / 16.),
            (0, 0, 7 / 16.),
            (0, 0, 7 / 16.)
        ],

    ]

    torchOffsetsSouth = [
        [  # FaceXIncreasing
            (-7 / 16., 3 / 16., 0),
            (-7 / 16., 3 / 16., 0),
            (-7 / 16., 3 / 16., 0),
            (-7 / 16., 3 / 16., 0),
        ],
        [  # FaceXDecreasing
            (7 / 16., 3 / 16., 0),
            (7 / 16., 3 / 16., 0),
            (7 / 16., 3 / 16., 0),
            (7 / 16., 3 / 16., 0),
        ],
        [  # FaceYIncreasing
            (7 / 16., -3 / 16., 7 / 16.),
            (7 / 16., -3 / 16., -7 / 16.),
            (-7 / 16., -3 / 16., -7 / 16.),
            (-7 / 16., -3 / 16., 7 / 16.),
        ],
        [  # FaceYDecreasing
            (7 / 16., 3 / 16., 7 / 16.),
            (-7 / 16., 3 / 16., 7 / 16.),
            (-7 / 16., 3 / 16., -7 / 16.),
            (7 / 16., 3 / 16., -7 / 16.),
        ],

        [  # FaceZIncreasing
            (0, 3 / 16., -7 / 16.),
            (0, 3 / 16., -7 / 16.),
            (0, 3 / 16., -7 / 16.),
            (0, 3 / 16., -7 / 16.)
        ],
        [  # FaceZDecreasing
            (0, 3 / 16., 7 / 16.),
            (0, 3 / 16., 7 / 16.),
            (0, 3 / 16., 7 / 16.),
            (0, 3 / 16., 7 / 16.),
        ],

    ]
    torchOffsetsNorth = torchOffsetsWest = torchOffsetsEast = torchOffsetsSouth

    torchOffsets = [
        torchOffsetsStraight,
        torchOffsetsSouth,
        torchOffsetsNorth,
        torchOffsetsWest,
        torchOffsetsEast,
        torchOffsetsStraight,
    ] + [torchOffsetsStraight] * 10

    torchOffsets = numpy.array(torchOffsets, dtype='float32')

    torchOffsets[1][..., 3, :, 0] -= 0.5

    torchOffsets[1][..., 0:2, 0:2, 0] -= 0.5
    torchOffsets[1][..., 4:6, 0:2, 0] -= 0.5
    torchOffsets[1][..., 0:2, 2:4, 0] -= 0.1
    torchOffsets[1][..., 4:6, 2:4, 0] -= 0.1

    torchOffsets[1][..., 2, :, 0] -= 0.25

    torchOffsets[2][..., 3, :, 0] += 0.5
    torchOffsets[2][..., 0:2, 0:2, 0] += 0.5
    torchOffsets[2][..., 4:6, 0:2, 0] += 0.5
    torchOffsets[2][..., 0:2, 2:4, 0] += 0.1
    torchOffsets[2][..., 4:6, 2:4, 0] += 0.1
    torchOffsets[2][..., 2, :, 0] += 0.25

    torchOffsets[3][..., 3, :, 2] -= 0.5
    torchOffsets[3][..., 0:2, 0:2, 2] -= 0.5
    torchOffsets[3][..., 4:6, 0:2, 2] -= 0.5
    torchOffsets[3][..., 0:2, 2:4, 2] -= 0.1
    torchOffsets[3][..., 4:6, 2:4, 2] -= 0.1
    torchOffsets[3][..., 2, :, 2] -= 0.25

    torchOffsets[4][..., 3, :, 2] += 0.5
    torchOffsets[4][..., 0:2, 0:2, 2] += 0.5
    torchOffsets[4][..., 4:6, 0:2, 2] += 0.5
    torchOffsets[4][..., 0:2, 2:4, 2] += 0.1
    torchOffsets[4][..., 4:6, 2:4, 2] += 0.1
    torchOffsets[4][..., 2, :, 2] += 0.25

    upCoords = ((7, 6), (7, 8), (9, 8), (9, 6))
    downCoords = ((7, 14), (7, 16), (9, 16), (9, 14))

    def makeTorchVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        blockIndices = self.getMaterialIndices(blockMaterials)
        torchOffsets = self.torchOffsets[blockData[blockIndices]]
        texes = texMap(blocks[blockIndices], blockData[blockIndices])
        yield
        arrays = []
        for direction in range(6):
            vertexArray = self.makeTemplate(direction, blockIndices)
            if not len(vertexArray):
                return

            vertexArray.view('uint8')[_RGBA] = 0xff
            vertexArray[_XYZ] += torchOffsets[:, direction]
            if direction == pymclevel.faces.FaceYIncreasing:
                vertexArray[_ST] = self.upCoords
            if direction == pymclevel.faces.FaceYDecreasing:
                vertexArray[_ST] = self.downCoords
            vertexArray[_ST] += texes[:, numpy.newaxis, direction]
            arrays.append(vertexArray)
            yield
        self.vertexArrays = arrays

    makeVertices = makeTorchVertices


class RailBlockRenderer(BlockRenderer):
    blocktypes = [pymclevel.materials.alphaMaterials.Rail.ID, pymclevel.materials.alphaMaterials.PoweredRail.ID, pymclevel.materials.alphaMaterials.DetectorRail.ID]
    renderstate = ChunkCalculator.renderstateAlphaTest

    railTextures = numpy.array([
        [(0, 128), (0, 144), (16, 144), (16, 128)],  # east-west
        [(0, 128), (16, 128), (16, 144), (0, 144)],  # north-south
        [(0, 128), (16, 128), (16, 144), (0, 144)],  # south-ascending
        [(0, 128), (16, 128), (16, 144), (0, 144)],  # north-ascending
        [(0, 128), (0, 144), (16, 144), (16, 128)],  # east-ascending
        [(0, 128), (0, 144), (16, 144), (16, 128)],  # west-ascending

        [(0, 112), (0, 128), (16, 128), (16, 112)],  # northeast corner
        [(0, 128), (16, 128), (16, 112), (0, 112)],  # southeast corner
        [(16, 128), (16, 112), (0, 112), (0, 128)],  # southwest corner
        [(16, 112), (0, 112), (0, 128), (16, 128)],  # northwest corner

        [(0, 192), (0, 208), (16, 208), (16, 192)],  # unknown
        [(0, 192), (0, 208), (16, 208), (16, 192)],  # unknown
        [(0, 192), (0, 208), (16, 208), (16, 192)],  # unknown
        [(0, 192), (0, 208), (16, 208), (16, 192)],  # unknown
        [(0, 192), (0, 208), (16, 208), (16, 192)],  # unknown
        [(0, 192), (0, 208), (16, 208), (16, 192)],  # unknown

    ], dtype='float32')
    railTextures -= pymclevel.materials.alphaMaterials.blockTextures[pymclevel.materials.alphaMaterials.Rail.ID, 0, 0]

    railOffsets = numpy.array([
        [0, 0, 0, 0],
        [0, 0, 0, 0],

        [0, 0, 1, 1],  # south-ascending
        [1, 1, 0, 0],  # north-ascending
        [1, 0, 0, 1],  # east-ascending
        [0, 1, 1, 0],  # west-ascending

        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],

        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],

    ], dtype='float32')

    def makeRailVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        direction = pymclevel.faces.FaceYIncreasing
        blockIndices = self.getMaterialIndices(blockMaterials)
        yield

        bdata = blockData[blockIndices]
        railBlocks = blocks[blockIndices]
        tex = texMap(railBlocks, bdata, pymclevel.faces.FaceYIncreasing)[:, numpy.newaxis, :]

        # disable 'powered' or 'pressed' bit for powered and detector rails
        bdata[railBlocks != pymclevel.materials.alphaMaterials.Rail.ID] &= ~0x8

        vertexArray = self.makeTemplate(direction, blockIndices)
        if not len(vertexArray):
            return

        vertexArray[_ST] = self.railTextures[bdata]
        vertexArray[_ST] += tex

        vertexArray[_XYZ][..., 1] -= 0.9
        vertexArray[_XYZ][..., 1] += self.railOffsets[bdata]

        blockLight = areaBlockLights[1:-1, 1:-1, 1:-1]

        vertexArray.view('uint8')[_RGB] *= blockLight[blockIndices][..., numpy.newaxis, numpy.newaxis]
        yield
        self.vertexArrays = [vertexArray]

    makeVertices = makeRailVertices


class LadderBlockRenderer(BlockRenderer):
    blocktypes = [pymclevel.materials.alphaMaterials.Ladder.ID]

    ladderOffsets = numpy.array([
        [(0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)],
        [(0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)],

        [(0, -1, 0.9), (0, 0, -0.1), (0, 0, -0.1), (0, -1, 0.9)],  # facing east
        [(0, 0, 0.1), (0, -1, -.9), (0, -1, -.9), (0, 0, 0.1)],  # facing west
        [(.9, -1, 0), (.9, -1, 0), (-.1, 0, 0), (-.1, 0, 0)],  # north
        [(0.1, 0, 0), (0.1, 0, 0), (-.9, -1, 0), (-.9, -1, 0)],  # south

    ] + [[(0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)]] * 10, dtype='float32')

    ladderTextures = numpy.array([
        [(0, 192), (0, 208), (16, 208), (16, 192)],  # unknown
        [(0, 192), (0, 208), (16, 208), (16, 192)],  # unknown

        [(64, 96), (64, 80), (48, 80), (48, 96), ],  # e
        [(48, 80), (48, 96), (64, 96), (64, 80), ],  # w
        [(48, 96), (64, 96), (64, 80), (48, 80), ],  # n
        [(64, 80), (48, 80), (48, 96), (64, 96), ],  # s

        ] + [[(0, 192), (0, 208), (16, 208), (16, 192)]] * 10, dtype='float32')

    def ladderVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        blockIndices = self.getMaterialIndices(blockMaterials)
        blockLight = areaBlockLights[1:-1, 1:-1, 1:-1]
        yield
        bdata = blockData[blockIndices]

        vertexArray = self.makeTemplate(pymclevel.faces.FaceYIncreasing, blockIndices)
        if not len(vertexArray):
            return

        vertexArray[_ST] = self.ladderTextures[bdata]
        vertexArray[_XYZ] += self.ladderOffsets[bdata]
        vertexArray.view('uint8')[_RGB] *= blockLight[blockIndices][..., numpy.newaxis, numpy.newaxis]

        yield
        self.vertexArrays = [vertexArray]

    makeVertices = ladderVertices


class SnowBlockRenderer(BlockRenderer):
    snowID = 78

    blocktypes = [snowID]

    def makeSnowVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        snowIndices = self.getMaterialIndices(blockMaterials)
        arrays = []
        yield
        for direction, exposedFaceIndices in enumerate(facingBlockIndices):
    # def makeFaceVertices(self, direction, blockIndices, exposedFaceIndices, blocks, blockData, blockLight, facingBlockLight, texMap):
        # return []

            if direction != pymclevel.faces.FaceYIncreasing:
                blockIndices = snowIndices & exposedFaceIndices
            else:
                blockIndices = snowIndices

            facingBlockLight = areaBlockLights[self.directionOffsets[direction]]
            lights = facingBlockLight[blockIndices][..., numpy.newaxis, numpy.newaxis]

            vertexArray = self.makeTemplate(direction, blockIndices)
            if not len(vertexArray):
                continue

            vertexArray[_ST] += texMap([self.snowID], 0, 0)[:, numpy.newaxis, 0:2]
            vertexArray.view('uint8')[_RGB] *= lights

            if direction == pymclevel.faces.FaceYIncreasing:
                vertexArray[_XYZ][..., 1] -= 0.875

            if direction != pymclevel.faces.FaceYIncreasing and direction != pymclevel.faces.FaceYDecreasing:
                vertexArray[_XYZ][..., 2:4, 1] -= 0.875
                vertexArray[_ST][..., 2:4, 1] += 14

            arrays.append(vertexArray)
            yield
        self.vertexArrays = arrays

    makeVertices = makeSnowVertices


class RedstoneBlockRenderer(BlockRenderer):
    blocktypes = [55]

    def redstoneVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        blockIndices = self.getMaterialIndices(blockMaterials)
        yield
        vertexArray = self.makeTemplate(pymclevel.faces.FaceYIncreasing, blockIndices)
        if not len(vertexArray):
            return

        vertexArray[_ST] += pymclevel.materials.alphaMaterials.blockTextures[55, 0, 0]
        vertexArray[_XYZ][..., 1] -= 0.9

        bdata = blockData[blockIndices]

        bdata <<= 3
        # bdata &= 0xe0
        bdata[bdata > 0] |= 0x80

        vertexArray.view('uint8')[_RGBA][..., 0] = bdata[..., numpy.newaxis]
        vertexArray.view('uint8')[_RGBA][..., 0:3] *= [1, 0, 0]

        yield
        self.vertexArrays = [vertexArray]

    makeVertices = redstoneVertices

# button, floor plate, door -> 1-cube features


class FeatureBlockRenderer(BlockRenderer):
#    blocktypes = [pymclevel.materials.alphaMaterials.Button.ID,
#                  pymclevel.materials.alphaMaterials.StoneFloorPlate.ID,
#                  pymclevel.materials.alphaMaterials.WoodFloorPlate.ID,
#                  pymclevel.materials.alphaMaterials.WoodenDoor.ID,
#                  pymclevel.materials.alphaMaterials.IronDoor.ID,
#                  ]
#
    blocktypes = [pymclevel.materials.alphaMaterials.Fence.ID]

    buttonOffsets = [
        [[-14 / 16., 6 / 16., -5 / 16.],
         [-14 / 16., 6 / 16., 5 / 16.],
         [-14 / 16., -7 / 16., 5 / 16.],
         [-14 / 16., -7 / 16., -5 / 16.],
        ],
        [[0 / 16., 6 / 16., 5 / 16.],
         [0 / 16., 6 / 16., -5 / 16.],
         [0 / 16., -7 / 16., -5 / 16.],
         [0 / 16., -7 / 16., 5 / 16.],
        ],

        [[0 / 16., -7 / 16., 5 / 16.],
         [0 / 16., -7 / 16., -5 / 16.],
         [-14 / 16., -7 / 16., -5 / 16.],
         [-14 / 16., -7 / 16., 5 / 16.],
        ],
        [[0 / 16., 6 / 16., 5 / 16.],
         [-14 / 16., 6 / 16., 5 / 16.],
         [-14 / 16., 6 / 16., -5 / 16.],
         [0 / 16., 6 / 16., -5 / 16.],
        ],

        [[0 / 16., 6 / 16., -5 / 16.],
         [-14 / 16., 6 / 16., -5 / 16.],
         [-14 / 16., -7 / 16., -5 / 16.],
         [0 / 16., -7 / 16., -5 / 16.],
        ],
        [[-14 / 16., 6 / 16., 5 / 16.],
         [0 / 16., 6 / 16., 5 / 16.],
         [0 / 16., -7 / 16., 5 / 16.],
         [-14 / 16., -7 / 16., 5 / 16.],
        ],
    ]
    buttonOffsets = numpy.array(buttonOffsets)
    buttonOffsets[buttonOffsets < 0] += 1.0

    dirIndexes = ((3, 2), (-3, 2), (1, 3), (1, 3), (-1, 2), (1, 2))

    def buttonVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        blockIndices = blocks == pymclevel.materials.alphaMaterials.Button.ID
        axes = blockIndices.nonzero()

        vertexArray = numpy.zeros((len(axes[0]), 6, 4, 6), dtype=numpy.float32)
        vertexArray[_XYZ][..., 0] = axes[0][..., numpy.newaxis, numpy.newaxis]
        vertexArray[_XYZ][..., 1] = axes[2][..., numpy.newaxis, numpy.newaxis]
        vertexArray[_XYZ][..., 2] = axes[1][..., numpy.newaxis, numpy.newaxis]

        vertexArray[_XYZ] += self.buttonOffsets
        vertexArray[_ST] = [[0, 0], [0, 16], [16, 16], [16, 0]]
        vertexArray[_ST] += texMap(pymclevel.materials.alphaMaterials.Stone.ID, 0)[numpy.newaxis, :, numpy.newaxis]

        # if direction == 0:
#        for i, j in enumerate(self.dirIndexes[direction]):
#                if j < 0:
#                    j = -j
#                    j -= 1
#                    offs = self.buttonOffsets[direction, ..., j] * 16
#                    offs = 16 - offs
#
#                else:
#                    j -= 1
#                    offs =self.buttonOffsets[direction, ..., j] * 16
#
#                # if i == 1:
#                #
#                #    vertexArray[_ST][...,i] -= offs
#                # else:
#                vertexArray[_ST][...,i] -= offs
#
        vertexArray.view('uint8')[_RGB] = 255
        vertexArray.shape = (len(axes[0]) * 6, 4, 6)

        self.vertexArrays = [vertexArray]

    fenceTemplates = makeVertexTemplates(3 / 8., 0, 3 / 8., 5 / 8., 1, 5 / 8.)

    def fenceVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        fenceMask = blocks == pymclevel.materials.alphaMaterials.Fence.ID
        fenceIndices = fenceMask.nonzero()
        yield

        vertexArray = numpy.zeros((len(fenceIndices[0]), 6, 4, 6), dtype='float32')
        for i in range(3):
            j = (0, 2, 1)[i]

            vertexArray[..., i] = fenceIndices[j][:, numpy.newaxis, numpy.newaxis]  # xxx swap z with y using ^

        vertexArray[..., 0:5] += self.fenceTemplates[..., 0:5]
        vertexArray[_ST] += pymclevel.materials.alphaMaterials.blockTextures[pymclevel.materials.alphaMaterials.WoodPlanks.ID, 0, 0]

        vertexArray.view('uint8')[_RGB] = self.fenceTemplates[..., 5][..., numpy.newaxis]
        vertexArray.view('uint8')[_A] = 0xFF
        vertexArray.view('uint8')[_RGB] *= areaBlockLights[1:-1, 1:-1, 1:-1][fenceIndices][..., numpy.newaxis, numpy.newaxis, numpy.newaxis]
        vertexArray.shape = (vertexArray.shape[0] * 6, 4, 6)
        yield
        self.vertexArrays = [vertexArray]

    makeVertices = fenceVertices


class StairBlockRenderer(BlockRenderer):
    @classmethod
    def getBlocktypes(cls, mats):
        return [a.ID for a in mats.AllStairs]

    # South - FaceXIncreasing
    # North - FaceXDecreasing
    # West - FaceZIncreasing
    # East - FaceZDecreasing
    stairTemplates = numpy.array([makeVertexTemplates(**kw) for kw in [
        # South - FaceXIncreasing
        {"xmin":0.5},
        # North - FaceXDecreasing
        {"xmax":0.5},
        # West - FaceZIncreasing
        {"zmin":0.5},
        # East - FaceZDecreasing
        {"zmax":0.5},
        # Slabtype
        {"ymax":0.5},
        ]
    ])

    def stairVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        arrays = []
        materialIndices = self.getMaterialIndices(blockMaterials)
        yield
        stairBlocks = blocks[materialIndices]
        stairData = blockData[materialIndices]
        stairTop = (stairData >> 2).astype(bool)
        stairData &= 3

        blockLight = areaBlockLights[1:-1, 1:-1, 1:-1]
        x, z, y = materialIndices.nonzero()

        for _ in ("slab", "step"):
            vertexArray = numpy.zeros((len(x), 6, 4, 6), dtype='float32')
            for i in range(3):
                vertexArray[_XYZ][..., i] = (x, y, z)[i][:, numpy.newaxis, numpy.newaxis]

            if _ == "step":
                vertexArray[_XYZST] += self.stairTemplates[4][..., :5]
                vertexArray[_XYZ][..., 1][stairTop] += 0.5
            else:
                vertexArray[_XYZST] += self.stairTemplates[stairData][..., :5]

            vertexArray[_ST] += texMap(stairBlocks, 0)[..., numpy.newaxis, :]

            vertexArray.view('uint8')[_RGB] = self.stairTemplates[4][numpy.newaxis, ..., 5, numpy.newaxis]
            vertexArray.view('uint8')[_RGB] *= 0xf
            vertexArray.view('uint8')[_A] = 0xff

            vertexArray.shape = (len(x) * 6, 4, 6)
            yield
            arrays.append(vertexArray)
        self.vertexArrays = arrays

    makeVertices = stairVertices

class VineBlockRenderer(BlockRenderer):
    blocktypes = [106]

    SouthBit = 1 #FaceZIncreasing
    WestBit = 2 #FaceXDecreasing
    NorthBit = 4 #FaceZDecreasing
    EastBit = 8 #FaceXIncreasing

    renderstate = ChunkCalculator.renderstateVines

    def vineFaceVertices(self, direction, blockIndices, exposedFaceIndices, blocks, blockData, blockLight, facingBlockLight, texMap):

        bdata = blockData[blockIndices]
        blockIndices = numpy.array(blockIndices)
        if direction == pymclevel.faces.FaceZIncreasing:
            blockIndices[blockIndices] = (bdata & 1).astype(bool)
        elif direction == pymclevel.faces.FaceXDecreasing:
            blockIndices[blockIndices] = (bdata & 2).astype(bool)
        elif direction == pymclevel.faces.FaceZDecreasing:
            blockIndices[blockIndices] = (bdata & 4).astype(bool)
        elif direction == pymclevel.faces.FaceXIncreasing:
            blockIndices[blockIndices] = (bdata & 8).astype(bool)
        else:
            return []
        vertexArray = self.makeTemplate(direction, blockIndices)
        if not len(vertexArray):
            return vertexArray

        vertexArray[_ST] += texMap(self.blocktypes[0], [0], direction)[:, numpy.newaxis, 0:2]

        lights = blockLight[blockIndices][..., numpy.newaxis, numpy.newaxis]
        vertexArray.view('uint8')[_RGB] *= lights

        vertexArray.view('uint8')[_RGB] *= LeafBlockRenderer.leafColor

        if direction == pymclevel.faces.FaceZIncreasing:
            vertexArray[_XYZ][..., 2] -= 0.0625
        if direction == pymclevel.faces.FaceXDecreasing:
            vertexArray[_XYZ][..., 0] += 0.0625
        if direction == pymclevel.faces.FaceZDecreasing:
            vertexArray[_XYZ][..., 2] += 0.0625
        if direction == pymclevel.faces.FaceXIncreasing:
            vertexArray[_XYZ][..., 0] -= 0.0625

        return vertexArray

    makeFaceVertices = vineFaceVertices


class SlabBlockRenderer(BlockRenderer):
    blocktypes = [44, 126]

    def slabFaceVertices(self, direction, blockIndices, exposedFaceIndices, blocks, blockData, blockLight, facingBlockLight, texMap):
        if direction != pymclevel.faces.FaceYIncreasing:
            blockIndices = blockIndices & exposedFaceIndices

        lights = facingBlockLight[blockIndices][..., numpy.newaxis, numpy.newaxis]
        bdata = blockData[blockIndices]
        top = (bdata >> 3).astype(bool)
        bdata &= 7

        vertexArray = self.makeTemplate(direction, blockIndices)
        if not len(vertexArray):
            return vertexArray

        vertexArray[_ST] += texMap(blocks[blockIndices], bdata, direction)[:, numpy.newaxis, 0:2]
        vertexArray.view('uint8')[_RGB] *= lights

        if direction == pymclevel.faces.FaceYIncreasing:
            vertexArray[_XYZ][..., 1] -= 0.5

        if direction != pymclevel.faces.FaceYIncreasing and direction != pymclevel.faces.FaceYDecreasing:
            vertexArray[_XYZ][..., 2:4, 1] -= 0.5
            vertexArray[_ST][..., 2:4, 1] += 8

        vertexArray[_XYZ][..., 1][top] += 0.5

        return vertexArray

    makeFaceVertices = slabFaceVertices


class WaterBlockRenderer(BlockRenderer):
    waterID = 9
    blocktypes = [8, waterID]
    renderstate = ChunkCalculator.renderstateWater

    def waterFaceVertices(self, direction, blockIndices, exposedFaceIndices, blocks, blockData, blockLight, facingBlockLight, texMap):
        blockIndices = blockIndices & exposedFaceIndices
        vertexArray = self.makeTemplate(direction, blockIndices)
        vertexArray[_ST] += texMap(self.waterID, 0, 0)[numpy.newaxis, numpy.newaxis]
        vertexArray.view('uint8')[_RGB] *= facingBlockLight[blockIndices][..., numpy.newaxis, numpy.newaxis]
        return vertexArray

    makeFaceVertices = waterFaceVertices


class IceBlockRenderer(BlockRenderer):
    iceID = 79
    blocktypes = [iceID]
    renderstate = ChunkCalculator.renderstateIce

    def iceFaceVertices(self, direction, blockIndices, exposedFaceIndices, blocks, blockData, blockLight, facingBlockLight, texMap):
        blockIndices = blockIndices & exposedFaceIndices
        vertexArray = self.makeTemplate(direction, blockIndices)
        vertexArray[_ST] += texMap(self.iceID, 0, 0)[numpy.newaxis, numpy.newaxis]
        vertexArray.view('uint8')[_RGB] *= facingBlockLight[blockIndices][..., numpy.newaxis, numpy.newaxis]
        return vertexArray

    makeFaceVertices = iceFaceVertices

from glutils import DisplayList


class MCRenderer(object):
    isPreviewer = False

    def __init__(self, level=None, alpha=1.0):
        self.render = True
        self.origin = (0, 0, 0)
        self.rotation = 0

        self.bufferUsage = 0

        self.invalidChunkQueue = deque()
        self._chunkWorker = None
        self.chunkRenderers = {}
        self.loadableChunkMarkers = DisplayList()
        self.visibleLayers = set(Layer.AllLayers)

        self.masterLists = None

        alpha = alpha * 255
        self.alpha = (int(alpha) & 0xff)

        self.chunkStartTime = datetime.now()
        self.oldChunkStartTime = self.chunkStartTime

        self.oldPosition = None

        self.chunkSamples = [timedelta(0, 0, 0)] * 15

        self.chunkIterator = None

        import leveleditor
        Settings = leveleditor.Settings

        Settings.fastLeaves.addObserver(self)

        Settings.roughGraphics.addObserver(self)
        Settings.showHiddenOres.addObserver(self)
        Settings.vertexBufferLimit.addObserver(self)

        Settings.drawEntities.addObserver(self)
        Settings.drawTileEntities.addObserver(self)
        Settings.drawTileTicks.addObserver(self)
        Settings.drawUnpopulatedChunks.addObserver(self, "drawTerrainPopulated")
        Settings.drawMonsters.addObserver(self)
        Settings.drawItems.addObserver(self)

        Settings.showChunkRedraw.addObserver(self, "showRedraw")
        Settings.spaceHeight.addObserver(self)
        Settings.targetFPS.addObserver(self, "targetFPS")

        self.level = level

    chunkClass = ChunkRenderer
    calculatorClass = ChunkCalculator

    minViewDistance = 2
    maxViewDistance = 24

    _viewDistance = 8

    needsRedraw = True

    def toggleLayer(self, val, layer):
        if val:
            self.visibleLayers.add(layer)
        else:
            self.visibleLayers.discard(layer)
        for cr in self.chunkRenderers.itervalues():
            cr.invalidLayers.add(layer)

        self.loadNearbyChunks()

    def layerProperty(layer, default=True):  # @NoSelf
        attr = intern("_draw" + layer)

        def _get(self):
            return getattr(self, attr, default)

        def _set(self, val):
            if val != _get(self):
                setattr(self, attr, val)
                self.toggleLayer(val, layer)

        return property(_get, _set)

    drawEntities = layerProperty(Layer.Entities)
    drawTileEntities = layerProperty(Layer.TileEntities)
    drawTileTicks = layerProperty(Layer.TileTicks)
    drawMonsters = layerProperty(Layer.Monsters)
    drawItems = layerProperty(Layer.Items)
    drawTerrainPopulated = layerProperty(Layer.TerrainPopulated)

    def inSpace(self):
        if self.level is None:
            return True
        h = self.position[1]
        return ((h > self.level.Height + self.spaceHeight) or
                (h <= -self.spaceHeight))

    def chunkDistance(self, cpos):
        camx, camy, camz = self.position

        # if the renderer is offset into the world somewhere, adjust for that
        ox, oy, oz = self.origin
        camx -= ox
        camz -= oz

        camcx = int(numpy.floor(camx)) >> 4
        camcz = int(numpy.floor(camz)) >> 4

        cx, cz = cpos

        return max(abs(cx - camcx), abs(cz - camcz))

    overheadMode = False

    def detailLevelForChunk(self, cpos):
        if self.overheadMode:
            return 2
        if self.isPreviewer:
            w, l, h = self.level.bounds.size
            if w + l < 256:
                return 0

        distance = self.chunkDistance(cpos) - self.viewDistance
        if distance > 0 or self.inSpace():
            return 1
        return 0

    def getViewDistance(self):
        return self._viewDistance

    def setViewDistance(self, vd):
        vd = int(vd) & 0xfffe
        vd = min(max(vd, self.minViewDistance), self.maxViewDistance)
        if vd != self._viewDistance:
            self._viewDistance = vd
            self.viewDistanceChanged()
            # self.invalidateChunkMarkers()

    viewDistance = property(getViewDistance, setViewDistance, None, "View Distance")

    @property
    def effectiveViewDistance(self):
        if self.inSpace():
            return self.viewDistance * 4
        else:
            return self.viewDistance * 2

    def viewDistanceChanged(self):
        self.oldPosition = None  # xxx
        self.discardMasterList()
        self.loadNearbyChunks()
        self.discardChunksOutsideViewDistance()

    maxWorkFactor = 64
    minWorkFactor = 1
    workFactor = 2

    chunkCalculator = None

    _level = None

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, level):
        """ this probably warrants creating a new renderer """
        self.stopWork()

        self._level = level
        self.oldPosition = None
        self.position = (0, 0, 0)
        self.chunkCalculator = None

        self.invalidChunkQueue = deque()

        self.discardAllChunks()

        self.loadableChunkMarkers.invalidate()

        if level:
            self.chunkCalculator = self.calculatorClass(self.level)

            self.oldPosition = None
            level.allChunks

        self.loadNearbyChunks()

    position = (0, 0, 0)

    def loadChunksStartingFrom(self, wx, wz, distance=None):  # world position
        if None is self.level:
            return

        cx = wx >> 4
        cz = wz >> 4

        if distance is None:
            d = self.effectiveViewDistance
        else:
            d = distance

        self.chunkIterator = self.iterateChunks(wx, wz, d * 2)

    def iterateChunks(self, x, z, d):
        cx = x >> 4
        cz = z >> 4

        yield (cx, cz)

        step = dir = 1

        while True:
            for i in range(step):
                cx += dir
                yield (cx, cz)

            for i in range(step):
                cz += dir
                yield (cx, cz)

            step += 1
            if step > d and not self.overheadMode:
                raise StopIteration

            dir = -dir

    chunkIterator = None

    @property
    def chunkWorker(self):
        if self._chunkWorker is None:
            self._chunkWorker = self.makeWorkIterator()
        return self._chunkWorker

    def stopWork(self):
        self._chunkWorker = None

    def discardAllChunks(self):
        self.bufferUsage = 0
        self.forgetAllDisplayLists()
        self.chunkRenderers = {}
        self.oldPosition = None  # xxx force reload

    def discardChunksInBox(self, box):
        self.discardChunks(box.chunkPositions)

    def discardChunksOutsideViewDistance(self):
        if self.overheadMode:
            return

        # print "discardChunksOutsideViewDistance"
        d = self.effectiveViewDistance
        cx = (self.position[0] - self.origin[0]) / 16
        cz = (self.position[2] - self.origin[2]) / 16

        origin = (cx - d, cz - d)
        size = d * 2

        if not len(self.chunkRenderers):
            return
        (ox, oz) = origin
        bytes = 0
        # chunks = numpy.fromiter(self.chunkRenderers.iterkeys(), dtype='int32', count=len(self.chunkRenderers))
        chunks = numpy.fromiter(self.chunkRenderers.iterkeys(), dtype='i,i', count=len(self.chunkRenderers))
        chunks.dtype = 'int32'
        chunks.shape = len(self.chunkRenderers), 2

        if size:
            outsideChunks = chunks[:, 0] < ox - 1
            outsideChunks |= chunks[:, 0] > ox + size
            outsideChunks |= chunks[:, 1] < oz - 1
            outsideChunks |= chunks[:, 1] > oz + size
            chunks = chunks[outsideChunks]

        self.discardChunks(chunks)

    def discardChunks(self, chunks):
        for cx, cz in chunks:
            self.discardChunk(cx, cz)
        self.oldPosition = None  # xxx force reload

    def discardChunk(self, cx, cz):
        " discards the chunk renderer for this chunk and compresses the chunk "
        if (cx, cz) in self.chunkRenderers:
            self.bufferUsage -= self.chunkRenderers[cx, cz].bufferSize
            self.chunkRenderers[cx, cz].forgetDisplayLists()
            del self.chunkRenderers[cx, cz]

    _fastLeaves = False

    @property
    def fastLeaves(self):
        return self._fastLeaves

    @fastLeaves.setter
    def fastLeaves(self, val):
        if self._fastLeaves != bool(val):
            self.discardAllChunks()

        self._fastLeaves = bool(val)

    _roughGraphics = False

    @property
    def roughGraphics(self):
        return self._roughGraphics

    @roughGraphics.setter
    def roughGraphics(self, val):
        if self._roughGraphics != bool(val):
            self.discardAllChunks()

        self._roughGraphics = bool(val)

    _showHiddenOres = False

    @property
    def showHiddenOres(self):
        return self._showHiddenOres

    @showHiddenOres.setter
    def showHiddenOres(self, val):
        if self._showHiddenOres != bool(val):
            self.discardAllChunks()

        self._showHiddenOres = bool(val)

    def invalidateChunk(self, cx, cz, layers=None):
        " marks the chunk for regenerating vertex data and display lists "
        if (cx, cz) in self.chunkRenderers:
            # self.chunkRenderers[(cx,cz)].invalidate()
            # self.bufferUsage -= self.chunkRenderers[(cx, cz)].bufferSize

            self.chunkRenderers[(cx, cz)].invalidate(layers)
            # self.bufferUsage += self.chunkRenderers[(cx, cz)].bufferSize

            self.invalidChunkQueue.append((cx, cz))  # xxx encapsulate

    def invalidateChunksInBox(self, box, layers=None):
        # If the box is at the edge of any chunks, expanding by 1 makes sure the neighboring chunk gets redrawn.
        box = box.expand(1)

        self.invalidateChunks(box.chunkPositions, layers)

    def invalidateEntitiesInBox(self, box):
        self.invalidateChunks(box.chunkPositions, [Layer.Entities])

    def invalidateChunks(self, chunks, layers=None):
        for c in chunks:
            cx, cz = c
            self.invalidateChunk(cx, cz, layers)

        self.stopWork()
        self.discardMasterList()
        self.loadNearbyChunks()

    def invalidateAllChunks(self, layers=None):
        self.invalidateChunks(self.chunkRenderers.iterkeys(), layers)

    def forgetAllDisplayLists(self):
        for cr in self.chunkRenderers.itervalues():
            cr.forgetDisplayLists()

    def invalidateMasterList(self):
        self.discardMasterList()

    shouldRecreateMasterList = True

    def discardMasterList(self):
        self.shouldRecreateMasterList = True

    @property
    def shouldDrawAll(self):
        box = self.level.bounds
        return self.isPreviewer and box.width + box.length < 256

    distanceToChunkReload = 32.0

    def cameraMovedFarEnough(self):
        if self.shouldDrawAll:
            return False
        if self.oldPosition is None:
            return True

        cPos = self.position
        oldPos = self.oldPosition

        cameraDelta = self.distanceToChunkReload

        return any([abs(x - y) > cameraDelta for x, y in zip(cPos, oldPos)])

    def loadVisibleChunks(self):
        """ loads nearby chunks if the camera has moved beyond a certain distance """

        # print "loadVisibleChunks"
        if self.cameraMovedFarEnough():
            if datetime.now() - self.lastVisibleLoad > timedelta(0, 0.5):
                self.discardChunksOutsideViewDistance()
                self.loadNearbyChunks()

                self.oldPosition = self.position
                self.lastVisibleLoad = datetime.now()

    lastVisibleLoad = datetime.now()

    def loadNearbyChunks(self):
        if None is self.level:
            return
        # print "loadNearbyChunks"
        cameraPos = self.position

        if self.shouldDrawAll:
            self.loadAllChunks()
        else:
            # subtract self.origin to load nearby chunks correctly for preview renderers
            self.loadChunksStartingFrom(int(cameraPos[0]) - self.origin[0], int(cameraPos[2]) - self.origin[2])

    def loadAllChunks(self):
        box = self.level.bounds

        self.loadChunksStartingFrom(box.origin[0] + box.width / 2, box.origin[2] + box.length / 2, max(box.width, box.length))

    _floorTexture = None

    @property
    def floorTexture(self):
        if self._floorTexture is None:
            self._floorTexture = Texture(self.makeFloorTex)
        return self._floorTexture

    def makeFloorTex(self):
        color0 = (0xff, 0xff, 0xff, 0x22)
        color1 = (0xff, 0xff, 0xff, 0x44)

        img = numpy.array([color0, color1, color1, color0], dtype='uint8')

        GL.glTexParameter(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)
        GL.glTexParameter(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)

        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, 2, 2, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, img)

    def invalidateChunkMarkers(self):
        self.loadableChunkMarkers.invalidate()

    def _drawLoadableChunkMarkers(self):
        if self.level.chunkCount:
            chunkSet = set(self.level.allChunks)

            sizedChunks = chunkMarkers(chunkSet)

            GL.glPushAttrib(GL.GL_FOG_BIT)
            GL.glDisable(GL.GL_FOG)

            GL.glEnable(GL.GL_BLEND)
            GL.glEnable(GL.GL_POLYGON_OFFSET_FILL)
            GL.glPolygonOffset(DepthOffset.ChunkMarkers, DepthOffset.ChunkMarkers)
            GL.glEnable(GL.GL_DEPTH_TEST)

            GL.glEnableClientState(GL.GL_TEXTURE_COORD_ARRAY)
            GL.glEnable(GL.GL_TEXTURE_2D)
            GL.glColor(1.0, 1.0, 1.0, 1.0)

            self.floorTexture.bind()
            # chunkColor = numpy.zeros(shape=(chunks.shape[0], 4, 4), dtype='float32')
#            chunkColor[:]= (1, 1, 1, 0.15)
#
#            cc = numpy.array(chunks[:,0] + chunks[:,1], dtype='int32')
#            cc &= 1
#            coloredChunks = cc > 0
#            chunkColor[coloredChunks] = (1, 1, 1, 0.28)
#            chunkColor *= 255
#            chunkColor = numpy.array(chunkColor, dtype='uint8')
#
            # GL.glColorPointer(4, GL.GL_UNSIGNED_BYTE, 0, chunkColor)
            for size, chunks in sizedChunks.iteritems():
                if not len(chunks):
                    continue
                chunks = numpy.array(chunks, dtype='float32')

                chunkPosition = numpy.zeros(shape=(chunks.shape[0], 4, 3), dtype='float32')
                chunkPosition[:, :, (0, 2)] = numpy.array(((0, 0), (0, 1), (1, 1), (1, 0)), dtype='float32')
                chunkPosition[:, :, (0, 2)] *= size
                chunkPosition[:, :, (0, 2)] += chunks[:, numpy.newaxis, :]
                chunkPosition *= 16
                GL.glVertexPointer(3, GL.GL_FLOAT, 0, chunkPosition.ravel())
                # chunkPosition *= 8
                GL.glTexCoordPointer(2, GL.GL_FLOAT, 0, (chunkPosition[..., (0, 2)] * 8).ravel())
                GL.glDrawArrays(GL.GL_QUADS, 0, len(chunkPosition) * 4)

            GL.glDisableClientState(GL.GL_TEXTURE_COORD_ARRAY)
            GL.glDisable(GL.GL_TEXTURE_2D)
            GL.glDisable(GL.GL_BLEND)
            GL.glDisable(GL.GL_DEPTH_TEST)
            GL.glDisable(GL.GL_POLYGON_OFFSET_FILL)
            GL.glPopAttrib()

    def drawLoadableChunkMarkers(self):
        if not self.isPreviewer or isinstance(self.level, pymclevel.MCInfdevOldLevel):
            self.loadableChunkMarkers.call(self._drawLoadableChunkMarkers)

        # self.drawCompressedChunkMarkers()

    needsImmediateRedraw = False
    viewingFrustum = None
    if "-debuglists" in sys.argv:
        def createMasterLists(self):
            pass

        def callMasterLists(self):
            for cr in self.chunkRenderers.itervalues():
                cr.debugDraw()
    else:
        def createMasterLists(self):
            if self.shouldRecreateMasterList:
                lists = {}
                chunkLists = defaultdict(list)
                chunksPerFrame = 80
                shouldRecreateAgain = False

                for ch in self.chunkRenderers.itervalues():
                    if chunksPerFrame:
                        if ch.needsRedisplay:
                            chunksPerFrame -= 1
                        ch.makeDisplayLists()
                    else:
                        shouldRecreateAgain = True

                    if ch.renderstateLists:
                        for rs in ch.renderstateLists:
                            chunkLists[rs] += ch.renderstateLists[rs]

                for rs in chunkLists:
                    if len(chunkLists[rs]):
                        lists[rs] = numpy.array(chunkLists[rs], dtype='uint32').ravel()

                # lists = lists[lists.nonzero()]
                self.masterLists = lists
                self.shouldRecreateMasterList = shouldRecreateAgain
                self.needsImmediateRedraw = shouldRecreateAgain

        def callMasterLists(self):
            for renderstate in self.chunkCalculator.renderstates:
                if renderstate not in self.masterLists:
                    continue

                if self.alpha != 0xff and renderstate is not ChunkCalculator.renderstateLowDetail:
                    GL.glEnable(GL.GL_BLEND)
                renderstate.bind()

                GL.glCallLists(self.masterLists[renderstate])

                renderstate.release()
                if self.alpha != 0xff and renderstate is not ChunkCalculator.renderstateLowDetail:
                    GL.glDisable(GL.GL_BLEND)

    errorLimit = 10

    def draw(self):
        self.needsRedraw = False
        if not self.level:
            return
        if not self.chunkCalculator:
            return
        if not self.render:
            return

        chunksDrawn = 0
        if self.level.materials.name in ("Pocket", "Alpha"):
            GL.glMatrixMode(GL.GL_TEXTURE)
            GL.glScalef(1/2., 1/2., 1/2.)

        with gl.glPushMatrix(GL.GL_MODELVIEW):
            dx, dy, dz = self.origin
            GL.glTranslate(dx, dy, dz)

            GL.glEnable(GL.GL_CULL_FACE)
            GL.glEnable(GL.GL_DEPTH_TEST)

            self.level.materials.terrainTexture.bind()
            GL.glEnable(GL.GL_TEXTURE_2D)
            GL.glEnableClientState(GL.GL_TEXTURE_COORD_ARRAY)

            offset = DepthOffset.PreviewRenderer if self.isPreviewer else DepthOffset.Renderer
            GL.glPolygonOffset(offset, offset)
            GL.glEnable(GL.GL_POLYGON_OFFSET_FILL)

            self.createMasterLists()
            try:
                self.callMasterLists()

            except GL.GLError, e:
                if self.errorLimit:
                    self.errorLimit -= 1
                    traceback.print_exc()
                    print e

            GL.glDisable(GL.GL_POLYGON_OFFSET_FILL)

            GL.glDisable(GL.GL_CULL_FACE)
            GL.glDisable(GL.GL_DEPTH_TEST)

            GL.glDisable(GL.GL_TEXTURE_2D)
            GL.glDisableClientState(GL.GL_TEXTURE_COORD_ARRAY)
                # if self.drawLighting:
            self.drawLoadableChunkMarkers()

        if self.level.materials.name in ("Pocket", "Alpha"):
            GL.glMatrixMode(GL.GL_TEXTURE)
            GL.glScalef(2., 2., 2.)

    renderErrorHandled = False

    def addDebugInfo(self, addDebugString):
        addDebugString("BU: {0} MB, ".format(
            self.bufferUsage / 1000000,
             ))

        addDebugString("WQ: {0}, ".format(len(self.invalidChunkQueue)))
        if self.chunkIterator:
            addDebugString("[LR], ")

        addDebugString("CR: {0}, ".format(len(self.chunkRenderers),))

    def next(self):
        self.chunkWorker.next()

    def makeWorkIterator(self):
        ''' does chunk face and vertex calculation work. returns a generator that can be
        iterated over for smaller work units.'''

        try:
            while True:
                if self.level is None:
                    raise StopIteration

                if len(self.invalidChunkQueue) > 1024:
                    self.invalidChunkQueue.clear()

                if len(self.invalidChunkQueue):
                    c = self.invalidChunkQueue[0]
                    for i in self.workOnChunk(c):
                        yield
                    self.invalidChunkQueue.popleft()

                elif self.chunkIterator is None:
                    raise StopIteration

                else:
                    c = self.chunkIterator.next()
                    if self.vertexBufferLimit:
                        while self.bufferUsage > (0.9 * (self.vertexBufferLimit << 20)):
                            deadChunk = None
                            deadDistance = self.chunkDistance(c)
                            for cr in self.chunkRenderers.itervalues():
                                dist = self.chunkDistance(cr.chunkPosition)
                                if dist > deadDistance:
                                    deadChunk = cr
                                    deadDistance = dist

                            if deadChunk is not None:
                                self.discardChunk(*deadChunk.chunkPosition)

                            else:
                                break

                        else:
                            for i in self.workOnChunk(c):
                                yield

                    else:
                        for i in self.workOnChunk(c):
                            yield

                yield

        finally:
            self._chunkWorker = None
            if self.chunkIterator:
                self.chunkIterator = None

    vertexBufferLimit = 384

    def getChunkRenderer(self, c):
        if not (c in self.chunkRenderers):
            cr = self.chunkClass(self, c)
        else:
            cr = self.chunkRenderers[c]

        return cr

    def calcFacesForChunkRenderer(self, cr):
        self.bufferUsage -= cr.bufferSize

        calc = cr.calcFaces()
        work = 0
        for i in calc:
            yield
            work += 1

        self.chunkDone(cr, work)

    def workOnChunk(self, c):
        work = 0

        if self.level.containsChunk(*c):
            cr = self.getChunkRenderer(c)
            if self.viewingFrustum:
                # if not self.viewingFrustum.visible(numpy.array([[c[0] * 16 + 8, 64, c[1] * 16 + 8, 1.0]]), 64).any():
                if not self.viewingFrustum.visible1([c[0] * 16 + 8, self.level.Height / 2, c[1] * 16 + 8, 1.0], self.level.Height / 2):
                    raise StopIteration
                    yield

            faceInfoCalculator = self.calcFacesForChunkRenderer(cr)
            try:
                for result in faceInfoCalculator:
                    work += 1
                    if (work % MCRenderer.workFactor) == 0:
                        yield

                self.invalidateMasterList()

            except Exception, e:
                traceback.print_exc()
                fn = c

                logging.info(u"Skipped chunk {f}: {e}".format(e=e, f=fn))

    redrawChunks = 0

    def chunkDone(self, chunkRenderer, work):
        self.chunkRenderers[chunkRenderer.chunkPosition] = chunkRenderer
        self.bufferUsage += chunkRenderer.bufferSize
        # print "Chunk {0} used {1} work units".format(chunkRenderer.chunkPosition, work)
        if not self.needsRedraw:
            if self.redrawChunks:
                self.redrawChunks -= 1
                if not self.redrawChunks:
                    self.needsRedraw = True

            else:
                self.redrawChunks = 2

        if work > 0:
            self.oldChunkStartTime = self.chunkStartTime
            self.chunkStartTime = datetime.now()
            self.chunkSamples.pop(0)
            self.chunkSamples.append(self.chunkStartTime - self.oldChunkStartTime)

            cx, cz = chunkRenderer.chunkPosition



class PreviewRenderer(MCRenderer):
    isPreviewer = True


def rendermain():
    renderer = MCRenderer()

    renderer.level = pymclevel.mclevel.loadWorld("World1")
    renderer.viewDistance = 6
    renderer.detailLevelForChunk = lambda * x: 0
    start = datetime.now()

    renderer.loadVisibleChunks()

    try:
        while True:
        # for i in range(100):
            renderer.next()
    except StopIteration:
        pass
    except Exception, e:
        traceback.print_exc()
        print repr(e)

    duration = datetime.now() - start
    perchunk = duration / len(renderer.chunkRenderers)
    print "Duration: {0} ({1} chunks per second, {2} per chunk, {3} chunks)".format(duration, 1000000.0 / perchunk.microseconds, perchunk, len(renderer.chunkRenderers))

    # display.init( (640, 480), OPENGL | DOUBLEBUF )
    from mcedit import GLDisplayContext
    from OpenGL import GLU
    cxt = GLDisplayContext()
    import pygame

    # distance = 4000
    GL.glMatrixMode(GL.GL_PROJECTION)
    GL.glLoadIdentity()
    GLU.gluPerspective(35, 640.0 / 480.0, 0.5, 4000.0)
    h = 366

    pos = (0, h, 0)

    look = (0.0001, h - 1, 0.0001)
    up = (0, 1, 0)
    GL.glMatrixMode(GL.GL_MODELVIEW)
    GL.glLoadIdentity()

    GLU.gluLookAt(pos[0], pos[1], pos[2],
                   look[0], look[1], look[2],
                   up[0], up[1], up[2])

    GL.glClearColor(0.0, 0.0, 0.0, 1.0)

    framestart = datetime.now()
    frames = 200
    for i in range(frames):
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        renderer.draw()
        pygame.display.flip()

    delta = datetime.now() - framestart
    seconds = delta.seconds + delta.microseconds / 1000000.0
    print "{0} frames in {1} ({2} per frame, {3} FPS)".format(frames, delta, delta / frames, frames / seconds)

    while True:
        evt = pygame.event.poll()
        if evt.type == pygame.MOUSEBUTTONDOWN:
            break
    # time.sleep(3.0)


import traceback
import cProfile

if __name__ == "__main__":
    cProfile.run("rendermain()", "mcedit.profile")
