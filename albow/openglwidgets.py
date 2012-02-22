#-------------------------------------------------------------------------
#
#   Albow - OpenGL widgets
#
#-------------------------------------------------------------------------

from __future__ import division
from OpenGL import GL, GLU
from widget import Widget


class GLViewport(Widget):

    is_gl_container = True

    def gl_draw_self(self, root, offset):
        rect = self.rect.move(offset)
        # GL_CLIENT_ALL_ATTRIB_BITS is borked: defined as -1 but
        # glPushClientAttrib insists on an unsigned long.
        #GL.glPushClientAttrib(0xffffffff)
        #GL.glPushAttrib(GL.GL_ALL_ATTRIB_BITS)
        GL.glViewport(rect.left, root.height - rect.bottom, rect.width, rect.height)
        self.gl_draw_viewport()
        #GL.glPopAttrib()
        #GL.glPopClientAttrib()

    def gl_draw_viewport(self):
        self.setup_matrices()
        self.gl_draw()

    def setup_matrices(self):
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        self.setup_projection()
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        self.setup_modelview()

    def setup_projection(self):
        pass

    def setup_modelview(self):
        pass

    def gl_draw(self):
        pass

    def augment_mouse_event(self, event):
        Widget.augment_mouse_event(self, event)
        w, h = self.size
        viewport = numpy.array((0, 0, w, h), dtype='int32')
        self.setup_matrices()
        gf = GL.glGetDoublev
        pr_mat = gf(GL.GL_PROJECTION_MATRIX)
        mv_mat = gf(GL.GL_MODELVIEW_MATRIX)
        x, y = event.local
        y = h - y
        up = GLU.gluUnProject
        try:
            p0 = up(x, y, 0.0, mv_mat, pr_mat, viewport)
            p1 = up(x, y, 1.0, mv_mat, pr_mat, viewport)
            event.dict['ray'] = (p0, p1)
        except ValueError:  # projection failed!
            pass

import numpy

#-------------------------------------------------------------------------


class GLOrtho(GLViewport):

    def __init__(self, rect=None,
            xmin=-1, xmax=1, ymin=-1, ymax=1,
            near=-1, far=1, **kwds):
        GLViewport.__init__(self, rect, **kwds)
        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax
        self.near = near
        self.far = far

    def setup_projection(self):
        GL.glOrtho(self.xmin, self.xmax, self.ymin, self.ymax,
            self.near, self.far)


class GLPixelOrtho(GLOrtho):
    def __init__(self, rect=None, near=-1, far=1, **kwds):
        GLOrtho.__init__(self, rect, near, far, **kwds)
        self.xmin = 0
        self.ymin = 0
        self.xmax = self.width
        self.ymax = self.height


#-------------------------------------------------------------------------


class GLPerspective(GLViewport):

    def __init__(self, rect=None, fovy=20,
            near=0.1, far=1000, **kwds):
        GLViewport.__init__(self, rect, **kwds)
        self.fovy = fovy
        self.near = near
        self.far = far

    def setup_projection(self):
        aspect = self.width / self.height
        GLU.gluPerspective(self.fovy, aspect, self.near, self.far)
