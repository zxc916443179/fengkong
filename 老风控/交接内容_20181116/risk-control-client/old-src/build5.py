from distutils.core import setup
import py2exe

## py2exe are not supported on py3.5/py3.6
## use py3.4 instead
setup( windows = ['client5.py'] ,
        zipfile = None,
        options = { 'py2exe' : {
            "bundle_files": 1,
            "dll_excludes": ["MSVCP90.dll", "w9xpopen.exe"],
            "includes": ["sip"],
            "compressed": 1,
            "optimize": 1
            }
        }
)

