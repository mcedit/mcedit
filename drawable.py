"""
    ${NAME}
"""
from __future__ import absolute_import, division, print_function, unicode_literals
import logging
log = logging.getLogger(__name__)

from OpenGL import GL

class Drawable(object):

    def __init__(self):
        super(Drawable, self).__init__()
        self._displayList = None
        self.invalidList = True
        self.children = []

    def setUp(self):
        """
        Set up rendering settings and view matrices
        :return:
        :rtype:
        """

    def tearDown(self):
        """
        Return any settings changed in setUp to their previous states
        :return:
        :rtype:
        """

    def drawSelf(self):
        """
        Draw this drawable, if it has its own graphics.
        :return:
        :rtype:
        """

    def _draw(self):
        self.setUp()
        self.drawSelf()
        for child in self.children:
            child.draw()
        self.tearDown()

    def draw(self):
        if self._displayList is None:
           self._displayList = GL.glGenLists(1)

        if self.invalidList:
            self.compileList()

        GL.glCallList(self._displayList)

    def compileList(self):
        GL.glNewList(self._displayList, GL.GL_COMPILE)
        self._draw()
        GL.glEndList()
        self.invalidList = False

    def invalidate(self):
        self.invalidList = True
