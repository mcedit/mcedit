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
import collections
import os
import traceback
from albow import FloatField, IntField, AttrRef, Row, Label, Widget, TabPanel, CheckBox, Column, Button, TextFieldWrapped
from editortools.blockview import BlockButton
from editortools.editortool import EditorTool
from glbackground import Panel
from mceutils import ChoiceButton, alertException, setWindowCaption, showProgress
import mcplatform
from operation import Operation
from albow.dialogs import wrapped_label, alert
import pymclevel
from pymclevel import BoundingBox


def alertFilterException(func):
    def _func(*args, **kw):
        try:
            func(*args, **kw)
        except Exception, e:
            print traceback.format_exc()
            alert(u"Exception during filter operation. See console for details.\n\n{0}".format(e))

    return _func

def addNumField(page, optionName, val, min=None, max=None):
        if isinstance(val, float):
            ftype = FloatField
        else:
            ftype = IntField

        if min == max:
            min = None
            max = None

        field = ftype(value=val, width=100, min=min, max=max)
        page.optionDict[optionName] = AttrRef(field, 'value')

        row = Row([Label(optionName), field])
        return row

class FilterModuleOptions(Widget):
    is_gl_container = True

    def __init__(self, tool, module, *args, **kw):
        Widget.__init__(self, *args, **kw)
        self.tool = tool
        pages = TabPanel()
        pages.is_gl_container = True
        self.pages = pages
        self.optionDict = {}
        pageTabContents = []

        print "Creating options for ", module
        if hasattr(module, "inputs"):
            if isinstance(module.inputs, list):
                for tabData in module.inputs:
                    title, page, pageRect = self.makeTabPage(self.tool, tabData)
                    pages.add_page(title, page)
                    pages.set_rect(pageRect.union(pages._rect))
            elif isinstance(module.inputs, tuple):
                title, page, pageRect = self.makeTabPage(self.tool, module.inputs)
                pages.add_page(title, page)
                pages.set_rect(pageRect)
        else:
            self.size = (0, 0)

        pages.shrink_wrap()
        self.add(pages)
        self.shrink_wrap()
        if len(pages.pages):
            if(pages.current_page != None):
                pages.show_page(pages.current_page)
            else:
                pages.show_page(pages.pages[0])

        for eachPage in pages.pages:
            self.optionDict = dict(self.optionDict.items() + eachPage.optionDict.items())

    def makeTabPage(self, tool, inputs):
        page = Widget()
        page.is_gl_container = True
        rows = []
        cols = []
        height = 0
        max_height = 550
        page.optionDict = {}
        page.tool = tool
        title = "Tab"

        for optionName, optionType in inputs:
            if isinstance(optionType, tuple):
                if isinstance(optionType[0], (int, long, float)):
                    if len(optionType) > 2:
                        val, min, max = optionType
                    elif len(optionType) == 2:
                        min, max = optionType
                        val = min

                    rows.append(addNumField(page, optionName, val, min, max))

                if isinstance(optionType[0], (str, unicode)):
                    isChoiceButton = False

                    if optionType[0] == "string":
                        kwds = []
                        wid = None
                        lin = None
                        val = None
                        for keyword in optionType:
                            if isinstance(keyword, (str, unicode)) and keyword != "string":
                                kwds.append(keyword)
                        for keyword in kwds:
                            splitWord = keyword.split('=')
                            if len(splitWord) > 1:
                                v = None
                                key = None

                                try:
                                    v = int(splitWord[1])
                                except:
                                    pass

                                key = splitWord[0]
                                if v is not None:
                                    if key == "lines":
                                        lin = v
                                    elif key == "width":
                                        wid = v
                                else:
                                    if key == "value":
                                        val = splitWord[1]

                        if lin is None:
                            lin = 1
                        if val is None:
                            val = "Input String Here"
                        if wid is None:
                            wid = 200

                        field = TextFieldWrapped(value=val, width=wid,lines=lin)
                        page.optionDict[optionName] = AttrRef(field, 'value')

                        row = Row((Label(optionName), field))
                        rows.append(row)
                    else:
                        isChoiceButton = True

                    if isChoiceButton:
                        choiceButton = ChoiceButton(map(str, optionType))
                        page.optionDict[optionName] = AttrRef(choiceButton, 'selectedChoice')

                        rows.append(Row((Label(optionName), choiceButton)))

            elif isinstance(optionType, bool):
                cbox = CheckBox(value=optionType)
                page.optionDict[optionName] = AttrRef(cbox, 'value')

                row = Row((Label(optionName), cbox))
                rows.append(row)

            elif isinstance(optionType, (int, float)):
                rows.append(addNumField(self, optionName, optionType))

            elif optionType == "blocktype" or isinstance(optionType, pymclevel.materials.Block):
                blockButton = BlockButton(tool.editor.level.materials)
                if isinstance(optionType, pymclevel.materials.Block):
                    blockButton.blockInfo = optionType

                row = Column((Label(optionName), blockButton))
                page.optionDict[optionName] = AttrRef(blockButton, 'blockInfo')

                rows.append(row)
            elif optionType == "label":
                rows.append(wrapped_label(optionName, 50))

            elif optionType == "string":
                field = TextFieldWrapped(value="Input String Here", width=200, lines=1)
                page.optionDict[optionName] = AttrRef(field, 'value')

                row = Row((Label(optionName), field))
                rows.append(row)

            elif optionType == "title":
                title = optionName

            else:
                raise ValueError(("Unknown option type", optionType))

        height = sum(r.height for r in rows)

        if height > max_height:
            h = 0
            for i, r in enumerate(rows):
                h += r.height
                if h > height / 2:
                    break

            cols.append(Column(rows[:i]))
            rows = rows[i:]
        #cols.append(Column(rows))

        if len(rows):
            cols.append(Column(rows))

        if len(cols):
            page.add(Row(cols))
        page.shrink_wrap()

        return (title, page, page._rect)

    @property
    def options(self):
        return dict((k, v.get()) for k, v in self.optionDict.iteritems())

    @options.setter
    def options(self, val):
        for k in val:
            if k in self.optionDict:
                self.optionDict[k].set(val[k])


