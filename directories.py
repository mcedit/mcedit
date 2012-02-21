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


import sys
import os

def win32_utf8_argv():                                                                                               
    """Uses shell32.GetCommandLineArgvW to get sys.argv as a list of UTF-8                                           
    strings.                                                                                                         

    Versions 2.5 and older of Python don't support Unicode in sys.argv on                                            
    Windows, with the underlying Windows API instead replacing multi-byte                                            
    characters with '?'.                                                                                             

    Returns None on failure.                                                                                         

    Example usage:                                                                                                   

    >>> def main(argv=None):                                                                                         
    ...    if argv is None:                                                                                          
    ...        argv = win32_utf8_argv() or sys.argv                                                                  
    ...                                                                                                              
    """                                                                                                              

    try:                                                                                                             
        from ctypes import POINTER, byref, cdll, c_int, windll                                                       
        from ctypes.wintypes import LPCWSTR, LPWSTR                                                                  

        GetCommandLineW = cdll.kernel32.GetCommandLineW                                                              
        GetCommandLineW.argtypes = []                                                                                
        GetCommandLineW.restype = LPCWSTR                                                                            

        CommandLineToArgvW = windll.shell32.CommandLineToArgvW                                                       
        CommandLineToArgvW.argtypes = [LPCWSTR, POINTER(c_int)]                                                      
        CommandLineToArgvW.restype = POINTER(LPWSTR)                                                                 

        cmd = GetCommandLineW()                                                                                      
        argc = c_int(0)                                                                                              
        argv = CommandLineToArgvW(cmd, byref(argc))                                                                  
        if argc.value > 0:                                                                                           
#            # Remove Python executable if present                                                                    
#            if argc.value - len(sys.argv) == 1:                                                                      
#                start = 1                                                                                            
#            else:                                                                                                    
#                start = 0                                                                                            
            return [argv[i] for i in                                                                 
                    xrange(0, argc.value)]                                                                       
    except Exception:                                                                                                
        pass

def findDirectories():
    #print 'CWD:', os.getcwdu()

    def fsdecode(x): return x.decode(sys.getfilesystemencoding());

    argzero = fsdecode(sys.argv[0])
    #print "EXE", fsdecode(sys.executable)
    #print "ARGV", map(fsdecode, sys.argv)

    if sys.platform == "win32":
        if sys.executable.endswith("python.exe") or sys.executable.endswith("pythonw.exe"):
            dataDir = os.path.split(argzero)[0]
            runningInEditor = True
        else:
            dataDir = os.path.split(sys.executable.decode(sys.getfilesystemencoding()))[0]
            runningInEditor = False
    elif sys.platform == "darwin":
        dataDir = os.getcwdu()
        runningInEditor = False
    else:
        if argzero.endswith("mcedit.pyo"):
            dataDir = os.path.split(argzero)[0]
            runningInEditor = False
        else:
            dataDir = os.getcwdu()
            runningInEditor = True

    #print "Parent Dir: ", dataDir

    if not runningInEditor:
        if u'MCEditData' in os.listdir(os.getcwdu()):
            dataDir = os.path.join(os.getcwdu(), u'MCEditData')
        #else:
        #    raise RuntimeError, "Cannot find MCEditData! (did you start from the right directory?)"

    if not len(dataDir):
        print "DataDir was empty, using cwd."
        dataDir = os.getcwdu()

    #docsFolder = mcplatform.documents_folder()

    if runningInEditor:
        print "Running in development mode!"

    os.chdir(os.path.abspath(dataDir))
    return dataDir, runningInEditor

dataDir, runningInEditor = findDirectories()
