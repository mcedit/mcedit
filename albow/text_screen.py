#
#   Albow - Text Screen
#

from pygame import Rect
from pygame.locals import *
from screen import Screen
from theme import FontProperty
from resource import get_image, get_font, get_text
from vectors import add, maximum
from controls import Button

#------------------------------------------------------------------------------


class Page(object):

    def __init__(self, text_screen, heading, lines):
        self.text_screen = text_screen
        self.heading = heading
        self.lines = lines
        width, height = text_screen.heading_font.size(heading)
        for line in lines:
            w, h = text_screen.font.size(line)
            width = max(width, w)
            height += h
        self.size = (width, height)

    def draw(self, surface, color, pos):
        heading_font = self.text_screen.heading_font
        text_font = self.text_screen.font
        x, y = pos
        buf = heading_font.render(self.heading, True, color)
        surface.blit(buf, (x, y))
        y += buf.get_rect().height
        for line in self.lines:
            buf = text_font.render(line, True, color)
            surface.blit(buf, (x, y))
            y += buf.get_rect().height

#------------------------------------------------------------------------------


class TextScreen(Screen):

#    bg_color = (0, 0, 0)
#    fg_color = (255, 255, 255)
#    border = 20

    heading_font = FontProperty('heading_font')
    button_font = FontProperty('button_font')

    def __init__(self, shell, filename, **kwds):
        text = get_text(filename)
        text_pages = text.split("\nPAGE\n")
        pages = []
        page_size = (0, 0)
        for text_page in text_pages:
            lines = text_page.strip().split("\n")
            page = Page(self, lines[0], lines[1:])
            pages.append(page)
            page_size = maximum(page_size, page.size)
        self.pages = pages
        bf = self.button_font
        b1 = Button("Prev Page", font=bf, action=self.prev_page)
        b2 = Button("Menu", font=bf, action=self.go_back)
        b3 = Button("Next Page", font=bf, action=self.next_page)
        b = self.margin
        page_rect = Rect((b, b), page_size)
        gap = (0, 18)
        b1.topleft = add(page_rect.bottomleft, gap)
        b2.midtop = add(page_rect.midbottom, gap)
        b3.topright = add(page_rect.bottomright, gap)
        Screen.__init__(self, shell, **kwds)
        self.size = add(b3.bottomright, (b, b))
        self.add(b1)
        self.add(b2)
        self.add(b3)
        self.prev_button = b1
        self.next_button = b3
        self.set_current_page(0)

    def draw(self, surface):
        b = self.margin
        self.pages[self.current_page].draw(surface, self.fg_color, (b, b))

    def at_first_page(self):
        return self.current_page == 0

    def at_last_page(self):
        return self.current_page == len(self.pages) - 1

    def set_current_page(self, n):
        self.current_page = n
        self.prev_button.enabled = not self.at_first_page()
        self.next_button.enabled = not self.at_last_page()

    def prev_page(self):
        if not self.at_first_page():
            self.set_current_page(self.current_page - 1)

    def next_page(self):
        if not self.at_last_page():
            self.set_current_page(self.current_page + 1)

    def go_back(self):
        self.parent.show_menu()
