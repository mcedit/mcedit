#
#    Albow - Menu bar
#

from pygame import Rect
from widget import Widget, overridable_property


class MenuBar(Widget):

    menus = overridable_property('menus', "List of Menu instances")

    def __init__(self, menus=None, width=0, **kwds):
        font = self.predict_font(kwds)
        height = font.get_linesize()
        Widget.__init__(self, Rect(0, 0, width, height), **kwds)
        self.menus = menus or []
        self._hilited_menu = None

    def get_menus(self):
        return self._menus

    def set_menus(self, x):
        self._menus = x

    def draw(self, surf):
        fg = self.fg_color
        bg = self.bg_color
        font = self.font
        hilited = self._hilited_menu
        x = 0
        for menu in self._menus:
            text = " %s " % menu.title
            if menu is hilited:
                buf = font.render(text, True, bg, fg)
            else:
                buf = font.render(text, True, fg, bg)
            surf.blit(buf, (x, 0))
            x += surf.get_width()

    def mouse_down(self, e):
        mx = e.local[0]
        font = self.font
        x = 0
        for menu in self._menus:
            text = " %s " % menu.title
            w = font.size(text)[0]
            if x <= mx < x + w:
                self.show_menu(menu, x)

    def show_menu(self, menu, x):
        self._hilited_menu = menu
        try:
            i = menu.present(self, (x, self.height))
        finally:
            self._hilited_menu = None
        menu.invoke_item(i)

    def handle_command_key(self, e):
        menus = self.menus
        for m in xrange(len(menus) - 1, -1, -1):
            menu = menus[m]
            i = menu.find_item_for_key(e)
            if i >= 0:
                menu.invoke_item(i)
                return True
        return False
