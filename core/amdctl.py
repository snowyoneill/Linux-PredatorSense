## ------------------------------##
## ------ AMD CPU controls ------##
# ---------------------------------##
# Voltage monitoring and undervolting for AMD-based Predator / Nitro
# laptops, via the amdctl utility (https://github.com/kevinlekiller/amdctl).
# Ported from Linux-NitroSense.
# ---------------------------------##

from core.commandrunner import CommandRunner

_status_runner = CommandRunner()
_undervolt_runner = CommandRunner()
# Global process better perf instead of creating and destroying every update cycle
_voltage_process = CommandRunner()


def checkUndervoltStatus(self):
    _status_runner.run("amdctl", ["-m", "-g", "-c0"])
    underVoltStatus = _status_runner.output
    # remove the first 3 lines which are not needed
    underVoltStatus = underVoltStatus.splitlines()[3:]
    # we only want column 0, 5, 6, 7, 10 and 11
    underVoltStatus = "\n".join(
        f"{cols[0]}\t{cols[5]}\t{cols[6].replace('.00', '')}\t{cols[7]}\t{cols[11]}"
        for cols in (line.split() for line in underVoltStatus)
        if len(cols) > 11
    )

    self.undervolt = underVoltStatus


## Apply the undervoltage offset values. amdctl works in VID steps of 16 mV,
## so the requested core offset in mV is converted to steps (min 1).
def applyUndervolt(self, core, cache):
    vid = max(1, round(core / 16))
    _undervolt_runner.run("amdctl", ["-m", f"-v{vid}"])
    checkUndervoltStatus(self)


## Update the current VCore
def checkVoltage(self):
    _voltage_process.run("amdctl", ["-g", "-c0"])
    voltage = _voltage_process.output
    voltages = []
    for line in voltage.splitlines():
        if "mV" in line:
            for comp in line.split():
                if "mV" in comp:
                    voltages.append(int(comp.replace("mV", "")) / 1000)

    if voltages:
        avg_v = sum(voltages) / len(voltages)

        self.voltage = avg_v

        if avg_v < self.minrecordedVoltage:
            self.minrecordedVoltage = avg_v
        if avg_v > self.maxrecordedVoltage:
            self.maxrecordedVoltage = avg_v
