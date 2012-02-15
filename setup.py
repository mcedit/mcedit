from esky import bdist_esky
from setuptools import setup

import os
import sys
import glob
import platform

LONG_DESC = '''
World / Saved Game Editor for the indie game Minecraft

Import and export creations from saved games. Brush tools allow modifying
terrain on a larger scale. Create, remove, and regenerate chunks in modern
'infinite' Minecraft levels.

Works with saved games from Minecraft Classic, Indev, Infdev, Alpha, Beta,
Release, and Pocket Edition.
'''

# setup() options that are common on all platforms.
SETUP_COMMON = {
    # General fields,
    'name': 'MCEdit',
    'version': '0.1.1',
    'description': 'Minecraft World Editor',
    'long_description': LONG_DESC,

    'author': 'David Vierra',
    'author_email': 'codewarrior0@gmail.com',

    'maintainer': 'MCDevs',
    'maintainer_email': 'mcdevs@tkte.ch',

    'url': 'http://www.github.com/mcedit/mcedit',

    # PyPi,
    'keywords': 'minecraft world editor',
    'classifiers': [
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
    ],

    # Building,
    'packages': [
        'pymclevel',
    ],
    'package_data': {
        'pymclevel': [
            '*.yaml',
            '*.txt',
            '_nbt.*'
        ]
    },
    'scripts': [
        'main.py'
    ]
}

ESKY_OPTIONS = {
    'bdist_esky': {
        'includes':[
            'ctypes',
            'logging',
            'OpenGL.arrays.*',
            'OpenGL.platform',
            'OpenGL.platform.win32',
            'encodings'
        ],
        'excludes':[
            'Tkconstants',
            'Tkinter',
            'tcl',
            'Cython'
        ],
        'freezer_options': {
            'optimize': 2,
            'compressed': True,
            'bundle_files': 3,
            'dll_excludes': [
                'mswsock.dll',
                'powrprof.dll'
            ],
        }
    }
}

def build_nbt():
    """
    Builds _nbt.py.
    """
    os.chdir('pymclevel')
    os.system(sys.executable + ' setup.py build_ext --inplace --force')
    os.chdir('..')

def setup_win32():
    """
    Packing setup for Windows 32/64.
    """
    import py2exe

    # This little ditty makes sure the font module is available
    origIsSystemDLL = py2exe.build_exe.isSystemDLL
    def isSystemDLL(pathname):
        if os.path.basename(pathname).lower() in ['sdl_ttf.dll']:
            return 0
        return origIsSystemDLL(pathname)
    py2exe.build_exe.isSystemDLL = isSystemDLL

def get_data_files(*args):
    return [(d, glob.glob(d+'/*')) for d in args]

def main():
    build_nbt()
    if platform.system() == 'Windows':
        setup_win32()

    data_files = get_data_files('fonts', 'toolicons') + [
        ('', [
            'history.txt',
            'README.html',
            'favicon.png',
            'terrain-classic.png',
            'terrain-pocket.png',
            'char.png',
            'gui.png',
            'terrain.png'
        ])
    ]

    setup(
        data_files=data_files,
        options=ESKY_OPTIONS,
        **SETUP_COMMON
    )


if __name__ == '__main__':
    main()
