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

"""
errorreporting.py

Patch the `traceback' module to print "self" with each stack frame.
"""
import sys
import traceback
import platform
from datetime import datetime
import os
import httplib

def extract_tb(tb, limit=None):
    """Return list of up to limit pre-processed entries from traceback.

    This is useful for alternate formatting of stack traces.  If
    'limit' is omitted or None, all entries are extracted.  A
    pre-processed stack trace entry is a quadruple (filename, line
    number, function name, text) representing the information that is
    usually printed for a stack trace.  The text is a string with
    leading and trailing whitespace stripped; if the source is not
    available it is None.
    """
    if limit is None:
        if hasattr(sys, 'tracebacklimit'):
            limit = sys.tracebacklimit
    list = []
    n = 0
    while tb is not None and (limit is None or n < limit):
        f = tb.tb_frame
        lineno = tb.tb_lineno
        co = f.f_code
        filename = co.co_filename
        name = co.co_name
        self = f.f_locals.get('self')
        try:
            selfstr = self and "(self={0})".format(self) or " "
        except:
            selfstr = " "
        traceback.linecache.checkcache(filename)
        line = traceback.linecache.getline(filename, lineno, f.f_globals)
        if line:
            line = line.strip()
        else:
            line = None
        list.append((filename, lineno, name, line, selfstr))
        tb = tb.tb_next
        n = n + 1
    return list


def format_list(extracted_list):
    """Format a list of traceback entry tuples for printing.

    Given a list of tuples as returned by extract_tb() or
    extract_stack(), return a list of strings ready for printing.
    Each string in the resulting list corresponds to the item with the
    same index in the argument list.  Each string ends in a newline;
    the strings may contain internal newlines as well, for those items
    whose source text line is not None.
    """
    list = []
    for filename, lineno, name, line, selfstr in extracted_list:
        item = '  File "%s", line %d, in %s %s\n' % (filename, lineno, name, selfstr[:60])
        if line:
            item = item + '    %s\n' % line.strip()
        list.append(item)
    return list

traceback.extract_tb = extract_tb
traceback.format_list = format_list

def clamp(num, low, high):
    return min(high, max(low, num))

def releaseInfo():
    import release

    uname = platform.uname()
    uname = list(uname)
    uname[1] = hex(hash(uname[1]))

    info = """Release: MCEdit-{0}\n{1}
Platform: {2}, Name: {3}, Version{4}, Arch: {5}
Platform:{6}, Processor: {7}, 
uname: {8}
""".format(release.release, datetime.now(), sys.platform, os.name, platform.version(), platform.architecture(), platform.platform(), platform.processor(), uname)
    try:
        from OpenGL import GL
        info += "Version: {0}\n".format(GL.glGetString(GL.GL_VERSION))
        info += "Vendor: {0}\nRenderer: {1}\n".format(GL.glGetString(GL.GL_VENDOR), GL.glGetString(GL.GL_RENDERER))
        from albow import root
        info += "Frames: {0}\n".format(root.get_root().frames)

    finally:
        return info



def reportCrash(crashlog):
    try:
        import mcplatform
        parentDir = mcplatform.parentDir
        minecraftDir = mcplatform.minecraftDir


        if hasattr(sys, 'frozen') or sys.platform != "win32":
            crashlog = crashlog.replace(parentDir, "[MCEdit folder]")
            crashlog = crashlog.replace(minecraftDir, "[Minecraft folder]")
    except Exception, e:
        print repr(e), "while scrubbing user directories from crash log!"

    releaseString = releaseInfo()
    crashlog = releaseString + crashlog
    print crashlog
#    logfilename = "mcedit-{0}-crash.log".format(os.getpid())
#    if not os.path.exists("logs"):
#        try:
#            os.mkdir("logs")
#            logfilename = os.path.join("logs", logfilename)
#        except Exception, e:
#            print "Couldn't make logs dir!", repr(e)


    #with open(logfilename, "w") as f:
    #    f.write(crashlog)
    #print "This info has also been logged to " + logfilename
#    try:
#        import config
#        if not config.config.getboolean('Settings', 'Report Crashes'): return;
#    except Exception, e:
#        print repr(e), "while retrieving Report Crashes setting. Reporting anyway."
#
#    print "Crash log length: ", len(crashlog)
#    conn = httplib.HTTPConnection("company.com")
#    conn.request("POST", "/bugs.php", crashlog)
#    resp = conn.getresponse().read()
#    conn.close()
#    print "Response length: ", len(resp)
#    #print resp
#    print ""
#    print "The above traceback was automatically reported to the author."
#    print "To disable crash reporting, "
#    print "Open MCEdit.ini and set Report Crashes to 0."

def reportException(exc):
    tb = traceback.format_exc()
    try:
        reportCrash(tb)
    except Exception, e:
        print "Error while reporting crash: ", repr(e)