class FilterToolPanel(Panel):
    def __init__(self, tool):
        Panel.__init__(self)

        self.savedOptions = {}

        self.tool = tool
        self.selectedFilterName = None
        if len(self.tool.filterModules):
            self.reload()

    def reload(self):
        for i in list(self.subwidgets):
            self.remove(i)

        tool = self.tool

        if len(tool.filterModules) is 0:
            self.add(Label("No filter modules found!"))
            self.shrink_wrap()
            return

        if self.selectedFilterName is None or self.selectedFilterName not in tool.filterNames:
            self.selectedFilterName = tool.filterNames[0]

        self.filterOptionsPanel = None
        while self.filterOptionsPanel is None:
            module = self.tool.filterModules[self.selectedFilterName]
            try:
                self.filterOptionsPanel = FilterModuleOptions(self.tool, module)
            except Exception, e:
                alert("Error creating filter inputs for {0}: {1}".format(module, e))
                traceback.print_exc()
                self.tool.filterModules.pop(self.selectedFilterName)
                self.selectedFilterName = tool.filterNames[0]

            if len(tool.filterNames) == 0:
                raise ValueError("No filters loaded!")

        self.filterSelect = ChoiceButton(tool.filterNames, choose=self.filterChanged)
        self.filterSelect.selectedChoice = self.selectedFilterName

        self.confirmButton = Button("Filter", action=self.tool.confirm)

        filterLabel = Label("Filter:", fg_color=(177, 177, 255, 255))
        filterLabel.mouse_down = lambda x: mcplatform.platform_open(mcplatform.filtersDir)
        filterLabel.tooltipText = "Click to open filters folder"
        filterSelectRow = Row((filterLabel, self.filterSelect))

        self.add(Column((filterSelectRow, self.filterOptionsPanel, self.confirmButton)))

        self.shrink_wrap()
        if self.parent:
            self.centery = self.parent.centery

        if self.selectedFilterName in self.savedOptions:
            self.filterOptionsPanel.options = self.savedOptions[self.selectedFilterName]

    def filterChanged(self):
        self.saveOptions()
        self.selectedFilterName = self.filterSelect.selectedChoice
        self.reload()

    filterOptionsPanel = None

    def saveOptions(self):
        if self.filterOptionsPanel:
            self.savedOptions[self.selectedFilterName] = self.filterOptionsPanel.options


