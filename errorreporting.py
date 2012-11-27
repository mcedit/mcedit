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
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

errorreporting.py

Patch the `traceback' module to print "self" with each stack frame.
"""
import collections
import sys
import traceback
import platform
from datetime import datetime
import os
import json
import httplib
import zlib
import release
import logging
log = logging.getLogger(__name__)

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
    for filename, lineno, name, line, selfstr in reversed(extracted_list):
        item = '  File "%s", line %d, in %s %s\n' % (filename, lineno, name, selfstr[:60])
        if line:
            item = item + '    %s\n' % line.strip()
        list.append(item)
    return list

traceback.extract_tb = extract_tb
traceback.format_list = format_list

EXCEPTIONAL_API_KEY = "37eaf2a19432e268829ef4fa35921ad399bbda80"

def sanitize(s):
    import mcplatform
    parentDir = mcplatform.parentDir
    minecraftDir = mcplatform.minecraftDir
    home = os.path.expanduser("~")

    s = s.replace(parentDir, "[MCEdit folder]")
    s = s.replace(repr(parentDir)[1:-1], "[MCEdit folder]")
    s = s.replace(minecraftDir, "[Minecraft folder]")
    s = s.replace(repr(minecraftDir)[1:-1], "[Minecraft folder]")
    s = s.replace(home, "[User home folder]")
    s = s.replace(repr(home)[1:-1], "[User home folder]")
    return s

def get_backtrace():
    backtrace = traceback.format_exc()
    try:
        backtrace = sanitize(backtrace)

    except Exception, e:
        print repr(e), "while scrubbing user directories from crash log! Error not reported."
        raise

    return backtrace.split('\n')

def json_crash_report():
    exc_class, exc_value, exc_tb = sys.exc_info()

    report = {}
    # We don't handle requests, so repurpose the request fields for release info.
    request = report['request'] = {}
    request['controller'] = release.release

    exception = report['exception'] = {}
    exception['backtrace'] = get_backtrace()
    exception['exception_class'] = exc_class.__name__
    try:
        exception['message'] = sanitize(str(exc_value))
    except:
        exception['message'] = ""

    exception['occurred_at'] = datetime.now().isoformat()

    try:
        os.getcwdu().encode('ascii')
        ascii_cwd = True
    except UnicodeEncodeError:
        ascii_cwd = False

    app_env = report['application_environment'] = {}
    app_env['application_root_directory'] = "ASCII" if ascii_cwd else "Unicode"
    app_env['framework'] = 'mcedit'
    app_env['language'] = 'python'
    app_env['language_version'] = sys.version

    env = app_env['env'] = collections.OrderedDict()

    env['OS_NAME'] = os.name,
    env['OS_VERSION'] = platform.version()
    env['OS_ARCH'] = platform.architecture()
    env['OS_PLATFORM'] = platform.platform()
    env['OS_CPU'] = platform.processor()

    env['FS_ENCODING'] = sys.getfilesystemencoding()

    if 'LANG' in os.environ:
        env['LANG'] = os.environ['LANG']

    try:
        from albow import root
        env['FRAMES'] = str(root.get_root().frames)
    except:
        log.info("Can't get frame count")

    try:
        from OpenGL import GL
        env['GL_VERSION'] = GL.glGetString(GL.GL_VERSION)
    except:
        log.info("Can't get GL_VERSION")

    try:
        from OpenGL import GL
        env['GL_VENDOR'] = GL.glGetString(GL.GL_VENDOR)
    except:
        log.info("Can't get GL_VENDOR")


    try:
        from OpenGL import GL
        env['GL_RENDERER'] = GL.glGetString(GL.GL_RENDERER)
    except:
        log.info("Can't get GL_RENDERER")

    return json.dumps(report)

def post_crash_report():
    """
    POST http://api.exceptional.io/api/errors?api_key=YOUR_API_KEY&protocol_version=5

    Note: protocol_version 5 means use zlib compression.
    """

    report = json_crash_report()

    body = zlib.compress(report)
    conn = httplib.HTTPConnection("api.exceptional.io")
    conn.request("POST", "http://api.exceptional.io/api/errors?api_key=%s&protocol_version=5" % EXCEPTIONAL_API_KEY, body)

    resp = conn.getresponse()
    print "Response status: %s\n Response data: %s\n" % (resp.status, resp.read())
    conn.close()


def reportException():
    try:
        import config
        if config.config.get("Settings", "report crashes new"):
            post_crash_report()
    except Exception, e:
        print "Error while reporting crash: ", repr(e)
