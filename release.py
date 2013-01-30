import os.path
import subprocess
import directories

def get_version():
    """
    Loads the build version from the bundled version file, if available.
    """
    if not os.path.exists(os.path.join(directories.dataDir, 'RELEASE-VERSION')):
        try:
            return subprocess.check_output('git describe --tags --match=*.*.*'.split()).strip()
        except:
            return 'unknown'

    fin = open(os.path.join(directories.dataDir, 'RELEASE-VERSION'), 'rb')
    v = fin.read().strip()
    fin.close()

    return v

def get_commit():
    """
    Loads the git commit ID from the bundled version file, if available.
    """
    if not os.path.exists(os.path.join(directories.dataDir, 'GIT-COMMIT')):
        try:
            return subprocess.check_output('git rev-parse HEAD'.split()).strip()
        except:
            return 'unknown'

    fin = open(os.path.join(directories.dataDir, 'GIT-COMMIT'), 'rb')
    v = fin.read().strip()
    fin.close()

    return v

release = get_version()
commit = get_commit()
