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


from esky import bdist_esky
import glob
## ...
## ModuleFinder can't handle runtime changes to __path__, but win32com uses them
#try:
#    # py2exe 0.6.4 introduced a replacement modulefinder.
#    # This means we have to add package paths there, not to the built-in
#    # one.  If this new modulefinder gets integrated into Python, then
#    # we might be able to revert this some day.
#    # if this doesn't work, try import modulefinder
#    try:
#        import py2exe.mf as modulefinder
#    except ImportError:
#        import modulefinder
#    import win32com, sys
#    for p in win32com.__path__[1:]:
#        modulefinder.AddPackagePath("win32com", p)
#    for extra in ["win32com.shell"]: #,"win32com.mapi"
#        __import__(extra)
#        m = sys.modules[extra]
#        for p in m.__path__[1:]:
#            modulefinder.AddPackagePath(extra, p)
#except ImportError:
#    # no build path setup, no worries.
#    pass


from distutils.core import setup

# This little ditty makes sure the font module is available
import os
import py2exe
origIsSystemDLL = py2exe.build_exe.isSystemDLL
def isSystemDLL(pathname):
        if os.path.basename(pathname).lower() in ["sdl_ttf.dll"]:
                return 0
        return origIsSystemDLL(pathname)
py2exe.build_exe.isSystemDLL = isSystemDLL

build_number = 1

NAME = "MCEdit"
VERSION = "0.1.0r"+str(build_number)
DESCRIPTION = "Minecraft World Editor"
LONG_DESC = """World / Saved Game Editor for the indie game Minecraft

Import and export creations from saved games. Brush tools allow modifying terrain
on a larger scale. Create, remove, and regenerate chunks in modern "infinite"
Minecraft levels.

Works with saved games from Minecraft Classic, Indev, Infdev, Alpha, Beta, Release, and Pocket Edition.
"""
AUTHOR = "David Vierra"
AUTHOR_EMAIL = "codewarrior0@gmail.com"
URL = "http://github.com/mcedit/mcedit"
LICENSE = "Creative Commons Attribution;Non-Commercial;No-Derivatives"
KEYWORDS = "minecraft world editor"
CLASSIFIERS = [
    "Programming Language :: Python",
    "Programming Language :: Python :: 2",
]

import platform
ARCH = "win32" if platform.architecture()[0] == "32bit" else "win-amd64"

PACKAGES = ["pymclevel", "pymclevel.yaml"]
EXT_MODULES = []
PACKAGE_DATA = {"pymclevel":["*.yaml", "*.txt", "_nbt.*"]}

def get_data_files(*args):
    return [(d, glob.glob(d+"/*")) for d in args]

DATA_FILES = get_data_files("fonts", "toolicons") + [
    ("", "history.txt README.html favicon.png terrain-classic.png terrain-pocket.png char.png gui.png terrain.png".split()),
]

ESKY_OPTIONS = { 
"bdist_esky": {
    'includes':['ctypes', 'logging', 'OpenGL.arrays.*', 'OpenGL.platform', 'OpenGL.platform.win32', 'encodings'],
    'excludes':["Tkconstants", "Tkinter", "tcl", "Cython"],
    "freezer_options": {
        "optimize":2,
        "compressed":True,
        "bundle_files": 3,
        'dll_excludes': [ "mswsock.dll", "powrprof.dll" ],
        #"skip_archive":True,
    }
    
} 
}

import logging
logging.basicConfig(level=logging.DEBUG)

import os
import sys

#build _nbt.pyd
os.chdir("pymclevel")
os.system(sys.executable + " setup.py build_ext --inplace --force")
os.chdir("..")

setup(name=NAME,
      version=VERSION,
      author=AUTHOR,
      author_email=AUTHOR_EMAIL,
      url=URL,
      description=DESCRIPTION,
      long_description=LONG_DESC,
      keywords=KEYWORDS,
      packages=PACKAGES,
      ext_modules=EXT_MODULES,
      package_data=PACKAGE_DATA,
      data_files=DATA_FILES,
      license=LICENSE,
      classifiers=CLASSIFIERS,
      scripts=["main.py"],
      options=ESKY_OPTIONS,
     )
    