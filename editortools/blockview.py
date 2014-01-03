from OpenGL import GL

from numpy import array
from albow import ButtonBase, ValueDisplay, AttrRef, Row
from albow.openglwidgets import GLOrtho
import thumbview
import blockpicker
from glbackground import Panel, GLBackground
from glutils import DisplayList

class BlockView(GLOrtho):
    def __init__(self, materials, blockInfo=None):
        GLOrtho.__init__(self)
        self.list = DisplayList(self._gl_draw)
        self.blockInfo = blockInfo or materials.Air
        self.materials = materials

    listBlockInfo = None

    def gl_draw(self):
        if self.listBlockInfo != self.blockInfo:
            self.list.invalidate()
            self.listBlockInfo = self.blockInfo

        self.list.call()

    def _gl_draw(self):
        blockInfo = self.blockInfo
        if blockInfo.ID is 0:
            return

        GL.glColor(1.0, 1.0, 1.0, 1.0)
        GL.glEnable(GL.GL_TEXTURE_2D)
        GL.glEnable(GL.GL_ALPHA_TEST)
        self.materials.terrainTexture.bind()
        pixelScale = 0.5 if self.materials.name in ("Pocket", "Alpha") else 1.0
        texSize = 16 * pixelScale

        GL.glEnableClientState(GL.GL_TEXTURE_COORD_ARRAY)
        GL.glVertexPointer(2, GL.GL_FLOAT, 0, array([-1, -1,
                                 - 1, 1,
                                 1, 1,
                                 1, -1, ], dtype='float32'))
        texOrigin = array(self.materials.blockTextures[blockInfo.ID, blockInfo.blockData, 0])
        texOrigin *= pixelScale

        GL.glTexCoordPointer(2, GL.GL_FLOAT, 0, array([texOrigin[0], texOrigin[1] + texSize,
                                  texOrigin[0], texOrigin[1],
                                  texOrigin[0] + texSize, texOrigin[1],
                                  texOrigin[0] + texSize, texOrigin[1] + texSize], dtype='float32'))

        GL.glDrawArrays(GL.GL_QUADS, 0, 4)

        GL.glDisableClientState(GL.GL_TEXTURE_COORD_ARRAY)
        GL.glDisable(GL.GL_ALPHA_TEST)
        GL.glDisable(GL.GL_TEXTURE_2D)

    @property
    def tooltipText(self):
        return "{0}".format(self.blockInfo.name)


class BlockButton(ButtonBase, Panel):
    _ref = None

    def __init__(self, materials, blockInfo=None, ref=None, recentBlocks=None, *a, **kw):
        self.allowWildcards = False
        Panel.__init__(self, *a, **kw)

        self.bg_color = (1, 1, 1, 0.25)
        self._ref = ref
        if blockInfo is None and ref is not None:
            blockInfo = ref.get()
        blockInfo = blockInfo or materials.Air

        if recentBlocks is not None:
            self.recentBlocks = recentBlocks
        else:
            self.recentBlocks = []

        self.blockView = thumbview.BlockThumbView(materials, blockInfo, size=(48, 48))
        self.blockLabel = ValueDisplay(ref=AttrRef(self, 'labelText'), width=180, align="l")
        row = Row((self.blockView, self.blockLabel), align="b")

        # col = Column( (self.blockButton, self.blockNameLabel) )
        self.add(row)
        self.shrink_wrap()

        # self.blockLabel.bottom = self.blockButton.bottom
        # self.blockLabel.centerx = self.blockButton.centerx

        # self.add(self.blockLabel)

        self.materials = materials
        self.blockInfo = blockInfo
        # self._ref = ref
        self.updateRecentBlockView()

    recentBlockLimit = 7

    @property
    def blockInfo(self):
        if self._ref:
            return self._ref.get()
        else:
            return self._blockInfo

    @blockInfo.setter
    def blockInfo(self, bi):
        if self._ref:
            self._ref.set(bi)
        else:
            self._blockInfo = bi
        self.blockView.blockInfo = bi
        if bi not in self.recentBlocks:
            self.recentBlocks.append(bi)
            if len(self.recentBlocks) > self.recentBlockLimit:
                self.recentBlocks.pop(0)
            self.updateRecentBlockView()

    @property
    def labelText(self):
        labelText = self.blockInfo.name
        if len(labelText) > 24:
            labelText = labelText[:23] + "..."
        return labelText

        # self.blockNameLabel.text =

    def createRecentBlockView(self):
        def makeBlockView(bi):
            bv = BlockView(self.materials, bi)
            bv.size = (16, 16)

            def action(evt):
                self.blockInfo = bi
            bv.mouse_up = action
            return bv

        row = [makeBlockView(bi) for bi in self.recentBlocks]
        row = Row(row)

        widget = GLBackground()
        widget.bg_color = (0.8, 0.8, 0.8, 0.8)
        widget.add(row)
        widget.shrink_wrap()
        widget.anchor = "whtr"
        return widget

    def updateRecentBlockView(self):
        if self.recentBlockView:
            self.recentBlockView.set_parent(None)
        self.recentBlockView = self.createRecentBlockView()

        self.recentBlockView.right = self.width
        self.add(self.recentBlockView)
        #print self.rect, self.recentBlockView.rect

    recentBlockView = None

    @property
    def tooltipText(self):
        return "{0}".format(self.blockInfo.name)

    def action(self):
        blockPicker = blockpicker.BlockPicker(self.blockInfo, self.materials, allowWildcards=self.allowWildcards)
        if blockPicker.present():
            self.blockInfo = blockPicker.blockInfo
