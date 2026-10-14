## ------------------------------##
## ----- Intel CPU controls -----##
# ---------------------------------##
# Voltage monitoring and undervolting for Intel-based Predator / Nitro
# laptops. Voltage is read directly from MSR 0x198 via /dev/cpu/*/msr in
# pure Python - no msr-tools / rdmsr dependency required.
# ---------------------------------##

import os
import struct
import sys

from core.commandrunner import CommandRunner

## undervolt (https://github.com/georgewhewell/undervolt) lives in the local venv
UNDERVOLT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "venv", "lib", "python3.12", "site-packages", "undervolt.py",
)

# Reuse one runner per purpose instead of creating/destroying one every update
_undervolt_runner = CommandRunner()
_status_runner = CommandRunner()


## Read the current undervoltage offsets
def checkUndervoltStatus(self):
    _status_runner.run("sudo", [sys.executable, UNDERVOLT_PATH, "-r"])
    self.undervolt = _status_runner.output


## Apply the undervoltage offset values (negative mV)
def applyUndervolt(self, core, cache):
    _undervolt_runner.run(
        "sudo",
        [
            sys.executable,
            UNDERVOLT_PATH,
            "--core", "-" + str(core),
            "--cache", "-" + str(cache),
        ],
    )
    ## Confirm the settings were properly applied
    checkUndervoltStatus(self)


## Read VCore (VID) from MSR 0x198 bits 47:32 on every core, via /dev/cpu/*/msr
def read_all_voltages():
    msr_reg = 0x198
    voltages = []

    try:
        cpus = sorted([int(d) for d in os.listdir("/dev/cpu/") if d.isdigit()])
    except FileNotFoundError:
        return voltages

    for cpu in cpus:
        try:
            with open(f"/dev/cpu/{cpu}/msr", "rb") as f:
                f.seek(msr_reg)
                raw_bytes = f.read(8)
                raw_val = struct.unpack("Q", raw_bytes)[0]
                # Extract bits 47:32 and scale
                vid = (raw_val >> 32) & 0xFFFF
                voltages.append(vid / 8192.0)
        except Exception:
            continue

    return voltages


## Update the current VCore
def checkVoltage(self):
    data = read_all_voltages()

    if data:
        avg_v = sum(data) / len(data)
        voltage = avg_v

        self.voltage = voltage

        if voltage < self.minrecordedVoltage:
            self.minrecordedVoltage = voltage
        if voltage > self.maxrecordedVoltage:
            self.maxrecordedVoltage = voltage
