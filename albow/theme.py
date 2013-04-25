#
#    Albow - Themes
#

import resource

debug_theme = False


class ThemeProperty(object):

    def __init__(self, name):
        self.name = name
        self.cache_name = intern("_" + name)

    def __get__(self, obj, owner):
        if debug_theme:
            print "%s(%r).__get__(%r)" % (self.__class__.__name__, self.name, obj)
        try:  ###
            cache_name = self.cache_name
            try:
                return getattr(obj, cache_name)
            except AttributeError, e:
                if debug_theme:
                    print e
                value = self.get_from_theme(obj.__class__, self.name)
                obj.__dict__[cache_name] = value
                return value
        except:  ###
            if debug_theme:
                import traceback
                traceback.print_exc()
                print "-------------------------------------------------------"
            raise  ###

    def __set__(self, obj, value):
        if debug_theme:
            print "Setting %r.%s = %r" % (obj, self.cache_name, value)  ###
        obj.__dict__[self.cache_name] = value

    def get_from_theme(self, cls, name):
        return root.get(cls, name)


class FontProperty(ThemeProperty):

    def get_from_theme(self, cls, name):
        return root.get_font(cls, name)


class ThemeError(Exception):
    pass


class Theme(object):
    #  name   string          Name of theme, for debugging
    #  base   Theme or None   Theme on which this theme is based

    def __init__(self, name, base=None):
        self.name = name
        self.base = base

    def get(self, cls, name):
        try:
            return self.lookup(cls, name)
        except ThemeError:
            raise AttributeError("No value found in theme %s for '%s' of %s.%s" %
                (self.name, name, cls.__module__, cls.__name__))

    def lookup(self, cls, name):
        if debug_theme:
            print "Theme(%r).lookup(%r, %r)" % (self.name, cls, name)
        for base_class in cls.__mro__:
            class_theme = getattr(self, base_class.__name__, None)
            if class_theme:
                try:
                    return class_theme.lookup(cls, name)
                except ThemeError:
                    pass
        else:
            try:
                return getattr(self, name)
            except AttributeError:
                base_theme = self.base
                if base_theme:
                    return base_theme.lookup(cls, name)
                else:
                    raise ThemeError

    def get_font(self, cls, name):
        if debug_theme:
            print "Theme.get_font(%r, %r)" % (cls, name)
        spec = self.get(cls, name)
        if spec:
            if debug_theme:
                print "font spec =", spec
            return resource.get_font(*spec)


root = Theme('root')
root.margin = 3
root.font = (15, "Vera.ttf")
root.fg_color = (255, 255, 255)
root.bg_color = None
root.bg_image = None
root.scale_bg = False
root.border_width = 0
root.border_color = (0, 0, 0)
root.tab_bg_color = None
root.sel_color = (112, 112, 112)
root.highlight_color = None
root.hover_color = None
root.disabled_color = None
root.highlight_bg_color = None
root.hover_bg_color = None
root.enabled_bg_color = None
root.disabled_bg_color = None

root.RootWidget = Theme('RootWidget')
root.RootWidget.bg_color = (0, 0, 0)

root.Button = Theme('Button')
root.Button.font = (17, "VeraBd.ttf")
root.Button.fg_color = (255, 255, 0)
root.Button.highlight_color = (16, 255, 16)
root.Button.disabled_color = (64, 64, 64)
root.Button.hover_color = (255, 255, 225)
root.Button.default_choice_color = (144, 133, 255)
root.Button.default_choice_bg_color = None
root.Button.highlight_bg_color = None
root.Button.enabled_bg_color = (48, 48, 48)
root.Button.disabled_bg_color = None
root.Button.margin = 7
root.Button.border_width = 1
root.Button.border_color = (64, 64, 64)

root.ValueButton = Theme('ValueButton', base=root.Button)

root.Label = Theme('Label')
root.Label.margin = 4

root.SmallLabel = Theme('SmallLabel')
root.SmallLabel.font = (10, 'Vera.ttf')

root.ValueDisplay = Theme('ValueDisplay')
root.ValueDisplay.margin = 4

root.SmallValueDisplay = Theme('SmallValueDisplay')
root.SmallValueDisplay.font = (10, 'Vera.ttf')
root.ValueDisplay.margin = 2

root.ImageButton = Theme('ImageButton')
root.ImageButton.highlight_color = (0, 128, 255)

framed = Theme('framed')
framed.border_width = 1
framed.margin = 3

root.Field = Theme('Field', base=framed)
root.Field.border_color = (128, 128, 128)

root.CheckWidget = Theme('CheckWidget')
root.CheckWidget.smooth = False
root.CheckWidget.border_color = root.Field.border_color

root.Dialog = Theme('Dialog')
root.Dialog.bg_color = (40, 40, 40)
root.Dialog.border_width = 1
root.Dialog.margin = 15

root.DirPathView = Theme('DirPathView', base=framed)

root.FileListView = Theme('FileListView', base=framed)
root.FileListView.scroll_button_color = (255, 255, 0)

root.FileDialog = Theme("FileDialog")
root.FileDialog.up_button_text = "<-"

root.PaletteView = Theme('PaletteView')
root.PaletteView.sel_width = 2
root.PaletteView.scroll_button_size = 16
root.PaletteView.scroll_button_color = (0, 128, 255)
root.PaletteView.highlight_style = 'frame'
root.PaletteView.zebra_color = (48, 48, 48)

root.TextScreen = Theme('TextScreen')
root.TextScreen.heading_font = (24, "VeraBd.ttf")
root.TextScreen.button_font = (18, "VeraBd.ttf")
root.TextScreen.margin = 20

root.TabPanel = Theme('TabPanel')
root.TabPanel.tab_font = (18, "Vera.ttf")
root.TabPanel.tab_height = 24
root.TabPanel.tab_border_width = 0
root.TabPanel.tab_spacing = 4
root.TabPanel.tab_margin = 0
root.TabPanel.tab_fg_color = root.fg_color
root.TabPanel.default_tab_bg_color = (128, 128, 128)
root.TabPanel.tab_area_bg_color = None
root.TabPanel.tab_dimming = 0.75
#root.TabPanel.use_page_bg_color_for_tabs = True

menu = Theme('menu')
menu.bg_color = (64, 64, 64)
menu.fg_color = (255, 255, 255)
menu.disabled_color = (0, 0, 0)
menu.margin = 8
menu.border_color = (192, 192, 192)
menu.scroll_button_size = 16
menu.scroll_button_color = (255, 255, 0)

root.MenuBar = Theme('MenuBar', base=menu)
root.MenuBar.border_width = 0

root.Menu = Theme('Menu', base=menu)
root.Menu.border_width = 1

root.MusicVolumeControl = Theme('MusicVolumeControl', base=framed)
root.MusicVolumeControl.fg_color = (0x40, 0x40, 0x40)
