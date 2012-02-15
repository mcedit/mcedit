# MCEdit

MCEdit is an open-source, BSD-licenced world editor for the viral indie hit [Minecraft](http://www.minecraft.net/).

## For Developers

MCEdit is written in Python using a variety of open source modules. When developing it is recommended to use virtualenv to keep dependencies sane and to easy deployment.

### Development Quick Guide

You'll need Python 2.6+ and `easy_install`/`pip` at a minimum before getting started. This quick guide assumes a unix-y OS.

Clone MCEdit:

```bash
git clone https://github.com/mcdevs/mcedit
cd mcedit
git submodule init
git submodule update
```

Optionally (but highly recommended), setup and activate [virtualenv](http://pypi.python.org/pypi/virtualenv). virtualenv will simplify development by creating an isolated and barebones Python environment. Anything you install while virtualenv is active won't affect your system-wide Python installation, for example.

```bash
easy_install virtualenv
virtualenv ENV
. ENV/bin/activate
```

Install various dependencies. This may take a bit (especially numpy). If installing pygame errors, try installing from a [binary packages](http://pygame.org/install.html) or following one of the guides from that page to install from source.

```bash
easy_install PyOpenGL
easy_install numpy
easy_install pygame
easy_install pyyaml
```

You should now be able to run MCEdit with `python main.py` assuming you've installed all the dependencies correctly.
