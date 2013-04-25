#---------------------------------------------------------------------------
#
#    Albow - Pull-down or pop-up menu
#
#---------------------------------------------------------------------------

import sys
from root import get_root, get_focus
from dialogs import Dialog
from theme import ThemeProperty
from pygame import Rect, draw

#---------------------------------------------------------------------------


class MenuItem(object):

    keyname = ""
    keycode = None
    shift = False
    alt = False
    enabled = False

    if sys.platform.startswith('darwin') or sys.platform.startswith('mac'):
        cmd_name = "Cmd "
        option_name = "Opt "
    else:
        cmd_name = "Ctrl "
        option_name = "Alt "

    def __init__(self, text="", command=None):
        self.command = command
        if "/" in text:
            text, key = text.split("/", 1)
        else:
            key = ""
        self.text = text
        if key:
            keyname = key[-1]
            mods = key[:-1]
            self.keycode = ord(keyname.lower())
            if "^" in mods:
                self.shift = True
                keyname = "Shift " + keyname
            if "@" in mods:
                self.alt = True
                keyname = self.option_name + keyname
            self.keyname = self.cmd_name + keyname

#---------------------------------------------------------------------------


class Menu(Dialog):

    disabled_color = ThemeProperty('disabled_color')
    click_outside_response = -1
    scroll_button_size = ThemeProperty('scroll_button_size')
    scroll_button_color = ThemeProperty('scroll_button_color')
    scroll = 0

    def __init__(self, title, items, scrolling=False, scroll_items=30,
                 scroll_page=5, **kwds):
        self.title = title
        self.items = items
        self._items = [MenuItem(*item) for item in items]
        self.scrolling = scrolling and len(self._items) > scroll_items
        self.scroll_items = scroll_items
        self.scroll_page = scroll_page
        Dialog.__init__(self, **kwds)

        h = self.font.get_linesize()
        if self.scrolling:
            self.height = h * self.scroll_items + h
        else:
            self.height = h * len(self._items) + h

    def present(self, client, pos):
        client = client or get_root()
        self.topleft = client.local_to_global(pos)
        focus = get_focus()
        font = self.font
        h = font.get_linesize()
        items = self._items
        margin = self.margin
        if self.scrolling:
            height = h * self.scroll_items + h
        else:
            height = h * len(items) + h
        w1 = w2 = 0
        for item in items:
            item.enabled = self.command_is_enabled(item, focus)
            w1 = max(w1, font.size(item.text)[0])
            w2 = max(w2, font.size(item.keyname)[0])
        width = w1 + 2 * margin
        self._key_margin = width
        if w2 > 0:
            width += w2 + margin
        if self.scrolling:
            width += self.scroll_button_size            
        self.size = (width, height)
        self._hilited = None

        root = get_root()
        self.rect.clamp_ip(root.rect)

        return Dialog.present(self, centered=False)

    def command_is_enabled(self, item, focus):
        cmd = item.command
        if cmd:
            enabler_name = cmd + '_enabled'
            handler = focus
            while handler:
                enabler = getattr(handler, enabler_name, None)
                if enabler:
                    return enabler()
                handler = handler.next_handler()
        return True

    def scroll_up_rect(self):
        d = self.scroll_button_size
        r = Rect(0, 0, d, d)
        m = self.margin
        r.top = m
        r.right = self.width - m
        r.inflate_ip(-4, -4)
        return r

    def scroll_down_rect(self):
        d = self.scroll_button_size
        r = Rect(0, 0, d, d)
        m = self.margin
        r.bottom = self.height - m
        r.right = self.width - m
        r.inflate_ip(-4, -4)
        return r

    def draw(self, surf):
        font = self.font
        h = font.get_linesize()
        sep = surf.get_rect()
        sep.height = 1
        if self.scrolling:
            sep.width -= self.margin + self.scroll_button_size
        colors = [self.disabled_color, self.fg_color]
        bg = self.bg_color
        xt = self.margin
        xk = self._key_margin
        y = h // 2
        hilited = self._hilited
        if self.scrolling:
            items = self._items[self.scroll:self.scroll + self.scroll_items]
        else:
            items = self._items
        for item in items:
            text = item.text
            if not text:
                sep.top = y + h // 2
                surf.fill(colors[0], sep)
            else:
                if item is hilited:
                    rect = surf.get_rect()
                    rect.top = y
                    rect.height = h
                    if self.scrolling:
                        rect.width -= xt + self.scroll_button_size
                    surf.fill(colors[1], rect)
                    color = bg
                else:
                    color = colors[item.enabled]
                buf = font.render(item.text, True, color)
                surf.blit(buf, (xt, y))
                keyname = item.keyname
                if keyname:
                    buf = font.render(keyname, True, color)
                    surf.blit(buf, (xk, y))
            y += h
        if self.scrolling:
            if self.can_scroll_up():
                self.draw_scroll_up_button(surf)
            if self.can_scroll_down():
                self.draw_scroll_down_button(surf)

    def draw_scroll_up_button(self, surface):
        r = self.scroll_up_rect()
        c = self.scroll_button_color
        draw.polygon(surface, c, [r.bottomleft, r.midtop, r.bottomright])

    def draw_scroll_down_button(self, surface):
        r = self.scroll_down_rect()
        c = self.scroll_button_color
        draw.polygon(surface, c, [r.topleft, r.midbottom, r.topright])

    def mouse_move(self, e):
        self.mouse_drag(e)

    def mouse_drag(self, e):
        item = self.find_enabled_item(e)
        if item is not self._hilited:
            self._hilited = item
            self.invalidate()

    def mouse_up(self, e):
        if 1 <= e.button <= 3:
            item = self.find_enabled_item(e)
            if item:
                self.dismiss(self._items.index(item))

    def find_enabled_item(self, e):
        x, y = e.local
        if 0 <= x < (self.width - self.margin - self.scroll_button_size
                     if self.scrolling else self.width):
            h = self.font.get_linesize()
            i = (y - h // 2) // h + self.scroll
            items = self._items
            if 0 <= i < len(items):
                item = items[i]
                if item.enabled:
                    return item

    def mouse_down(self, event):
        if event.button == 1:
            if self.scrolling:
                p = event.local
                if self.scroll_up_rect().collidepoint(p):
                    self.scroll_up()
                    return
                elif self.scroll_down_rect().collidepoint(p):
                    self.scroll_down()
                    return
        if event.button == 4:
            self.scroll_up()
        if event.button == 5:
            self.scroll_down()

        Dialog.mouse_down(self, event)

    def scroll_up(self):
        if self.can_scroll_up():
            self.scroll = max(self.scroll - self.scroll_page, 0)

    def scroll_down(self):
        if self.can_scroll_down():
            self.scroll = min(self.scroll + self.scroll_page,
                              len(self._items) - self.scroll_items)

    def can_scroll_up(self):
        return self.scrolling and self.scroll > 0

    def can_scroll_down(self):
        return (self.scrolling and
                self.scroll + self.scroll_items < len(self._items))

    def find_item_for_key(self, e):
        for item in self._items:
            if item.keycode == e.key \
                and item.shift == e.shift and item.alt == e.alt:
                    focus = get_focus()
                    if self.command_is_enabled(item, focus):
                        return self._items.index(item)
                    else:
                        return -1
        return -1

    def get_command(self, i):
        if i >= 0:
            item = self._items[i]
            cmd = item.command
            if cmd:
                return cmd + '_cmd'

    def invoke_item(self, i):
        cmd = self.get_command(i)
        if cmd:
            get_focus().handle_command(cmd)
