from distutils.core import setup
import py2exe

setup( windows=['client4.py'],
        zipfile = None,
        options = {'py2exe' : {
            "bundle_files": 1,
            "dll_excludes": ["MSVCP90.dll", "w9xpopen.exe", "numpy-atlas.dll"],
            "includes": ["sip"],
            "compressed": 1,
            "optimize": 2,
            }
        }
)
