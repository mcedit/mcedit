################################################################
#
#   Albow - Tab Panel
#
################################################################

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
from albow import *
from pygame import Rect, Surface, draw, image
from pygame.locals import SRCALPHA
from widget import Widget
from theme import ThemeProperty, FontProperty
from utils import brighten
from numpy import fromstring


class TabPanel(Widget):
    #  pages         [Widget]
    #  current_page  Widget

    tab_font = FontProperty('tab_font')
    tab_height = ThemeProperty('tab_height')
    tab_border_width = ThemeProperty('tab_border_width')
    tab_spacing = ThemeProperty('tab_spacing')
    tab_margin = ThemeProperty('tab_margin')
    tab_fg_color = ThemeProperty('tab_fg_color')
    default_tab_bg_color = ThemeProperty('default_tab_bg_color')
    tab_area_bg_color = ThemeProperty('tab_area_bg_color')
    tab_dimming = ThemeProperty('tab_dimming')
    tab_titles = None
    #use_page_bg_color_for_tabs = ThemeProperty('use_page_bg_color_for_tabs')

    def __init__(self, pages=None, **kwds):
        Widget.__init__(self, **kwds)
        self.pages = []
        self.current_page = None
        if pages:
            w = h = 0
            for title, page in pages:
                w = max(w, page.width)
                h = max(h, page.height)
                self._add_page(title, page)
            self.size = (w, h)
            self.show_page(pages[0][1])

    def content_size(self):
        return self.width, self.height - self.tab_height

    def content_rect(self):
        return Rect((0, self.tab_height), self.content_size())

    def page_height(self):
        return self.height - self.tab_height

    def add_page(self, title, page):
        self._add_page(title, page)
        if not self.current_page:
            self.show_page(page)

    def _add_page(self, title, page):
        page.tab_title = title
        page.anchor = 'ltrb'
        self.pages.append(page)

    def remove_page(self, page):
        try:
            i = self.pages.index(page)
            del self.pages[i]
        except IndexError:
            pass
        if page is self.current_page:
            self.show_page(None)

    def show_page(self, page):
        if self.current_page:
            self.remove(self.current_page)
        self.current_page = page
        if page:
            th = self.tab_height
            page.rect = Rect(0, th, self.width, self.height - th)
            self.add(page)
            page.focus()

    def draw(self, surf):
        self.draw_tab_area_bg(surf)
        self.draw_tabs(surf)

    def draw_tab_area_bg(self, surf):
        bg = self.tab_area_bg_color
        if bg:
            surf.fill(bg, (0, 0, self.width, self.tab_height))

    def draw_tabs(self, surf):
        font = self.tab_font
        fg = self.tab_fg_color
        b = self.tab_border_width
        if b:
            surf.fill(fg, (0, self.tab_height - b, self.width, b))
        for i, title, page, selected, rect in self.iter_tabs():
            x0 = rect.left
            w = rect.width
            h = rect.height
            r = rect
            if not selected:
                r = Rect(r)
                r.bottom -= b
            self.draw_tab_bg(surf, page, selected, r)
            if b:
                surf.fill(fg, (x0, 0, b, h))
                surf.fill(fg, (x0 + b, 0, w - 2 * b, b))
                surf.fill(fg, (x0 + w - b, 0, b, h))
            buf = font.render(title, True, page.fg_color or fg)
            r = buf.get_rect()
            r.center = (x0 + w // 2, h // 2)
            surf.blit(buf, r)

    def iter_tabs(self):
        pages = self.pages
        current_page = self.current_page
        n = len(pages)
        b = self.tab_border_width
        s = self.tab_spacing
        h = self.tab_height
        m = self.tab_margin
        width = self.width - 2 * m + s - b
        x0 = m
        for i, page in enumerate(pages):
            x1 = m + (i + 1) * width // n  # self.tab_boundary(i + 1)
            selected = page is current_page
            yield i, page.tab_title, page, selected, Rect(x0, 0, x1 - x0 - s + b, h)
            x0 = x1

    def draw_tab_bg(self, surf, page, selected, rect):
        bg = self.tab_bg_color_for_page(page)
        if not selected:
            bg = brighten(bg, self.tab_dimming)
        surf.fill(bg, rect)

    def tab_bg_color_for_page(self, page):
        return getattr(page, 'tab_bg_color', None) \
            or page.bg_color \
            or self.default_tab_bg_color

    def mouse_down(self, e):
        x, y = e.local
        if y < self.tab_height:
            i = self.tab_number_containing_x(x)
            if i is not None:
                self.show_page(self.pages[i])

    def tab_number_containing_x(self, x):
        n = len(self.pages)
        m = self.tab_margin
        width = self.width - 2 * m + self.tab_spacing - self.tab_border_width
        i = (x - m) * n // width
        if 0 <= i < n:
            return i
        
    def gl_draw_self(self, root, offset):
        self.gl_draw(root, offset)

    def gl_draw(self, root, offset):
        pages = self.pages

        if len(pages) > 1:
            tlcorner = (offset[0] + self.bottomleft[0], offset[1] + self.bottomleft[1])
            pageTabContents = []        
            current_page = self.current_page
            n = len(pages)
            b = self.tab_border_width
            s = self.tab_spacing
            h = self.tab_height
            m = self.tab_margin
            tabWidth = (self.size[0]-(s*n)-(2*m))/n
            width = self.width - 2 * m + s - b
            x0 = m + tlcorner[0]

            font = self.tab_font
            fg = self.tab_fg_color
            surface = Surface(self.size, SRCALPHA)

            glEnable(GL_BLEND)
            
            for i, page in enumerate(pages):
                x1 = x0+tabWidth
                selected = page is current_page
                if selected:
                    glColor(1.0, 1.0, 1.0, 0.5)
                else:
                    glColor(0.5, 0.5, 0.5, 0.5)
                glRectf(x0, tlcorner[1]-(m+b), x1, tlcorner[1]-(h))
                buf = font.render(self.pages[i].tab_title, True, self.fg_color or fg)
                r = buf.get_rect()

                offs = ((tabWidth - r.size[0])/2) + m +((s+tabWidth)*i)

                surface.blit(buf, (offs, m))
                x0 = x1 + s    
            
            data = image.tostring(surface, 'RGBA', 1)
            rect = self.rect.move(offset)
            w, h = root.size
            glViewport(0, 0, w, h)
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            gluOrtho2D(0, w, 0, h)
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()
            glRasterPos2i(rect.left, h - rect.bottom)
            glPushAttrib(GL_COLOR_BUFFER_BIT)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glDrawPixels(self.width, self.height,
                GL_RGBA, GL_UNSIGNED_BYTE, fromstring(data, dtype='uint8'))
            glPopAttrib()
            glFlush()

            glDisable(GL_BLEND)
