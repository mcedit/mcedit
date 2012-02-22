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
glbackground.py

A UI element that only draws a single OpenGL quad.
"""

from albow.openglwidgets import GLOrtho
from OpenGL.GL import glEnable, glColor, glVertexPointer, glDrawArrays, glDisable, GL_BLEND, GL_FLOAT, GL_QUADS
from numpy import array
from pygame import mouse


class GLBackground(GLOrtho):
    margin = 8
    bg_color = (0.0, 0.0, 0.0, 0.6)

    #bg_color = (30/255.0,0,255/255.0, 100/255.0)
    def gl_draw(self):
        #if hasattr(self, 'highlight_bg_color') and self in self.get_root().find_widget(mouse.get_pos()).all_parents():
        #    color = self.highlight_bg_color
        #else:
        color = tuple(self.bg_color) + (1.0,)

        glEnable(GL_BLEND)
        glColor(color[0], color[1], color[2], color[3])
        glVertexPointer(2, GL_FLOAT, 0, array([-1, -1, -1, 1, 1, 1, 1, -1], dtype='float32'))
        glDrawArrays(GL_QUADS, 0, 4)
        glDisable(GL_BLEND)


class Panel(GLBackground):
    pass
