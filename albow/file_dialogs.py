# -*- coding: utf-8 -*-
#
#   Albow - File Dialogs
#

import os
from pygame import draw, Rect
from pygame.locals import *
from albow.widget import Widget
from albow.dialogs import Dialog, ask, alert
from albow.controls import Label, Button
from albow.fields import TextField
from albow.layout import Row, Column
from albow.palette_view import PaletteView
from albow.theme import ThemeProperty


class DirPathView(Widget):

    def __init__(self, width, client, **kwds):
        Widget.__init__(self, **kwds)
        self.set_size_for_text(width)
        self.client = client

    def draw(self, surf):
        frame = self.get_margin_rect()
        image = self.font.render(self.client.directory, True, self.fg_color)
        tw = image.get_width()
        mw = frame.width
        if tw <= mw:
            x = 0
        else:
            x = mw - tw
        surf.blit(image, (frame.left + x, frame.top))


class FileListView(PaletteView):

    #scroll_button_color = (255, 255, 0)

    def __init__(self, width, client, **kwds):
        font = self.predict_font(kwds)
        h = font.get_linesize()
        d = 2 * self.predict(kwds, 'margin')
        PaletteView.__init__(self, (width - d, h), 10, 1, scrolling=True, **kwds)
        self.client = client
        self.selection = None
        self.names = []

    def update(self):
        client = self.client
        dir = client.directory
        suffixes = client.suffixes

        def filter(name):
            path = os.path.join(dir, name)
            return os.path.isdir(path) or self.client.filter(path)

        try:
            names = [name for name in os.listdir(dir) if filter(name)]
                #if not name.startswith(".") and filter(name)]
        except EnvironmentError, e:
            alert(u"%s: %s" % (dir, e))
            names = []
        self.names = sorted(names)
        self.selection = None
        self.scroll = 0

    def num_items(self):
        return len(self.names)

    #def draw_prehighlight(self, surf, item_no, rect):
    #    draw.rect(surf, self.sel_color, rect)

    def draw_item(self, surf, item_no, rect):
        font = self.font
        color = self.fg_color
        buf = self.font.render(self.names[item_no], True, color)
        surf.blit(buf, rect)

    def click_item(self, item_no, e):
        self.selection = item_no
        self.client.dir_box_click(e.num_clicks == 2)

    def item_is_selected(self, item_no):
        return item_no == self.selection

    def get_selected_name(self):
        sel = self.selection
        if sel is not None:
            return self.names[sel]
        else:
            return ""


class FileDialog(Dialog):

    box_width = 250
    default_prompt = None
    up_button_text = ThemeProperty("up_button_text")

    def __init__(self, prompt=None, suffixes=None, **kwds):
        Dialog.__init__(self, **kwds)
        label = None
        d = self.margin
        self.suffixes = suffixes or ("",)
        up_button = Button(self.up_button_text, action=self.go_up)
        dir_box = DirPathView(self.box_width - up_button.width - 10, self)
        self.dir_box = dir_box
        top_row = Row([dir_box, up_button])
        list_box = FileListView(self.box_width - 16, self)
        self.list_box = list_box
        ctrls = [top_row, list_box]
        prompt = prompt or self.default_prompt
        if prompt:
            label = Label(prompt)
        if self.saving:
            filename_box = TextField(self.box_width)
            filename_box.change_action = self.update
            filename_box._enter_action = filename_box.enter_action
            filename_box.enter_action = self.enter_action
            self.filename_box = filename_box
            ctrls.append(Column([label, filename_box], align='l', spacing=0))
        else:
            if label:
                ctrls.insert(0, label)
        ok_button = Button(self.ok_label, action=self.ok, enable=self.ok_enable)
        self.ok_button = ok_button
        cancel_button = Button("Cancel", action=self.cancel)
        vbox = Column(ctrls, align='l', spacing=d)
        vbox.topleft = (d, d)
        y = vbox.bottom + d
        ok_button.topleft = (vbox.left, y)
        cancel_button.topright = (vbox.right, y)
        self.add(vbox)
        self.add(ok_button)
        self.add(cancel_button)
        self.shrink_wrap()
        self._directory = None
        self.directory = os.getcwdu()
        #print "FileDialog: cwd =", repr(self.directory) ###
        if self.saving:
            filename_box.focus()

    def get_directory(self):
        return self._directory

    def set_directory(self, x):
        x = os.path.abspath(x)
        while not os.path.exists(x):
            y = os.path.dirname(x)
            if y == x:
                x = os.getcwdu()
                break
            x = y
        if self._directory != x:
            self._directory = x
            self.list_box.update()
            self.update()

    directory = property(get_directory, set_directory)

    def filter(self, path):
        suffixes = self.suffixes
        if not suffixes or os.path.isdir(path):
            #return os.path.isfile(path)
            return True
        for suffix in suffixes:
            if path.endswith(suffix.lower()):
                return True

    def update(self):
        pass

    def go_up(self):
        self.directory = os.path.dirname(self.directory)
        self.list_box.scroll_to_item(0)

    def dir_box_click(self, double):
        if double:
            name = self.list_box.get_selected_name()
            path = os.path.join(self.directory, name)
            suffix = os.path.splitext(name)[1]
            if suffix not in self.suffixes and os.path.isdir(path):
                self.directory = path
            else:
                self.double_click_file(name)
        self.update()

    def enter_action(self):
        self.filename_box._enter_action()
        self.ok()

    def ok(self):
        self.dir_box_click(True)
        #self.dismiss(True)

    def cancel(self):
        self.dismiss(False)

    def key_down(self, evt):
        k = evt.key
        if k == K_RETURN or k == K_KP_ENTER:
            self.dir_box_click(True)
        if k == K_ESCAPE:
            self.cancel()


