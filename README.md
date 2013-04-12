# MCEdit

MCEdit is an open-source, BSD-licenced world editor for the viral indie hit [Minecraft](http://www.minecraft.net/). For downloads and update info, visit the official website at [www.mcedit.net](http://www.mcedit.net/). The rest of this file is intended for computer programmers and Linux users.

## Running from source

MCEdit is written in Python using a variety of open source modules. When developing it is recommended to use virtualenv to keep dependencies sane and for easy deployment. You'll need Python 2.7 and `easy_install`/`pip` at a minimum before getting started. This quick guide assumes a unix-y OS.

Clone MCEdit:

```bash
git clone --recursive https://github.com/mcedit/mcedit
```
Or, if you've already cloned MCEdit in the past and need to update, go to the existing source folder:
```bash
git pull --recurse-submodules
```

Optionally (but highly recommended), setup and activate [virtualenv](http://pypi.python.org/pypi/virtualenv). virtualenv will simplify development by creating an isolated and barebones Python environment. Anything you install while virtualenv is active won't affect your system-wide Python installation, for example.

```bash
cd mcedit
easy_install virtualenv
virtualenv ENV
. ENV/bin/activate
```

Install various dependencies. This may take a bit (especially numpy). If installing pygame errors, try installing from a [binary packages](http://pygame.org/install.html) or following one of the guides from that page to install from source. On Windows, `easy_install` is preferred because it installs prebuilt binary packages. On Linux and Mac OS X, you may want to use `pip install` instead.

```bash
easy_install PyOpenGL
easy_install numpy
easy_install pygame
easy_install pyyaml
```

Ubuntu Linux users can install the following packages via apt-get to grab all the dependencies easily and install them into the system python. This also downloads all libraries required to build these modules using `pip install`

```bash
apt-get install python-opengl python-pygame python-yaml python-numpy
```

You should now be able to run MCEdit with `python mcedit.py` assuming you've installed all the dependencies correctly.

