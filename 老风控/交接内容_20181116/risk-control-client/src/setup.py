
import sys
from cx_Freeze import setup, Executable

build_exe_options = {
        "includes": ["atexit"],
        "packages": ["os", "numpy", "lxml"],
        #"packages": ["os", "lxml"],
        "excludes": ["tkinter"]
        }

ClientGui = Executable(
        script = "client.py",
        base = "Win32GUI",
        )

setup(  name = "risk_control_client",
        version = "2.0.0",
        description = "Risk Control Client",
        options = {"build_exe": build_exe_options},
        executables = [ClientGui])

