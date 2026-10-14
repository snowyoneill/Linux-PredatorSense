## ------------------------------##
## -------Device Registers-------##
# ---------------------------------##
# This module contains the EC register maps for every supported Acer
# Predator / Nitro model, plus runtime detection of the machine we are
# running on (DMI product name) and the CPU vendor (Intel / AMD).
#
# Each device class exposes the register addresses as string hex values
# (e.g. "0x21") so callers keep using int(ECS.<REG>.value, 0) style access
# via the ECS shim below, plus per-device capability flags:
#
#   gpu_mode_mask  : mask applied to the GPU fan mode register before
#                    comparing against GPU_AUTO/TURBO/MANUAL_MODE.
#                    Predator shares 0x21 with LCD overdrive (bit 3),
#                    so its mask is 0xF0; Nitro keeps the full byte.
#   has_turbo_mode : device exposes a 4th "Turbo" power mode (Predator)
#   has_turbo_led  : device has a turbo LED register
#   has_lcd_overdrive : panel is driven by the EC overdrive bit
#   has_trackpad_status : trackpad status register is readable
#
# CAUTION: Changing or using these values on different laptops may cause
# unexpected behavior or damage to the laptop. Use at your own risk.
# ---------------------------------##

import os
import sys


class _BaseDevice:
    """Defaults shared by every device; register maps override as needed."""

    name = "Unknown Acer"
    series = "Predator"

    # Per-device behaviour flags
    gpu_mode_mask = 0xFF
    has_turbo_mode = False
    has_turbo_led = False
    has_lcd_overdrive = False
    has_trackpad_status = False

    # Power-mode register: Predator calls it PREDATORMODE, Nitro calls it
    # NITROMODE - both live at 0x2C, so main code uses the neutral MODE alias.
    MODE = "0x2C"

    # Optional registers (set only where they exist)
    TURBO_LED_CONTROL = None
    TURBO_LED_ON = "0x01"
    TURBO_LED_OFF = "0x00"
    LCDOVERDRIVE = None
    TRACKPADSTATUS = None
    TRACKPADENABLED = "0x00"
    TRACKPADDISABLED = "0x04"
    TURBOMODE = None


class PredatorPH315_54(_BaseDevice):
    ## ------ Predator Helios 300 (2021, PH315-54) ------ ##
    name = "Predator PH315-54"
    series = "Predator"

    # Register 0x21 is shared: upper nibble = GPU fan mode, bit 3 = LCD overdrive
    gpu_mode_mask = 0xF0
    has_turbo_mode = True
    has_turbo_led = True
    has_lcd_overdrive = True
    has_trackpad_status = True

    GPU_FAN_MODE_CONTROL = "0x21"  # Address to set GPU fan mode
    GPU_AUTO_MODE = "0x50"
    GPU_TURBO_MODE = "0x60"
    GPU_MANUAL_MODE = "0x70"
    GPU_MANUAL_SPEED_CONTROL = "0x3A"  # Address to set GPU fan speed

    CPU_FAN_MODE_CONTROL = "0x22"  # Address to set CPU fan mode
    CPU_AUTO_MODE = "0x54"
    CPU_TURBO_MODE = "0x58"
    CPU_MANUAL_MODE = "0x5C"
    CPU_MANUAL_SPEED_CONTROL = "0x37"  # Address to set CPU fan speed

    KB_30_SEC_AUTO = "0x06"  # Address to set keyboard backlight timeout
    KB_30_AUTO_OFF = "0x00"
    KB_30_AUTO_ON = "0x1E"

    CPUFANSPEEDHIGHBITS = "0x13"
    CPUFANSPEEDLOWBITS = "0x14"
    GPUFANSPEEDHIGHBITS = "0x15"
    GPUFANSPEEDLOWBITS = "0x16"

    CPUTEMP = "0xB0"
    GPUTEMP = "0xB7"
    SYSTEMP = "0xB3"

    POWERSTATUS = "0x00"  # Address to read power status
    POWERPLUGGEDIN = "0x01"
    POWERUNPLUGGED = "0x00"

    BATTERYCHARGELIMIT = "0x03"  # Address to set battery charge limit
    BATTERYLIMITON = "0x51"
    BATTERYLIMITOFF = "0x11"

    BATTERYSTATUS = "0xC1"  # Address to read battery status
    BATTERYPLUGGEDINANDCHARGING = "0x02"
    BATTERYDRAINING = "0x01"
    BATTERYOFF = "0x00"

    POWEROFFUSBCHARGING = "0x08"  # Address to switch USB charging on/off
    USBCHARGINGON = "0x0F"
    USBCHARGINGOFF = "0x1F"

    # LCD overdrive lives in bit 3 of the GPU fan mode register
    LCDOVERDRIVE = "0x21"  # (0x_0 = off, 0x_8 = on) - bit 3

    PREDATORMODE = "0x2C"  # Address to change modes
    QUIETMODE = "0x00"
    DEFAULTMODE = "0x01"
    EXTREMEMODE = "0x04"
    TURBOMODE = "0x05"

    TURBO_LED_CONTROL = "0x5B"
    TURBO_LED_ON = "0x01"
    TURBO_LED_OFF = "0x00"

    TRACKPADSTATUS = "0xA1"
    TRACKPADENABLED = "0x00"
    TRACKPADDISABLED = "0x04"


