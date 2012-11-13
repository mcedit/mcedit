from sets import Set
from albow import Label, TextField, Row, TableView, TableColumn, Column, Widget, Button, AttrRef
from albow.dialogs import Dialog
import toolbasics
from glbackground import GLBackground
from mceutils import CheckBoxLabel

from pymclevel.materials import Block

def anySubtype(self):
    bl = Block(self.materials, self.ID, self.blockData)
    bl.wildcard = True
    return bl

Block.anySubtype = anySubtype
Block.wildcard = False  # True if


class BlockPicker(Dialog):
    is_gl_container = True

    def __init__(self, blockInfo, materials, *a, **kw):
        self.allowWildcards = False
        Dialog.__init__(self, *a, **kw)
        panelWidth = 350

        self.materials = materials
        self.anySubtype = blockInfo.wildcard

        self.matchingBlocks = materials.allBlocks

        try:
            self.selectedBlockIndex = self.matchingBlocks.index(blockInfo)
        except ValueError:
            self.selectedBlockIndex = 0
            for i, b in enumerate(self.matchingBlocks):
                if blockInfo.ID == b.ID and blockInfo.blockData == b.blockData:
                    self.selectedBlockIndex = i
                    break

        lbl = Label("Search")
        # lbl.rect.topleft = (0,0)

        fld = TextField(300)
        # fld.rect.topleft = (100, 10)
        # fld.centery = lbl.centery
        # fld.left = lbl.right

        fld.change_action = self.textEntered
        fld.enter_action = self.ok
        fld.escape_action = self.cancel

        self.awesomeField = fld

        searchRow = Row((lbl, fld))

        def formatBlockName(x):
            block = self.matchingBlocks[x]
            r = "({id}:{data}) {name}".format(name=block.name, id=block.ID, data=block.blockData)
            if block.aka:
                r += " [{0}]".format(block.aka)

            return r

        tableview = TableView(columns=[TableColumn(" ", 24, "l", lambda x: ""), TableColumn("(ID) Name [Aliases]", 276, "l", formatBlockName)])
        tableicons = [toolbasics.BlockView(materials) for i in range(tableview.rows.num_rows())]
        for t in tableicons:
            t.size = (16, 16)
            t.margin = 0
        icons = Column(tableicons, spacing=2)

        # tableview.margin = 5
        tableview.num_rows = lambda: len(self.matchingBlocks)
        tableview.row_data = lambda x: (self.matchingBlocks[x], x, x)
        tableview.row_is_selected = lambda x: x == self.selectedBlockIndex
        tableview.click_row = self.selectTableRow
        draw_table_cell = tableview.draw_table_cell

        def draw_block_table_cell(surf, i, data, cell_rect, column):
            if isinstance(data, Block):

                tableicons[i - tableview.rows.scroll].blockInfo = data
            else:
                draw_table_cell(surf, i, data, cell_rect, column)

        tableview.draw_table_cell = draw_block_table_cell
        tableview.width = panelWidth
        tableview.anchor = "lrbt"
        # self.add(tableview)
        self.tableview = tableview
        tableWidget = Widget()
        tableWidget.add(tableview)
        tableWidget.shrink_wrap()

        def wdraw(*args):
            for t in tableicons:
                t.blockInfo = materials.Air

        tableWidget.draw = wdraw
        self.blockButton = blockView = toolbasics.BlockThumbView(materials, self.blockInfo)

        blockView.centerx = self.centerx
        blockView.top = tableview.bottom

        # self.add(blockview)

        but = Button("OK")
        but.action = self.ok
        but.top = blockView.bottom
        but.centerx = self.centerx
        but.align = "c"
        but.height = 30

        if self.allowWildcards:
        # self.add(but)
            anyRow = CheckBoxLabel("Any Subtype", ref=AttrRef(self, 'anySubtype'), tooltipText="Replace blocks with any data value. Only useful for Replace operations.")
            col = Column((searchRow, tableWidget, anyRow, blockView, but))
        else:
            col = Column((searchRow, tableWidget, blockView, but))
        col.anchor = "wh"
        self.anchor = "wh"

        panel = GLBackground()
        panel.bg_color = [i / 255. for i in self.bg_color]
        panel.anchor = "tlbr"
        self.add(panel)

        self.add(col)
        self.add(icons)
        icons.topleft = tableWidget.topleft
        icons.top += tableWidget.margin + 30
        icons.left += tableWidget.margin + 4

        self.shrink_wrap()
        panel.size = self.size

        try:
            self.tableview.rows.scroll_to_item(self.selectedBlockIndex)
        except:
            pass

    @property
    def blockInfo(self):
        if len(self.matchingBlocks):
            bl = self.matchingBlocks[self.selectedBlockIndex]
            if self.anySubtype:
                return bl.anySubtype()
            else:
                return bl

        else:
            return self.materials.Air

    def selectTableRow(self, i, e):
        oldIndex = self.selectedBlockIndex

        self.selectedBlockIndex = i
        self.blockButton.blockInfo = self.blockInfo
        if e.num_clicks > 1 and oldIndex == i:
            self.ok()

    def textEntered(self):
        text = self.awesomeField.text
        blockData = 0
        try:
            if ":" in text:
                text, num = text.split(":", 1)
                blockData = int(num) & 0xf
                blockID = int(text) & 0xff
            else:
                blockID = int(text) & 0xff

            block = self.materials.blockWithID(blockID, blockData)

            self.matchingBlocks = [block]
            self.selectedBlockIndex = 0
            self.tableview.rows.scroll_to_item(self.selectedBlockIndex)
            self.blockButton.blockInfo = self.blockInfo

            return
        except ValueError:
            pass
        except Exception, e:
            print repr(e)

        blocks = self.materials.allBlocks

        matches = blocks
        oldBlock = self.materials.Air
        if len(self.matchingBlocks):
            oldBlock = self.matchingBlocks[self.selectedBlockIndex]

        if len(text):
            matches = self.materials.blocksMatching(text)
            if blockData:
                ids = set(b.ID for b in matches)
                matches = sorted([self.materials.blockWithID(id, blockData) for id in ids])

            self.matchingBlocks = matches
        else:
            self.matchingBlocks = blocks

        if oldBlock in self.matchingBlocks:
            self.selectedBlockIndex = self.matchingBlocks.index(oldBlock)
        else:
            self.selectedBlockIndex = 0

        self.tableview.rows.scroll_to_item(self.selectedBlockIndex)
        self.blockButton.blockInfo = self.blockInfo
