#
#   Albow - Shell
#

from root import RootWidget

#------------------------------------------------------------------------------


class Shell(RootWidget):

    def __init__(self, surface, **kwds):
        RootWidget.__init__(self, surface, **kwds)
        self.current_screen = None

    def show_screen(self, new_screen):
        old_screen = self.current_screen
        if old_screen is not new_screen:
            if old_screen:
                old_screen.leave_screen()
            self.remove(old_screen)
            self.add(new_screen)
            self.current_screen = new_screen
            if new_screen:
                new_screen.focus()
                new_screen.enter_screen()

    def begin_frame(self):
        screen = self.current_screen
        if screen:
            screen.begin_frame()
