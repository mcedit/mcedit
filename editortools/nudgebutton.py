from numpy.core.umath import absolute
from pygame import key
from albow import Label
from pymclevel.box import Vector
import config
from glbackground import GLBackground

class NudgeButton(GLBackground):
    """ A button that captures movement keys while pressed and sends them to a listener as nudge events.
    Poorly planned. """

    is_gl_container = True

    def __init__(self):
        GLBackground.__init__(self)
        nudgeLabel = Label("Nudge", margin=8)

        self.add(nudgeLabel)
        self.shrink_wrap()

        # tooltipBacking = Panel()
        # tooltipBacking.bg_color = (0, 0, 0, 0.6)
        keys = [config.config.get("Keys", k).upper() for k in ("Forward", "Back", "Left", "Right", "Up", "Down")]

        nudgeLabel.tooltipText = "Click and hold.  While holding, use the movement keys ({0}{1}{2}{3}{4}{5}) to nudge. Hold SHIFT to nudge faster.".format(*keys)
        # tooltipBacking.shrink_wrap()

    def mouse_down(self, event):
        self.focus()

    def mouse_up(self, event):
        self.get_root().mcedit.editor.focus_switch = None  # xxxx restore focus to editor better

    def key_down(self, evt):
        keyname = key.name(evt.key)
        if keyname == config.config.get("Keys", "Up"):
            self.nudge(Vector(0, 1, 0))
        if keyname == config.config.get("Keys", "Down"):
            self.nudge(Vector(0, -1, 0))

        Z = self.get_root().mcedit.editor.mainViewport.cameraVector  # xxx mouthful
        absZ = map(abs, Z)
        if absZ[0] < absZ[2]:
            forward = (0, 0, (-1 if Z[2] < 0 else 1))
        else:
            forward = ((-1 if Z[0] < 0 else 1), 0, 0)

        back = map(int.__neg__, forward)
        left = forward[2], forward[1], -forward[0]
        right = map(int.__neg__, left)

        if keyname == config.config.get("Keys", "Forward"):
            self.nudge(Vector(*forward))
        if keyname == config.config.get("Keys", "Back"):
            self.nudge(Vector(*back))
        if keyname == config.config.get("Keys", "Left"):
            self.nudge(Vector(*left))
        if keyname == config.config.get("Keys", "Right"):
            self.nudge(Vector(*right))
