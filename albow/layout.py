#
#   Albow - Layout widgets
#

from pygame import Rect
from widget import Widget


class RowOrColumn(Widget):

    _is_gl_container = True

    def __init__(self, size, items, kwds):
        align = kwds.pop('align', 'c')
        spacing = kwds.pop('spacing', 10)
        expand = kwds.pop('expand', None)
        if isinstance(expand, int):
            expand = items[expand]
        #if kwds:
        #    raise TypeError("Unexpected keyword arguments to Row or Column: %s"
        #        % kwds.keys())
        Widget.__init__(self, **kwds)
        #print "albow.controls: RowOrColumn: size =", size, "expand =", expand ###
        d = self.d
        longways = self.longways
        crossways = self.crossways
        axis = self.axis
        k, attr2, attr3 = self.align_map[align]
        w = 0
        length = 0
        if isinstance(expand, int):
            expand = items[expand]
        elif not expand:
            expand = items[-1]
        move = ''
        for item in items:
            r = item.rect
            w = max(w, getattr(r, crossways))
            if item is expand:
                item.set_resizing(axis, 's')
                move = 'm'
            else:
                item.set_resizing(axis, move)
                length += getattr(r, longways)
        if size is not None:
            n = len(items)
            if n > 1:
                length += spacing * (n - 1)
            #print "albow.controls: expanding size from", length, "to", size ###
            setattr(expand.rect, longways, max(1, size - length))
        h = w * k // 2
        m = self.margin
        px = h * d[1] + m
        py = h * d[0] + m
        sx = spacing * d[0]
        sy = spacing * d[1]
        for item in items:
            setattr(item.rect, attr2, (px, py))
            self.add(item)
            p = getattr(item.rect, attr3)
            px = p[0] + sx
            py = p[1] + sy
        self.shrink_wrap()

#---------------------------------------------------------------------------


class Row(RowOrColumn):

    d = (1, 0)
    axis = 'h'
    longways = 'width'
    crossways = 'height'
    align_map = {
        't': (0, 'topleft', 'topright'),
        'c': (1, 'midleft', 'midright'),
        'b': (2, 'bottomleft', 'bottomright'),
    }

    def __init__(self, items, width=None, **kwds):
        """
        Row(items, align=alignment, spacing=10, width=None, expand=None)
        align = 't', 'c' or 'b'
        """
        RowOrColumn.__init__(self, width, items, kwds)

#---------------------------------------------------------------------------


class Column(RowOrColumn):

    d = (0, 1)
    axis = 'v'
    longways = 'height'
    crossways = 'width'
    align_map = {
        'l': (0, 'topleft', 'bottomleft'),
        'c': (1, 'midtop', 'midbottom'),
        'r': (2, 'topright', 'bottomright'),
    }

    def __init__(self, items, height=None, **kwds):
        """
        Column(items, align=alignment, spacing=10, height=None, expand=None)
        align = 'l', 'c' or 'r'
        """
        RowOrColumn.__init__(self, height, items, kwds)

#---------------------------------------------------------------------------


class Grid(Widget):

    _is_gl_container = True

    def __init__(self, rows, row_spacing=10, column_spacing=10, **kwds):
        col_widths = [0] * len(rows[0])
        row_heights = [0] * len(rows)
        for j, row in enumerate(rows):
            for i, widget in enumerate(row):
                if widget:
                    col_widths[i] = max(col_widths[i], widget.width)
                    row_heights[j] = max(row_heights[j], widget.height)
        row_top = 0
        for j, row in enumerate(rows):
            h = row_heights[j]
            y = row_top + h // 2
            col_left = 0
            for i, widget in enumerate(row):
                if widget:
                    w = col_widths[i]
                    x = col_left
                    widget.midleft = (x, y)
                col_left += w + column_spacing
            row_top += h + row_spacing
        width = max(1, col_left - column_spacing)
        height = max(1, row_top - row_spacing)
        r = Rect(0, 0, width, height)
        #print "albow.controls.Grid: r =", r ###
        #print "...col_widths =", col_widths ###
        #print "...row_heights =", row_heights ###
        Widget.__init__(self, r, **kwds)
        self.add(rows)

#---------------------------------------------------------------------------


class Frame(Widget):
    #  margin  int        spacing between border and widget

    border_width = 1
    margin = 2

    def __init__(self, client, border_spacing=None, **kwds):
        Widget.__init__(self, **kwds)
        self.client = client
        if border_spacing is not None:
            self.margin = self.border_width + border_spacing
        d = self.margin
        w, h = client.size
        self.size = (w + 2 * d, h + 2 * d)
        client.topleft = (d, d)
        self.add(client)
