from pygame import Rect
from widget import Widget


class GridView(Widget):
    #  cell_size   (width, height)   size of each cell
    #
    #  Abstract methods:
    #
    #    num_rows()  -->  no. of rows
    #    num_cols()  -->  no. of columns
    #    draw_cell(surface, row, col, rect)
    #    click_cell(row, col, event)

    def __init__(self, cell_size, nrows, ncols, **kwds):
        """nrows, ncols are for calculating initial size of widget"""
        Widget.__init__(self, **kwds)
        self.cell_size = cell_size
        w, h = cell_size
        d = 2 * self.margin
        self.size = (w * ncols + d, h * nrows + d)
        self.cell_size = cell_size

    def draw(self, surface):
        for row in xrange(self.num_rows()):
            for col in xrange(self.num_cols()):
                r = self.cell_rect(row, col)
                self.draw_cell(surface, row, col, r)

    def cell_rect(self, row, col):
        w, h = self.cell_size
        d = self.margin
        x = col * w + d
        y = row * h + d
        return Rect(x, y, w, h)

    def draw_cell(self, surface, row, col, rect):
        pass

    def mouse_down(self, event):
        if event.button == 1:
            x, y = event.local
            w, h = self.cell_size
            W, H = self.size
            d = self.margin
            if d <= x < W - d and d <= y < H - d:
                row = (y - d) // h
                col = (x - d) // w
                self.click_cell(row, col, event)

    def click_cell(self, row, col, event):
        pass
