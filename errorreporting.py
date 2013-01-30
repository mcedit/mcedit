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
import directories
import mcplatform
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
            selfstr = self and "(self is a {0})".format(self.__class__.__name__) or " "
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
    tb = sys.exc_traceback
    backtrace = []
    for filename, lineno, name, line, selfstr in extract_tb(tb):
        backtrace.append({
            "file":os.path.normpath(filename).replace(directories.dataDir, ""),
            "line":lineno,
            "symbol":name,
        })

    return backtrace

def json_crash_report():
    """
    fields = arguments[1] || new Object();
        fields.api_key = this.options.APIKey;
        fields.environment = this.options.environment;
        fields.client = "javascript";
        fields.revision = this.options.revision;
        fields.class_name = error.type || error.name;
        if (!error.name && (matches = error.message.match(/^(Uncaught )?(\w+): (.+)/))) {
          fields.class_name = matches[2];
          fields.message = matches[3];
        } else {
          fields.message = error.message;
        }
        if ((_ref5 = fields.class_name) == null) {
          fields.class_name = 'Error';
        }
        fields.backtraces = buildBacktrace(error.stack);
        fields.capture_method = error.mode;
        fields.occurred_at = ISODateString(new Date());
        fields.schema = window.location.protocol.replace(/:$/, '');
        fields.host = window.location.hostname;
        if (window.location.port.length > 0) {
          fields.port = window.location.port;
        }
        fields.path = window.location.pathname;
        fields.query = window.location.search;
        if (window.location.hash !== '') {
          fields.fragment = window.location.hash;
        }
        fields.user_agent = navigator.userAgent;
        fields.screen_width = screen.width;
        fields.screen_height = screen.height;
        fields.window_width = window.innerWidth;
        fields.window_height = window.innerHeight;
        fields.color_depth = screen.colorDepth;
    :return:
    :rtype:
    """
    exc_class, exc_value, exc_tb = sys.exc_info()

    fields = {}
    fields['revision'] = release.commit
    fields['build'] = release.release

    fields['client'] = 'MCEdit Client(?)'

    fields['backtraces'] = [{
        "name":"Crashed Thread",
        "faulted": True,
        "backtrace": get_backtrace(),
    }]

    fields['class_name'] = exc_class.__name__
    if isinstance(exc_value, UnicodeError):
        fields['message'] = exc_class.__name__
    else:
        try:
            fields['message'] = sanitize(str(exc_value))
        except:
            fields['message'] = ""

    fields['occurred_at'] = datetime.now().isoformat()

    try:
        os.getcwdu().encode('ascii')
        ascii_cwd = True
    except UnicodeEncodeError:
        ascii_cwd = False

    fields['environment'] = "development"
    fields['application_root_directory'] = "ASCII" if ascii_cwd else "Unicode"
    fields['language_version'] = sys.version

    fields['api_key'] = "6ea52b17-ac76-4fd8-8db4-2d7303473ca2"
    fields['OS_NAME'] = os.name
    fields['OS_VERSION'] = platform.version()
    fields['OS_ARCH'] = platform.architecture()
    fields['OS_PLATFORM'] = platform.platform()
    fields['OS_CPU'] = platform.processor()

    fields['FS_ENCODING'] = sys.getfilesystemencoding()

    if 'LANG' in os.environ:
        fields['LANG'] = os.environ['LANG']

    try:
        from albow import root
        fields['FRAMES'] = str(root.get_root().frames)
    except:
        log.info("Can't get frame count")

    try:
        from OpenGL import GL
        fields['GL_VERSION'] = GL.glGetString(GL.GL_VERSION)
    except:
        log.info("Can't get GL_VERSION")

    try:
        from OpenGL import GL
        fields['GL_VENDOR'] = GL.glGetString(GL.GL_VENDOR)
    except:
        log.info("Can't get GL_VENDOR")


    try:
        from OpenGL import GL
        fields['GL_RENDERER'] = GL.glGetString(GL.GL_RENDERER)
    except:
        log.info("Can't get GL_RENDERER")

    return json.dumps(fields)

def post_crash_report():
    """

        body = JSON.stringify(fields);
        this.HTTPTransmit(this.options.APIHost + this.options.notifyPath, [['Content-Type', 'application/json']], body);
    """

    report = json_crash_report()

    #conn = httplib.HTTPConnection("192.168.1.108", 3000)
    #conn.request("POST", "http://192.168.1.108:3000/bugs", body)
    conn = httplib.HTTPConnection("bugs.mcedit.net")
    headers = { "Content-type": "application/octet-stream" }

    conn.request("POST", "/bugs.php?foo=bar", report, headers)


    resp = conn.getresponse()
    print "Response status: %s\n Response data: %s\n" % (resp.status, resp.read())
    conn.close()


def reportException():
    try:
        import config
        if config.config.getboolean("Settings", "report crashes new"):
            post_crash_report()
    except Exception, e:
        print "Error while reporting crash: ", repr(e)
