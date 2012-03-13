import os.path


def get_version():
    """
    Loads the build version from the bundled version file, if available.
    """
    if not os.path.exists('RELEASE-VERSION'):
        return

    fin = open('RELEASE-VERSION', 'rb')
    v = fin.read().strip()
    fin.close()

    return v

release = get_version()
