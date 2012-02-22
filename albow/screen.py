#
#   Albow - Screen
#

from widget import Widget

#------------------------------------------------------------------------------


class Screen(Widget):

    def __init__(self, shell, **kwds):
        Widget.__init__(self, shell.rect, **kwds)
        self.shell = shell
        self.center = shell.center

    def begin_frame(self):
        pass

    def enter_screen(self):
        pass

    def leave_screen(self):
        pass
