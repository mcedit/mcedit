"""
    compass
"""
from __future__ import absolute_import, division, print_function, unicode_literals
import logging
from OpenGL import GL
from drawable import Drawable
from glutils import gl
from mceutils import loadPNGTexture

log = logging.getLogger(__name__)


def makeQuad(minx, miny, width, height):
    return [minx, miny, minx+width, miny, minx+width, miny+height, minx, miny + height]

class CompassOverlay(Drawable):
    _tex = None
    _yawPitch = (0., 0.)

    def __init__(self, small=False):
        super(CompassOverlay, self).__init__()
        self.small = small

    @property
    def yawPitch(self):
        return self._yawPitch

    @yawPitch.setter
    def yawPitch(self, value):
        self._yawPitch = value
        self.invalidate()

    def drawSelf(self):
        if self._tex is None:
            if self.small:
                filename = "compass_small.png"
            else:
                filename = "compass.png"

            self._tex = loadPNGTexture("toolicons/" + filename)#, minFilter=GL.GL_LINEAR, magFilter=GL.GL_LINEAR)

        self._tex.bind()
        size = 0.075

        with gl.glPushMatrix(GL.GL_MODELVIEW):
            GL.glLoadIdentity()

            yaw, pitch = self.yawPitch
            GL.glTranslatef(1.-size, size, 0.0)  # position on upper right corner
            GL.glRotatef(180-yaw, 0., 0., 1.)  # adjust to north
            GL.glColor3f(1., 1., 1.)

            with gl.glEnableClientState(GL.GL_TEXTURE_COORD_ARRAY):
                GL.glVertexPointer(2, GL.GL_FLOAT, 0, makeQuad(-size, -size, 2*size, 2*size))
                GL.glTexCoordPointer(2, GL.GL_FLOAT, 0, makeQuad(0, 0, 256, 256))

                with gl.glEnable(GL.GL_BLEND, GL.GL_TEXTURE_2D):
                    GL.glDrawArrays(GL.GL_QUADS, 0, 4)


