#!/usr/bin/env python3
"""Offscreen smoke test for PredatorSense using --preview (no root, no hardware).

Run from the repo root:
    QT_QPA_PLATFORM=offscreen python3 tests/smoke_test.py

Loads main.py up to (but not including) app.exec() into a namespace, then
exercises config persistence and the LCD-overdrive bitwise round-trip against
the simulated EC.
"""
import os
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Use a throwaway preview config dir so we never touch /etc.
PREVIEW_CACHE = os.path.join(
    os.path.expanduser("~"), ".cache", "predatorsense-preview-test"
)
shutil.rmtree(PREVIEW_CACHE, ignore_errors=True)

sys.argv = ["main.py", "--preview", "Predator PH315-54"]

src = open(os.path.join(REPO, "main.py")).read()
code = src[: src.index("app.exec()")]
ns = {"__name__": "__main__", "__file__": os.path.join(REPO, "main.py")}
exec(compile(code, "main.py", "exec"), ns)

app = ns["app"]
win = ns["application"]
ECS = ns["ECS"]
DEVICE = ns["DEVICE"]

# Redirect config into the throwaway dir.
ns["CONFIG_FOLDER"] = PREVIEW_CACHE
ns["CONFIG_FILE"] = os.path.join(PREVIEW_CACHE, "predatorsense.conf")

# --- Test 1: power-mode persistence (quiet mode round-trips through save) ---
win.setQuietMode()
win.saveState()
conf = open(ns["CONFIG_FILE"]).read().split()
mode_saved = int(conf[4])
assert mode_saved == int(ECS.QUIETMODE.value, 0), "quiet mode not persisted"

# --- Test 2: LCD overdrive bitwise round-trip on shared register 0x21 --------
if DEVICE.has_lcd_overdrive:
    gpu_reg = int(ECS.GPU_FAN_MODE_CONTROL.value, 0)
    base = win.ECHandler.ec_read(gpu_reg)
    win.toggleLCDOverdrive(True)
    on = win.ECHandler.ec_read(gpu_reg)
    assert on & 0x08, "overdrive bit not set"
    assert on & DEVICE.gpu_mode_mask == base & DEVICE.gpu_mode_mask, "fan mode corrupted"
    win.toggleLCDOverdrive(False)
    off = win.ECHandler.ec_read(gpu_reg)
    assert not (off & 0x08), "overdrive bit not cleared"

# --- Test 3: undervolt dropdown maps index -> mV (20 mV steps) ---------------
dd = win.undervolt_dropdown
assert dd.findText("-80 mV") == 4, "-80 mV not selectable"
assert dd.itemText(dd.count() - 1) == "-700 mV", "dropdown range wrong"

print("SMOKE TEST OK")
print("config contents:", conf)
shutil.rmtree(PREVIEW_CACHE, ignore_errors=True)
win.shutdown()
