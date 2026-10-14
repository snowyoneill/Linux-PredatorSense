# Render the Home tab offscreen for both brands and save screenshots.
# Each brand runs in a subprocess: main.py creates a QApplication at import
# time, and only one QApplication may exist per process.
# Usage: ./venv/bin/python tests/shot_home.py
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out_dir = os.path.dirname(os.path.abspath(__file__))

SNIPPET = """
import os, sys
sys.argv = ["main.py", "--preview", "%(model)s"]
root = %(root)r
src = open(os.path.join(root, "main.py")).read()
code = src[: src.index("app.exec()")]
ns = {"__name__": "__main__", "__file__": os.path.join(root, "main.py")}
exec(compile(code, "main.py", "exec"), ns)
win = ns["application"]
win.show()
ns["app"].processEvents()
win.grab().save(%(out)r)
win.shutdown()
"""

for brand, model in (("predator", "Predator PH315-54"), ("nitro", "Nitro AN515-46")):
    out = os.path.join(out_dir, f"home_{brand}.png")
    code = SNIPPET % {"model": model, "root": REPO, "out": out}
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    r = subprocess.run([sys.executable, "-c", code], env=env, cwd=REPO)
    print(brand, "exit", r.returncode, "->", out if r.returncode == 0 else "FAILED")
