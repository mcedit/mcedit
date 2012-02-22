#---------------------------------------------------------------------------
#
#   Albow - Music
#
#---------------------------------------------------------------------------

from __future__ import division
import os
from random import randrange

try:
    from pygame.mixer import music
except ImportError:
    music = None
    print "Music not available"

if music:
    import root
    music.set_endevent(root.MUSIC_END_EVENT)

from resource import resource_path
from root import schedule

#---------------------------------------------------------------------------

fadeout_time = 1  # Time over which to fade out music (sec)
change_delay = 2  # Delay between end of one item and starting the next (sec)

#---------------------------------------------------------------------------

music_enabled = True
current_music = None
current_playlist = None
next_change_delay = 0

#---------------------------------------------------------------------------


class PlayList(object):
    """A collection of music filenames to be played sequentially or
    randomly. If random is true, items will be played in a random order.
    If repeat is true, the list will be repeated indefinitely, otherwise
    each item will only be played once."""

    def __init__(self, items, random=False, repeat=False):
        self.items = list(items)
        self.random = random
        self.repeat = repeat

    def next(self):
        """Returns the next item to be played."""
        items = self.items
        if items:
            if self.random:
                n = len(items)
                if self.repeat:
                    n = (n + 1) // 2
                i = randrange(n)
            else:
                i = 0
            item = items.pop(i)
            if self.repeat:
                items.append(item)
            return item

#---------------------------------------------------------------------------


def get_music(*names, **kwds):
    """Return the full pathname of a music file from the "music" resource
    subdirectory."""
    prefix = kwds.pop('prefix', "music")
    return resource_path(prefix, *names)


def get_playlist(*names, **kwds):
    prefix = kwds.pop('prefix', "music")
    dirpath = get_music(*names, **{'prefix': prefix})
    items = [os.path.join(dirpath, filename)
        for filename in os.listdir(dirpath)
            if not filename.startswith(".")]
    items.sort()
    return PlayList(items, **kwds)


def change_playlist(new_playlist):
    """Fade out any currently playing music and start playing from the given
    playlist."""
    #print "albow.music: change_playlist" ###
    global current_music, current_playlist, next_change_delay
    if music and new_playlist is not current_playlist:
        current_playlist = new_playlist
        if music_enabled:
            music.fadeout(fadeout_time * 1000)
            next_change_delay = max(0, change_delay - fadeout_time)
            jog_music()
        else:
            current_music = None


def change_music(new_music, repeat=False):
    """Fade out any currently playing music and start playing the given
    music file."""
    #print "albow.music: change_music" ###
    if music and new_music is not current_music:
        if new_music:
            new_playlist = PlayList([new_music], repeat=repeat)
        else:
            new_playlist = None
        change_playlist(new_playlist)


def music_end():
    #print "albow.music: music_end" ###
    schedule(next_change_delay, jog_music)


def jog_music():
    """If no music is currently playing, start playing the next item
    from the current playlist."""
    if music_enabled and not music.get_busy():
        start_next_music()


def start_next_music():
    """Start playing the next item from the current playlist immediately."""
    #print "albow.music: start_next_music" ###
    global current_music, next_change_delay
    if music_enabled and current_playlist:
        next_music = current_playlist.next()
        if next_music:
            print "albow.music: loading", repr(next_music)  ###
            music.load(next_music)
            music.play()
            next_change_delay = change_delay
        current_music = next_music


def get_music_enabled():
    return music_enabled


def set_music_enabled(state):
    global music_enabled
    if music_enabled != state:
        music_enabled = state
        if state:
            # Music pausing doesn't always seem to work.
            #music.unpause()
            if current_music:
                # After stopping and restarting currently loaded music,
                # fadeout no longer works.
                #print "albow.music: reloading", repr(current_music) ###
                music.load(current_music)
                music.play()
            else:
                jog_music()
        else:
            #music.pause()
            music.stop()

#---------------------------------------------------------------------------

from pygame import Rect
from albow.widget import Widget
from albow.controls import Label, Button, CheckBox
from albow.layout import Row, Column, Grid
from albow.dialogs import Dialog


class EnableMusicControl(CheckBox):

    def get_value(self):
        return get_music_enabled()

    def set_value(self, x):
        set_music_enabled(x)


class MusicVolumeControl(Widget):

    def __init__(self, **kwds):
        Widget.__init__(self, Rect((0, 0), (100, 20)), **kwds)

    def draw(self, surf):
        r = self.get_margin_rect()
        r.width = int(round(music.get_volume() * r.width))
        surf.fill(self.fg_color, r)

    def mouse_down(self, e):
        self.mouse_drag(e)

    def mouse_drag(self, e):
        m = self.margin
        w = self.width - 2 * m
        x = max(0.0, min(1.0, (e.local[0] - m) / w))
        music.set_volume(x)
        self.invalidate()


class MusicOptionsDialog(Dialog):

    def __init__(self):
        Dialog.__init__(self)
        emc = EnableMusicControl()
        mvc = MusicVolumeControl()
        controls = Grid([
            [Label("Enable Music"), emc],
            [Label("Music Volume"), mvc],
        ])
        buttons = Button("OK", self.ok)
        contents = Column([controls, buttons], align='r', spacing=20)
        contents.topleft = (20, 20)
        self.add(contents)
        self.shrink_wrap()


def show_music_options_dialog():
    dlog = MusicOptionsDialog()
    dlog.present()