class FilterOperation(Operation):
    def __init__(self, editor, level, box, filter, options):
        super(FilterOperation, self).__init__(editor, level)
        self.box = box
        self.filter = filter
        self.options = options

    def perform(self, recordUndo=True):
        if recordUndo:
            self.undoLevel = self.extractUndo(self.level, self.box)

        self.filter.perform(self.level, BoundingBox(self.box), self.options)

        pass

    def dirtyBox(self):
        return self.box


class FilterTool(EditorTool):
    tooltipText = "Filter"
    toolIconName = "filter"

    def __init__(self, editor):
        EditorTool.__init__(self, editor)

        self.filterModules = {}

        self.panel = FilterToolPanel(self)

    @property
    def statusText(self):
        return "Choose a filter, then click Filter or press ENTER to apply it."

    def toolEnabled(self):
        return not (self.selectionBox() is None)

    def toolSelected(self):
        self.showPanel()

    @alertException
    def showPanel(self):
        if self.panel.parent:
            self.editor.remove(self.panel)

        self.reloadFilters()

        #self.panel = FilterToolPanel(self)
        self.panel.reload()

        self.panel.left = self.editor.left
        self.panel.centery = self.editor.centery

        self.editor.add(self.panel)

    def hidePanel(self):
        self.panel.saveOptions()
        if self.panel.parent:
            self.panel.parent.remove(self.panel)

    def reloadFilters(self):
        filterDir = mcplatform.filtersDir
        filterFiles = os.listdir(filterDir)
        filterPyfiles = filter(lambda x: x.endswith(".py"), filterFiles)

        def tryImport(name):
            try:
                return __import__(name)
            except Exception, e:
                print traceback.format_exc()
                alert(u"Exception while importing filter module {}. See console for details.\n\n{}".format(name, e))
                return object()

        filterModules = (tryImport(x[:-3]) for x in filterPyfiles)
        filterModules = filter(lambda module: hasattr(module, "perform"), filterModules)

        self.filterModules = collections.OrderedDict(sorted((self.moduleDisplayName(x), x) for x in filterModules))
        for m in self.filterModules.itervalues():
            try:
                reload(m)
            except Exception, e:
                print traceback.format_exc()
                alert(u"Exception while reloading filter module {}. Using previously loaded module. See console for details.\n\n{}".format(m.__file__, e))

    @property
    def filterNames(self):
        return [self.moduleDisplayName(module) for module in self.filterModules.itervalues()]

    def moduleDisplayName(self, module):
        return module.displayName if hasattr(module, 'displayName') else module.__name__.capitalize()

    @alertFilterException
    def confirm(self):

        with setWindowCaption("APPLYING FILTER - "):
            filterModule = self.filterModules[self.panel.filterSelect.selectedChoice]

            op = FilterOperation(self.editor, self.editor.level, self.selectionBox(), filterModule, self.panel.filterOptionsPanel.options)

            self.editor.level.showProgress = showProgress

            self.editor.addOperation(op)
            self.editor.addUnsavedEdit()

            self.editor.invalidateBox(self.selectionBox())
