from pygame import Rect, draw
from grid_view import GridView
from utils import frame_rect
from theme import ThemeProperty


class PaletteView(GridView):
    #  nrows   int   No. of displayed rows
    #  ncols   int   No. of displayed columns
    #
    #  Abstract methods:
    #
    #    num_items()  -->  no. of items
    #    draw_item(surface, item_no, rect)
    #    click_item(item_no, event)
    #    item_is_selected(item_no)  -->  bool

    sel_width = ThemeProperty('sel_width')
    zebra_color = ThemeProperty('zebra_color')
    scroll_button_size = ThemeProperty('scroll_button_size')
    scroll_button_color = ThemeProperty('scroll_button_color')
    highlight_style = ThemeProperty('highlight_style')
        # 'frame' or 'fill' or 'reverse' or None

    def __init__(self, cell_size, nrows, ncols, scrolling=False, **kwds):
        GridView.__init__(self, cell_size, nrows, ncols, **kwds)
        self.scrolling = scrolling
        if scrolling:
            d = self.scroll_button_size
            #l = self.width
            #b = self.height
            self.width += d
            #self.scroll_up_rect = Rect(l, 0, d, d).inflate(-4, -4)
            #self.scroll_down_rect = Rect(l, b - d, d, d).inflate(-4, -4)
        self.scroll = 0

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

    def draw(self, surface):

        GridView.draw(self, surface)
        if self.can_scroll_up():
            self.draw_scroll_up_button(surface)
        if self.can_scroll_down():
            self.draw_scroll_down_button(surface)

    def draw_scroll_up_button(self, surface):
        r = self.scroll_up_rect()
        c = self.scroll_button_color
        draw.polygon(surface, c, [r.bottomleft, r.midtop, r.bottomright])

    def draw_scroll_down_button(self, surface):
        r = self.scroll_down_rect()
        c = self.scroll_button_color
        draw.polygon(surface, c, [r.topleft, r.midbottom, r.topright])

    def draw_cell(self, surface, row, col, rect):
        i = self.cell_to_item_no(row, col)
        if i is not None:
            highlight = self.item_is_selected(i)
            self.draw_item_and_highlight(surface, i, rect, highlight)

    def draw_item_and_highlight(self, surface, i, rect, highlight):
        if i % 2:
            surface.fill(self.zebra_color, rect)
        if highlight:
            self.draw_prehighlight(surface, i, rect)
        if highlight and self.highlight_style == 'reverse':
            fg = self.inherited('bg_color') or self.sel_color
        else:
            fg = self.fg_color
        self.draw_item_with(surface, i, rect, fg)
        if highlight:
            self.draw_posthighlight(surface, i, rect)

    def draw_item_with(self, surface, i, rect, fg):
        old_fg = self.fg_color
        self.fg_color = fg
        try:
            self.draw_item(surface, i, rect)
        finally:
            self.fg_color = old_fg

    def draw_prehighlight(self, surface, i, rect):
        if self.highlight_style == 'reverse':
            color = self.fg_color
        else:
            color = self.sel_color
        self.draw_prehighlight_with(surface, i, rect, color)

    def draw_prehighlight_with(self, surface, i, rect, color):
        style = self.highlight_style
        if style == 'frame':
            frame_rect(surface, color, rect, self.sel_width)
        elif style == 'fill' or style == 'reverse':
            surface.fill(color, rect)

    def draw_posthighlight(self, surface, i, rect):
        pass

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

        GridView.mouse_down(self, event)

    def scroll_up(self):
        if self.can_scroll_up():
            self.scroll -= self.items_per_page() / 2

    def scroll_down(self):
        if self.can_scroll_down():
            self.scroll += self.items_per_page() / 2

    def scroll_to_item(self, n):
        i = max(0, min(n, self.num_items() - 1))
        p = self.items_per_page()
        self.scroll = p * (i // p)

    def can_scroll_up(self):
        return self.scrolling and self.scroll > 0

    def can_scroll_down(self):
        return self.scrolling and self.scroll + self.items_per_page() < self.num_items()

    def items_per_page(self):
        return self.num_rows() * self.num_cols()

    def click_cell(self, row, col, event):
        i = self.cell_to_item_no(row, col)
        if i is not None:
            self.click_item(i, event)

    def cell_to_item_no(self, row, col):
        i = self.scroll + row * self.num_cols() + col
        if 0 <= i < self.num_items():
            return i
        else:
            return None

    def num_rows(self):
        ch = self.cell_size[1]
        if ch:
            return self.height // ch
        else:
            return 0

    def num_cols(self):
        width = self.width
        if self.scrolling:
            width -= self.scroll_button_size
        cw = self.cell_size[0]
        if cw:
            return width // cw
        else:
            return 0

    def item_is_selected(self, n):
        return False

    def click_item(self, n, e):
        pass