class FileSaveDialog(FileDialog):

    saving = True
    default_prompt = "Save as:"
    ok_label = "Save"

    def get_filename(self):
        return self.filename_box.value

    def set_filename(self, x):
        dsuf = self.suffixes[0]
        if x.endswith(dsuf):
            x = x[:-len(dsuf)]
        self.filename_box.value = x

    filename = property(get_filename, set_filename)

    def get_pathname(self):
        path = os.path.join(self.directory, self.filename_box.value)
        suffixes = self.suffixes
        if suffixes and not path.endswith(suffixes[0]):
            path = path + suffixes[0]
        return path

    pathname = property(get_pathname)

    def double_click_file(self, name):
        self.filename_box.value = name

    def ok(self):
        path = self.pathname
        if os.path.exists(path):
            answer = ask("Replace existing '%s'?" % os.path.basename(path))
            if answer != "OK":
                return
        #FileDialog.ok(self)
        self.dismiss(True)

    def update(self):
        FileDialog.update(self)

    def ok_enable(self):
        return self.filename_box.text != ""


class FileOpenDialog(FileDialog):

    saving = False
    ok_label = "Open"

    def get_pathname(self):
        name = self.list_box.get_selected_name()
        if name:
            return os.path.join(self.directory, name)
        else:
            return None

    pathname = property(get_pathname)

    #def update(self):
    #    FileDialog.update(self)

    def ok_enable(self):
        path = self.pathname
        enabled = self.item_is_choosable(path)
        return enabled

    def item_is_choosable(self, path):
        return bool(path) and self.filter(path)

    def double_click_file(self, name):
        self.dismiss(True)


class LookForFileDialog(FileOpenDialog):

    target = None

    def __init__(self, target, **kwds):
        FileOpenDialog.__init__(self, **kwds)
        self.target = target

    def item_is_choosable(self, path):
        return path and os.path.basename(path) == self.target

    def filter(self, name):
        return name and os.path.basename(name) == self.target


def request_new_filename(prompt=None, suffix=None, extra_suffixes=None,
        directory=None, filename=None, pathname=None):
    if pathname:
        directory, filename = os.path.split(pathname)
    if extra_suffixes:
        suffixes = extra_suffixes
    else:
        suffixes = []
    if suffix:
        suffixes = [suffix] + suffixes
    dlog = FileSaveDialog(prompt=prompt, suffixes=suffixes)
    if directory:
        dlog.directory = directory
    if filename:
        dlog.filename = filename
    if dlog.present():
        return dlog.pathname
    else:
        return None


def request_old_filename(suffixes=None, directory=None):
    dlog = FileOpenDialog(suffixes=suffixes)
    if directory:
        dlog.directory = directory
    if dlog.present():
        return dlog.pathname
    else:
        return None


def look_for_file_or_directory(target, prompt=None, directory=None):
    dlog = LookForFileDialog(target=target, prompt=prompt)
    if directory:
        dlog.directory = directory
    if dlog.present():
        return dlog.pathname
    else:
        return None