class PredatorHelios300(_BaseDevice):
    ## ------ Predator Helios 300 (2018-2020, G3-5xx / PH315-5x / PH317-5x) ------ ##
    # Same register map as the PH315-54; community reported, untested.
    name = "Predator Helios 300"
    series = "Predator"

    gpu_mode_mask = 0xF0
    has_turbo_mode = True
    has_turbo_led = True
    has_lcd_overdrive = True
    has_trackpad_status = True

    GPU_FAN_MODE_CONTROL = "0x21"
    GPU_AUTO_MODE = "0x50"
    GPU_TURBO_MODE = "0x60"
    GPU_MANUAL_MODE = "0x70"
    GPU_MANUAL_SPEED_CONTROL = "0x3A"

    CPU_FAN_MODE_CONTROL = "0x22"
    CPU_AUTO_MODE = "0x54"
    CPU_TURBO_MODE = "0x58"
    CPU_MANUAL_MODE = "0x5C"
    CPU_MANUAL_SPEED_CONTROL = "0x37"

    KB_30_SEC_AUTO = "0x06"
    KB_30_AUTO_OFF = "0x00"
    KB_30_AUTO_ON = "0x1E"

    CPUFANSPEEDHIGHBITS = "0x13"
    CPUFANSPEEDLOWBITS = "0x14"
    GPUFANSPEEDHIGHBITS = "0x15"
    GPUFANSPEEDLOWBITS = "0x16"

    CPUTEMP = "0xB0"
    GPUTEMP = "0xB7"
    SYSTEMP = "0xB3"

    POWERSTATUS = "0x00"
    POWERPLUGGEDIN = "0x01"
    POWERUNPLUGGED = "0x00"

    BATTERYCHARGELIMIT = "0x03"
    BATTERYLIMITON = "0x51"
    BATTERYLIMITOFF = "0x11"

    BATTERYSTATUS = "0xC1"
    BATTERYPLUGGEDINANDCHARGING = "0x02"
    BATTERYDRAINING = "0x01"
    BATTERYOFF = "0x00"

    POWEROFFUSBCHARGING = "0x08"
    USBCHARGINGON = "0x0F"
    USBCHARGINGOFF = "0x1F"

    LCDOVERDRIVE = "0x21"

    PREDATORMODE = "0x2C"
    QUIETMODE = "0x00"
    DEFAULTMODE = "0x01"
    EXTREMEMODE = "0x04"
    TURBOMODE = "0x05"

    TURBO_LED_CONTROL = "0x5B"

    TRACKPADSTATUS = "0xA1"


