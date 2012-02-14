Required packages:
    
    Python 2.6 or 2.7
    numpy 1.3+
    pyopengl 3.0.0+
    pygame 1.9.1+
    pyyaml

Required to build accelerated _nbt.pyx module:

    Cython
    cc or gcc
    Python (development files)
    
Ubuntu, Debian, and similar:
    apt-get install python-numpy python-opengl python-pygame
    apt-get install cython python-dev gcc
    
FreeBSD:
    Install the following ports: graphics/py-opengl devel/py-game
    These will pull in the needed dependencies.