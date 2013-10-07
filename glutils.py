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
glutils.py

Pythonesque wrappers around certain OpenGL functions.
"""

from OpenGL import GL
from OpenGL.GL.ARB import window_pos
import numpy
import functools
from contextlib import contextmanager

from albow import Label
from albow.openglwidgets import GLOrtho
import config

import weakref
from OpenGL.GL import framebufferobjects as FBO
import sys


class gl(object):
    @classmethod
    def ResetGL(cls):
        DisplayList.invalidateAllLists()

    @classmethod
    @contextmanager
    def glPushMatrix(cls, matrixmode):
        try:
            GL.glMatrixMode(matrixmode)
            GL.glPushMatrix()
            yield
        finally:
            GL.glMatrixMode(matrixmode)
            GL.glPopMatrix()

    @classmethod
    @contextmanager
    def glPushAttrib(cls, attribs):
        try:
            GL.glPushAttrib(attribs)
            yield
        finally:
            GL.glPopAttrib()

    @classmethod
    @contextmanager
    def glBegin(cls, type):
        try:
            GL.glBegin(type)
            yield
        finally:
            GL.glEnd()

    @classmethod
    @contextmanager
    def glEnable(cls, *enables):
        try:
            GL.glPushAttrib(GL.GL_ENABLE_BIT)
            for e in enables:
                GL.glEnable(e)

            yield
        finally:
            GL.glPopAttrib()

    @classmethod
    @contextmanager
    def glEnableClientState(cls, *enables):
        try:
            GL.glPushClientAttrib(GL.GL_CLIENT_ALL_ATTRIB_BITS)
            for e in enables:
                GL.glEnableClientState(e)

            yield
        finally:
            GL.glPopClientAttrib()

    listCount = 0

    @classmethod
    def glGenLists(cls, n):
        cls.listCount += n
        return GL.glGenLists(n)

    @classmethod
    def glDeleteLists(cls, base, n):
        cls.listCount -= n
        return GL.glDeleteLists(base, n)


class DisplayList(object):
    allLists = []

    def __init__(self, drawFunc=None):
        self.drawFunc = drawFunc
        self._list = None

        def _delete(r):
            DisplayList.allLists.remove(r)
        self.allLists.append(weakref.ref(self, _delete))

    def __del__(self):
        self.invalidate()

    @classmethod
    def invalidateAllLists(self):
        allLists = []
        for listref in self.allLists:
            list = listref()
            if list:
                list.invalidate()
                allLists.append(listref)

        self.allLists = allLists

    def invalidate(self):
        if self._list:
            gl.glDeleteLists(self._list[0], 1)
            self._list = None

    def makeList(self, drawFunc):
        if self._list:
            return

        drawFunc = (drawFunc or self.drawFunc)
        if drawFunc is None:
            return

        l = gl.glGenLists(1)
        GL.glNewList(l, GL.GL_COMPILE)
        drawFunc()
        #try:
        GL.glEndList()
        #except GL.GLError:
        #    print "Error while compiling display list. Retrying display list code to pinpoint error"
        #    self.drawFunc()

        self._list = numpy.array([l], 'uintc')

    def getList(self, drawFunc=None):
        self.makeList(drawFunc)
        return self._list

    if "-debuglists" in sys.argv:
        def call(self, drawFunc=None):
            drawFunc = (drawFunc or self.drawFunc)
            if drawFunc is None:
                return
            drawFunc()
    else:
        def call(self, drawFunc=None):
            self.makeList(drawFunc)
            GL.glCallLists(self._list)


class Texture(object):
    allTextures = []
    defaultFilter = GL.GL_NEAREST

    def __init__(self, textureFunc=None, minFilter=None, magFilter=None):
        minFilter = minFilter or self.defaultFilter
        magFilter = magFilter or self.defaultFilter
        if textureFunc is None:
            textureFunc = lambda: None

        self.textureFunc = textureFunc
        self._texID = GL.glGenTextures(1)

        def _delete(r):
            Texture.allTextures.remove(r)
        self.allTextures.append(weakref.ref(self, _delete))
        self.bind()
        GL.glTexParameter(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, minFilter)
        GL.glTexParameter(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, magFilter)

        self.textureFunc()

    def __del__(self):
        self.delete()

    def delete(self):
        if self._texID is not None:
            GL.glDeleteTextures(self._texID)

    def bind(self):
        GL.glBindTexture(GL.GL_TEXTURE_2D, self._texID)

    def invalidate(self):
        self.dirty = True


class FramebufferTexture(Texture):
    def __init__(self, width, height, drawFunc):
        tex = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, tex)
        GL.glTexParameter(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)
        GL.glTexParameter(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA8, width, height, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, None)
        self.enabled = False
        self._texID = tex
        if bool(FBO.glGenFramebuffers) and "Intel" not in GL.glGetString(GL.GL_VENDOR):
            buf = FBO.glGenFramebuffers(1)
            depthbuffer = FBO.glGenRenderbuffers(1)

            FBO.glBindFramebuffer(FBO.GL_FRAMEBUFFER, buf)

            FBO.glBindRenderbuffer(FBO.GL_RENDERBUFFER, depthbuffer)
            FBO.glRenderbufferStorage(FBO.GL_RENDERBUFFER, GL.GL_DEPTH_COMPONENT, width, height)

            FBO.glFramebufferRenderbuffer(FBO.GL_FRAMEBUFFER, FBO.GL_DEPTH_ATTACHMENT, FBO.GL_RENDERBUFFER, depthbuffer)
            FBO.glFramebufferTexture2D(FBO.GL_FRAMEBUFFER, FBO.GL_COLOR_ATTACHMENT0, GL.GL_TEXTURE_2D, tex, 0)

            status = FBO.glCheckFramebufferStatus(FBO.GL_FRAMEBUFFER)
            if status != FBO.GL_FRAMEBUFFER_COMPLETE:
                print "glCheckFramebufferStatus", status
                self.enabled = False
                return

            FBO.glBindFramebuffer(FBO.GL_FRAMEBUFFER, buf)

            with gl.glPushAttrib(GL.GL_VIEWPORT_BIT):
                GL.glViewport(0, 0, width, height)
                drawFunc()

            FBO.glBindFramebuffer(FBO.GL_FRAMEBUFFER, 0)
            FBO.glDeleteFramebuffers(1, [buf])
            FBO.glDeleteRenderbuffers(1, [depthbuffer])
            self.enabled = True
        else:
            GL.glReadBuffer(GL.GL_BACK)

            GL.glPushAttrib(GL.GL_VIEWPORT_BIT | GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT | GL.GL_STENCIL_TEST | GL.GL_STENCIL_BUFFER_BIT)
            GL.glDisable(GL.GL_STENCIL_TEST)

            GL.glViewport(0, 0, width, height)
            GL.glScissor(0, 0, width, height)
            with gl.glEnable(GL.GL_SCISSOR_TEST):
                drawFunc()

            GL.glBindTexture(GL.GL_TEXTURE_2D, tex)
            GL.glReadBuffer(GL.GL_BACK)
            GL.glCopyTexSubImage2D(GL.GL_TEXTURE_2D, 0, 0, 0, 0, 0, width, height)

            GL.glPopAttrib()



def debugDrawPoint(point):
    GL.glColor(1.0, 1.0, 0.0, 1.0)
    GL.glPointSize(9.0)
    with gl.glBegin(GL.GL_POINTS):
        GL.glVertex3f(*point)
