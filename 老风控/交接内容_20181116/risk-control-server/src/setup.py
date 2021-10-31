
import sys
from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {
        "packages": ["os", "numpy", "lxml", "requests"],
        "excludes": ["tkinter"]
        }

# GUI applications require a different base on Windows (the default is for a
# console application).
base = None
if sys.platform == "win32":
    base = "Win32GUI"

ReaderConsole = Executable(
        script = "reader.py",
        base = "Console",
        )

ServerConsole = Executable(
        script = "server.py",
        base = "Console",
        )

setup(  name = "server",
        version = "2.0.0",
        description = "Program Deal with pbrc logs.",
        options = {"build_exe": build_exe_options},
        executables = [ReaderConsole, ServerConsole])
        #executables = [Executable("reader.py")])
        #executables = [Executable("test.py", base=base)])