class NitroAN515_46(_BaseDevice):
    ## ------ Nitro 5 (AN515-45/46/53/54/55/56/57/58, AN517-55) ------ ##
    name = "Nitro AN515-46"
    series = "Nitro"

    GPU_FAN_MODE_CONTROL = "0x21"  # Address to set GPU fan mode
    GPU_AUTO_MODE = "0x10"
    GPU_TURBO_MODE = "0x20"
    GPU_MANUAL_MODE = "0x30"
    GPU_MANUAL_SPEED_CONTROL = "0x3A"  # Address to set GPU fan speed

    CPU_FAN_MODE_CONTROL = "0x22"  # Address to set CPU fan mode
    CPU_AUTO_MODE = "0x04"
    CPU_TURBO_MODE = "0x08"
    CPU_MANUAL_MODE = "0x0C"
    CPU_MANUAL_SPEED_CONTROL = "0x37"  # Address to set CPU fan speed

    KB_30_SEC_AUTO = "0x06"  # Address to set keyboard backlight timeout
    KB_30_AUTO_OFF = "0x00"
    KB_30_AUTO_ON = "0x1E"

    CPUFANSPEEDHIGHBITS = "0x13"
    CPUFANSPEEDLOWBITS = "0x14"
    GPUFANSPEEDHIGHBITS = "0x15"
    GPUFANSPEEDLOWBITS = "0x16"

    CPUTEMP = "0xB0"
    GPUTEMP = "0xB6"
    SYSTEMP = "0xB3"

    POWERSTATUS = "0x00"  # Address to read power status
    POWERPLUGGEDIN = "0x01"
    POWERUNPLUGGED = "0x00"

    BATTERYCHARGELIMIT = "0x03"  # Address to set battery charge limit
    BATTERYLIMITON = "0x51"
    BATTERYLIMITOFF = "0x11"

    BATTERYSTATUS = "0xC1"  # Address to read battery status
    BATTERYPLUGGEDINANDCHARGING = "0x02"
    BATTERYDRAINING = "0x01"
    BATTERYOFF = "0x00"

    POWEROFFUSBCHARGING = "0x08"  # Address to switch USB charging on/off
    USBCHARGINGON = "0x0F"
    USBCHARGINGOFF = "0x1F"

    NITROMODE = "0x2C"  # Address to change modes
    QUIETMODE = "0x00"
    DEFAULTMODE = "0x01"
    EXTREMEMODE = "0x04"


class NitroAN515_44(_BaseDevice):
    ## ------ Nitro 5 (AN515-44) ------ ##
    name = "Nitro AN515-44"
    series = "Nitro"

    GPU_FAN_MODE_CONTROL = "0x21"  # Address to set GPU fan mode
    GPU_AUTO_MODE = "0x10"
    GPU_TURBO_MODE = "0x20"
    GPU_MANUAL_MODE = "0x30"
    GPU_MANUAL_SPEED_CONTROL = "0x3A"  # Address to set GPU fan speed

    CPU_FAN_MODE_CONTROL = "0x22"  # Address to set CPU fan mode
    CPU_AUTO_MODE = "0x04"
    CPU_TURBO_MODE = "0x08"
    CPU_MANUAL_MODE = "0x0C"
    CPU_MANUAL_SPEED_CONTROL = "0x37"  # Address to set CPU fan speed

    KB_30_SEC_AUTO = "0x06"  # Address to set keyboard backlight timeout
    KB_30_AUTO_OFF = "0x00"
    KB_30_AUTO_ON = "0x1E"

    CPUFANSPEEDHIGHBITS = "0x13"
    CPUFANSPEEDLOWBITS = "0x14"
    GPUFANSPEEDHIGHBITS = "0x15"
    GPUFANSPEEDLOWBITS = "0x16"

    CPUTEMP = "0xB0"
    GPUTEMP = "0xB4"
    SYSTEMP = "0xB0"

    POWERSTATUS = "0x00"  # Address to read power status
    POWERPLUGGEDIN = "0x01"
    POWERUNPLUGGED = "0x00"

    BATTERYCHARGELIMIT = "0x03"  # Address to set battery charge limit
    BATTERYLIMITON = "0x40"
    BATTERYLIMITOFF = "0x00"

    BATTERYSTATUS = "0xC1"  # Address to read battery status
    BATTERYPLUGGEDINANDCHARGING = "0x02"
    BATTERYDRAINING = "0x01"
    BATTERYOFF = "0x00"

    POWEROFFUSBCHARGING = "0x08"  # Address to switch USB charging on/off
    USBCHARGINGON = "0x0F"
    USBCHARGINGOFF = "0x1F"

    NITROMODE = "0x2C"  # Address to change modes
    QUIETMODE = "0x00"
    DEFAULTMODE = "0x01"
    EXTREMEMODE = "0x04"


