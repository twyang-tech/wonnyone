"""Windows launcher for the existing UA naming application."""
from pathlib import Path
import runpy

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().with_name("UA-Naming .py")), run_name="__main__")
