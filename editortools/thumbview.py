from OpenGL import GLU, GL
from numpy import array
from albow import Widget
from albow.openglwidgets import GLPerspective
from glutils import FramebufferTexture, gl
import pymclevel
from renderer import PreviewRenderer

class ThumbView(GLPerspective):

    def __init__(self, sch, **kw):
        GLPerspective.__init__(self, **kw)  # self, xmin= -32, xmax=32, ymin= -32, ymax=32, near= -1000, far=1000)
        self.far = 16000
        self.schematic = sch
        self.renderer = PreviewRenderer(sch)
        self.fboSize = (128, 128)
        # self.renderer.position = (sch.Length / 2, 0, sch.Height / 2)

    def setup_modelview(self):
        GLU.gluLookAt(-self.schematic.Width * 2.8, self.schematic.Height * 2.5 + 1, -self.schematic.Length * 1.5,
                      self.schematic.Width, 0, self.schematic.Length,
                      0, 1, 0)
    fbo = None

    def gl_draw_tex(self):
        self.clear()
        self.renderer.draw()

    def clear(self):
        if self.drawBackground:
            GL.glClearColor(0.25, 0.27, 0.77, 1.0)
        else:
            GL.glClearColor(0.0, 0.0, 0.0, 0.0)
        GL.glClear(GL.GL_DEPTH_BUFFER_BIT | GL.GL_COLOR_BUFFER_BIT)

    def gl_draw(self):
        if self.schematic.chunkCount > len(self.renderer.chunkRenderers):
            self.gl_draw_thumb()
        else:
            if self.fbo is None:
                w, h = self.fboSize
                self.fbo = FramebufferTexture(w, h, self.gl_draw_tex)
            GL.glMatrixMode(GL.GL_PROJECTION)
            GL.glLoadIdentity()
            GL.glMatrixMode(GL.GL_MODELVIEW)
            GL.glLoadIdentity()
            GL.glEnableClientState(GL.GL_TEXTURE_COORD_ARRAY)
            GL.glColor(1.0, 1.0, 1.0, 1.0)
            GL.glVertexPointer(2, GL.GL_FLOAT, 0, array([-1, -1,
                         - 1, 1,
                         1, 1,
                         1, -1, ], dtype='float32'))
            GL.glTexCoordPointer(2, GL.GL_FLOAT, 0, array([0, 0, 0, 256, 256, 256, 256, 0], dtype='float32'))
            e = (GL.GL_TEXTURE_2D,)
            if not self.drawBackground:
                e += (GL.GL_ALPHA_TEST,)
            with gl.glEnable(*e):
                self.fbo.bind()
                GL.glDrawArrays(GL.GL_QUADS, 0, 4)
            GL.glDisableClientState(GL.GL_TEXTURE_COORD_ARRAY)

    drawBackground = True

    def gl_draw_thumb(self):
        GL.glPushAttrib(GL.GL_SCISSOR_BIT)
        r = self.rect
        r = r.move(*self.local_to_global_offset())
        GL.glScissor(r.x, self.get_root().height - r.y - r.height, r.width, r.height)
        with gl.glEnable(GL.GL_SCISSOR_TEST):
            self.clear()
            self.renderer.draw()
        GL.glPopAttrib()


class BlockThumbView(Widget):
    is_gl_container = True

    def __init__(self, materials, blockInfo=None, **kw):
        Widget.__init__(self, **kw)
        self.materials = materials
        self.blockInfo = blockInfo

    thumb = None
    _blockInfo = None

    @property
    def blockInfo(self):
        return self._blockInfo

    @blockInfo.setter
    def blockInfo(self, b):
        if self._blockInfo != b:
            if self.thumb:
                self.thumb.set_parent(None)
            self._blockInfo = b
            if b is None:
                return

            sch = pymclevel.MCSchematic(shape=(1, 1, 1), mats=self.materials)
            if b:
                sch.Blocks[:] = b.ID
                sch.Data[:] = b.blockData

            self.thumb = ThumbView(sch)
            self.add(self.thumb)
            self.thumb.size = self.size
            self.thumb.drawBackground = False
            for i in self.thumb.renderer.chunkWorker:
                pass