MODEL_TO_DEVICE = {
    # --- Predator (register map verified on PH315-54) ---
    "Predator PH315-54": PredatorPH315_54,
    # --- Predator Helios 300 family, community reported / untested ---
    "Predator PH315-51": PredatorHelios300,
    "Predator PH315-52": PredatorHelios300,
    "Predator PH315-53": PredatorHelios300,
    "Predator PH317-51": PredatorHelios300,
    "Predator PH317-52": PredatorHelios300,
    "Predator PH317-53": PredatorHelios300,
    # --- Nitro 5 (register maps from Linux-NitroSense) ---
    "Nitro AN515-45": NitroAN515_46,
    "Nitro AN515-46": NitroAN515_46,
    "Nitro AN515-53": NitroAN515_46,
    "Nitro AN515-54": NitroAN515_46,
    "Nitro AN515-55": NitroAN515_46,
    "Nitro AN515-56": NitroAN515_46,
    "Nitro AN515-57": NitroAN515_46,
    "Nitro AN515-58": NitroAN515_46,
    "Nitro AN517-55": NitroAN515_46,
    "Nitro AN515-44": NitroAN515_44,
}


class _ECSShim:
    """Expose the detected device class with the legacy ECS.<REG>.value API."""

    def __init__(self, device):
        self._device = device

    def __getattr__(self, name):
        try:
            value = getattr(self._device, name)
        except AttributeError:
            raise AttributeError(
                f"Register '{name}' is not defined for {self._device.name}"
            )
        if value is None:
            raise AttributeError(
                f"Register '{name}' is not supported on {self._device.name}"
            )
        return _RegValue(value)


class _RegValue:
    __slots__ = ("value",)

    def __init__(self, value):
        self.value = value


def _read_dmi(field):
    path = os.path.join("/sys/class/dmi/id", field)
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return ""


def detect_model():
    """Return the DMI product name, e.g. 'Predator PH315-54'. No deps needed."""
    return _read_dmi("product_name")


def detect_cpu_type():
    """Return 'Intel', 'AMD' or 'Unknown' from /proc/cpuinfo."""
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("vendor_id"):
                    vendor = line.split(":", 1)[1].strip().lower()
                    if "amd" in vendor:
                        return "AMD"
                    if "intel" in vendor:
                        return "Intel"
                    break
    except OSError:
        pass
    return "Unknown"


def detect_device():
    """Detect the running machine and return its device class, or exit."""
    model = detect_model()
    print(f"Detected running on: {model or 'unknown device'}")
    device = MODEL_TO_DEVICE.get(model)
    if device is None:
        print(f"Device '{model}' is not supported!")
        print("Supported models: " + ", ".join(sorted(MODEL_TO_DEVICE)))
        sys.exit(1)
    print(f"Using registers for {device.name}")
    return device


# --- Detected at import time (main.py runs this before using ECS) ----------
DEVICE = None
ECS = None
MODEL = ""
CPU_TYPE = "Unknown"


def init():
    """Detect the machine; populates DEVICE / ECS / MODEL / CPU_TYPE globals."""
    global DEVICE, ECS, MODEL, CPU_TYPE
    MODEL = detect_model()
    CPU_TYPE = detect_cpu_type()
    DEVICE = detect_device()
    ECS = _ECSShim(DEVICE)
    print(f"CPU type: {CPU_TYPE}")
    return DEVICE
