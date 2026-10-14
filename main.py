import enum
import os
import signal
import sys

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPalette, QColor

from ui.frontend import Ui_PredatorSense
from core.ecwrite import ECWrite
import core.device_regs as device_regs
import utils.keyboard as keyboard

##------------------------------##
##-------Device Detection-------##
# ---------------------------------##
# Detect the running machine (DMI product name) and CPU vendor, then bind
# the ECS register shim to the matching register map. Exits if unsupported.
#
# Preview mode: `python3 main.py --preview "Nitro AN515-55"` renders the UI for
# another supported model without touching the real EC (a simulated register
# file is used instead, so it needs no root and cannot harm your machine).
PREVIEW_MODEL = None
if "--preview" in sys.argv:
    idx = sys.argv.index("--preview")
    if idx + 1 < len(sys.argv):
        PREVIEW_MODEL = sys.argv.pop(idx + 1)
    sys.argv.pop(idx)

if PREVIEW_MODEL:
    device_regs.MODEL = PREVIEW_MODEL
    device_regs.CPU_TYPE = "Intel"
    device = device_regs.MODEL_TO_DEVICE.get(PREVIEW_MODEL)
    if device is None:
        print(f"Model '{PREVIEW_MODEL}' is not supported!")
        print("Supported models: " + ", ".join(sorted(device_regs.MODEL_TO_DEVICE)))
        sys.exit(1)
    device_regs.DEVICE = device
    device_regs.ECS = device_regs._ECSShim(device)
    # Keyboard writes are printed instead of sent to /dev/acer-gkbbl-*, so the
    # tab can be previewed without reprogramming the real keyboard.
    keyboard.DRY_RUN = True
    print(f"[PREVIEW] Rendering UI for {device.name} (simulated EC, no hardware access)")
else:
    device_regs.init()

ECS = device_regs.ECS
DEVICE = device_regs.DEVICE
CPU_TYPE = device_regs.CPU_TYPE

if CPU_TYPE == "AMD":
    from core.amdctl import applyUndervolt, checkUndervoltStatus, checkVoltage
elif CPU_TYPE == "Intel":
    from core.intelctl import applyUndervolt, checkUndervoltStatus, checkVoltage
else:
    def checkUndervoltStatus(self):
        self.undervolt = "Undervolt not supported for this CPU type."

    def applyUndervolt(self, core, cache):
        self.undervolt = "Undervolt not supported for this CPU type."

    def checkVoltage(self):
        self.voltage = 0

CONFIG_FOLDER = "/etc/predatorsense/"
CONFIG_FILE = os.path.join(CONFIG_FOLDER, "predatorsense.conf")
RGB_CONFIG_FILE = os.path.join(CONFIG_FOLDER, "rgb.conf")
UPDATE_INTERVAL = 1000 #1 sec interval


def resource_path(relative):
    """Absolute path to a bundled resource, working both from source and from a
    PyInstaller one-file bundle (where files are unpacked into sys._MEIPASS)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


## Brand follows the detected/previewed device series, so the same binary presents
## itself as PredatorSense on Predator machines and NitroSense on Nitro machines.
BRAND = "NitroSense" if DEVICE.series == "Nitro" else "PredatorSense"
APP_TITLE = f"Linux {BRAND}"
APP_ICON = resource_path(os.path.join("assets", BRAND.lower() + ".ico"))

if PREVIEW_MODEL:
    # Never read/write the real config while previewing another model
    CONFIG_FOLDER = os.path.join(os.path.expanduser("~"), ".cache", "predatorsense-preview")
    CONFIG_FILE = os.path.join(CONFIG_FOLDER, "predatorsense.conf")
    RGB_CONFIG_FILE = os.path.join(CONFIG_FOLDER, "rgb.conf")
    # Don't shell out to undervolt (needs sudo) while previewing.
    # The redefinition of the CPU-specific functions above is intentional.
    def checkUndervoltStatus(self):  # noqa: F811
        self.undervolt = "[preview] undervolt status not queried"

    def applyUndervolt(self, core, cache):  # noqa: F811
        self.undervolt = "[preview] undervolt not applied"

##------------------------------##
##-------Predator Fan Mode------##
# ProcessorFanState
class PFS(enum.Enum):  
    Manual = 0
    Auto = 1
    Turbo = 2

##------------------------------##
##---- Simulated EC (preview) --##
# ---------------------------------##
# Backs --preview: a dict of registers seeded from the selected device's own
# constants, so the UI renders as it would on that machine without touching
# real hardware (no root needed, nothing can be mis-written).
class PreviewEC:
    def __init__(self):
        d = DEVICE          # capability flags live on the device class
        r = ECS             # register addresses come from the ECS shim
        self.mem = {
            int(r.GPU_FAN_MODE_CONTROL.value, 0): int(r.GPU_AUTO_MODE.value, 0),
            int(r.CPU_FAN_MODE_CONTROL.value, 0): int(r.CPU_AUTO_MODE.value, 0),
            int(r.KB_30_SEC_AUTO.value, 0): int(r.KB_30_AUTO_ON.value, 0),
            int(r.POWEROFFUSBCHARGING.value, 0): int(r.USBCHARGINGON.value, 0),
            int(r.MODE.value, 0): int(r.DEFAULTMODE.value, 0),
            int(r.BATTERYCHARGELIMIT.value, 0): int(r.BATTERYLIMITON.value, 0),
            int(r.POWERSTATUS.value, 0): int(r.POWERPLUGGEDIN.value, 0),
            int(r.BATTERYSTATUS.value, 0): int(r.BATTERYPLUGGEDINANDCHARGING.value, 0),
            int(r.CPUTEMP.value, 0): 54,
            int(r.GPUTEMP.value, 0): 61,
            int(r.SYSTEMP.value, 0): 47,
            int(r.CPUFANSPEEDHIGHBITS.value, 0): 0x50,
            int(r.CPUFANSPEEDLOWBITS.value, 0): 0x00,
            int(r.GPUFANSPEEDHIGHBITS.value, 0): 0x60,
            int(r.GPUFANSPEEDLOWBITS.value, 0): 0x00,
            int(r.CPU_MANUAL_SPEED_CONTROL.value, 0): 30,
            int(r.GPU_MANUAL_SPEED_CONTROL.value, 0): 30,
        }
        if d.has_turbo_led:
            self.mem[int(r.TURBO_LED_CONTROL.value, 0)] = int(r.TURBO_LED_OFF.value, 0)
        if d.has_trackpad_status:
            self.mem[int(r.TRACKPADSTATUS.value, 0)] = int(r.TRACKPADENABLED.value, 0)

    def ec_refresh(self):
        pass

    def ec_read(self, address):
        return self.mem.get(address, 0)

    def ec_write(self, address, value):
        self.mem[address] = value

    def shutdown_ec(self):
        print("[PREVIEW] simulated EC closed.")

##------------------------------##
##-------Main QT Window---------##
class MainWindow(QtWidgets.QDialog, Ui_PredatorSense):

    def __init__(self):
        super(MainWindow, self).__init__()
        self._initialize_variables()
        self.setupUI(self)
        self._initialize_ec_handler()
        self._initialize_ui()

        # Setup new timer to periodically read the EC regsiters and update UI
        self.setUpdateUITimer()

    ## ----------------------------------------------------
    def _initialize_variables(self):
        self.turboEnabled = False
        self.cpufanspeed = 0
        self.gpufanspeed = 0
        self.cpuTemp = 0
        self.gpuTemp = 0
        self.sysTemp = 0
        self.voltage = 0.5
        self.underVolt = ""
        self.minrecordedVoltage = 2.0 # V # Max operating voltage for Intel desktop 13th gen
        self.maxrecordedVoltage = 0 # V

        self.powerPluggedIn = False
        self.onBatteryPower = False
        self.displayOverdrive = False
        self.predatorMode = ECS.DEFAULTMODE.value
        self.usbCharging = ECS.USBCHARGINGON.value

        self.cpuMode = ECS.CPU_AUTO_MODE.value
        self.gpuMode = ECS.GPU_AUTO_MODE.value
        self.cpuFanMode = PFS.Auto
        self.gpuFanMode = PFS.Auto
        self.KB30Timeout = ECS.KB_30_AUTO_OFF.value
        self.trackpad = ECS.TRACKPADENABLED.value
        self.batteryChargeLimit = ECS.BATTERYLIMITOFF.value

        ## Capability flags consumed by setupUI (hides unsupported widgets on
        ## Nitro machines: no Turbo power mode, no LCD overdrive)
        self.has_turbo_mode = DEVICE.has_turbo_mode
        self.has_lcd_overdrive = DEVICE.has_lcd_overdrive

        ## Brand logo shown above the status row (original app drew
        ## PredatorLogo.png as a tab background). Nitro has no logo asset, so
        ## the label is simply omitted there.
        self.brand_logo = (resource_path(os.path.join("assets", "predator_logo.png"))
                           if DEVICE.series != "Nitro" else None)

        ## RGB keyboard support depends on the acer-gkbbl character devices
        ## being present; in preview mode DRY_RUN makes is_supported() return
        ## True so the tab can be inspected (writes are printed, not sent).
        self.selected_color = (255, 255, 255)
        self.keyboardSupported = keyboard.is_supported()

    ## ----------------------------------------------------
    def _initialize_ec_handler(self):
        self.ECHandler = PreviewEC() if PREVIEW_MODEL else ECWrite()
        self.ECHandler.ec_refresh()

    ## ----------------------------------------------------
    ## Undervolt offset chosen in the UI: index N == -N*20 mV
    def selectedOffset(self):
        # The offset combo is editable so values between the 20 mV presets can be
        # typed (e.g. "-85 mV"). Parse the text rather than the index, and clamp
        # to the 0..700 mV range the hardware allows.
        text = self.undervolt_dropdown.currentText().replace("mV", "").strip()
        try:
            mv = abs(int(text))
        except ValueError:
            mv = 0
        return min(mv, 700)

    def applySelectedUndervolt(self):
        offset = self.selectedOffset()
        applyUndervolt(self, offset, offset)

    def resetUndervolt(self):
        # Back to stock voltage in one click, and move the dropdown to 0 mV too
        # so the widget reflects the offset that is actually applied.
        self.undervolt_dropdown.setCurrentIndex(0)
        applyUndervolt(self, 0, 0)

    ## ----------------------------------------------------
    def _initialize_ui(self):
        ## Drop the keyboard tab entirely when the machine has no RGB device
        if not self.keyboardSupported:
            idx = self.fan_control_tab.indexOf(self.keyboard_tab)
            if idx != -1:
                self.fan_control_tab.removeTab(idx)

        ## Brand-aware status label
        self.predatorModeLabel.setText(
            "Nitro Mode:  " if DEVICE.series == "Nitro" else "Predator Mode:")

        checkUndervoltStatus(self)
        self.checkPowerTempFan()
        self.checkPredatorStatus()
        self.loadConfig()
        self.setupGUI()
        if self.keyboardSupported:
            self.kbLoadConfig()

    ## ----------------------------------------------------
    ## Initialise the frame, check all registers and set the appropriate widgets
    def setupGUI(self):
        # if self.cb:
        #     self.coolboost_checkbox.setChecked(True)
        # self.coolboost_checkbox.clicked['bool'].connect(self.toggleCB)

        self.global_auto.clicked.connect(lambda: self.saveAndRun(self.setDefaultMode))
        self.global_turbo.clicked.connect(lambda: self.saveAndRun(self.setTurboMode))

        self.cpu_auto.clicked.connect(lambda: self.saveAndRun(self.cpuauto))
        self.cpu_manual.clicked.connect(lambda: self.saveAndRun(self.cpusetmanual))
        self.cpu_turbo.clicked.connect(lambda: self.saveAndRun(self.cpumax))
        self.gpu_auto.clicked.connect(lambda: self.saveAndRun(self.gpuauto))
        self.gpu_manual.clicked.connect(lambda: self.saveAndRun(self.gpusetmanual))
        self.gpu_turbo.clicked.connect(lambda: self.saveAndRun(self.gpumax))
        self.cpuManualSlider.valueChanged.connect(self.cpumanual)
        self.gpuManualSlider.valueChanged.connect(self.gpumanual)
        self.exit_button.clicked.connect(self.shutdown)
        self.reset_button.clicked.connect(self.resetUndervolt)
        self.undervolt_button.clicked.connect(self.applySelectedUndervolt)

        if self.keyboardSupported:
            self.color_button.clicked.connect(lambda: self.saveAndRun(self.kbSelectColor))
            self.apply_button.clicked.connect(lambda: self.saveAndRun(self.kbApplySettings))
            self.save_button.clicked.connect(lambda: self.saveAndRun(self.kbSaveConfig))
            self.load_button.clicked.connect(lambda: self.saveAndRun(self.kbLoadConfig))

        ## ----------------------------------------------------

        ## We can toggle the register but it does not seem to actually disble the trackpad
        # if self.trackpad == int(TRACKPADENABLED, 0):
        #     self.trackpadCB.setChecked(False)
        # elif self.trackpad == int(TRACKPADDISABLED, 0):
        #     self.trackpadCB.setChecked(True)
        # else:
        #     print("Error read EC register for Trackpad: " + str(self.trackpad))
    
        ## Set the 30 sec backlight timer
        if self.KB30Timeout == int(ECS.KB_30_AUTO_OFF.value, 0):
            self.KBTimerCB.setChecked(False)
        else:
            self.KBTimerCB.setChecked(True)

        ## Set the LCD overdrive indicator (Predator only, bit 3 of 0x21)
        if DEVICE.has_lcd_overdrive:
            # Check if the lower 4 bits equals 8
            overdriveEnabled = self.displayOverdrive & (1 << 3)
            if overdriveEnabled == 0:
                self.LCDOverdriveCB.setChecked(False)
            else:
                self.LCDOverdriveCB.setChecked(True)

        ## Set the USB charging indicator
        if self.usbCharging == int(ECS.USBCHARGINGON.value, 0):
            self.usbChargingCB.setChecked(True)
        elif self.usbCharging == int(ECS.USBCHARGINGOFF.value, 0):
            self.usbChargingCB.setChecked(False)
        else:
            print("Error read EC register for USB Charging: " + str(self.usbCharging))

        ## Set the charge limit indicator
        if self.batteryChargeLimit == int(ECS.BATTERYLIMITON.value, 0):
            self.chargeLimit.setChecked(True)
            self.batteryChargeLimitValue.setText("On ")
        elif self.batteryChargeLimit == int(ECS.BATTERYLIMITOFF.value, 0):
            self.chargeLimit.setChecked(False)
            self.batteryChargeLimitValue.setText("Off")
        else:
            print("Error read EC register for Charge Limit: " + str(self.batteryChargeLimit))                   

        self.setPredatorMode()
        self.setFanMode()

        ## ----------------------------------------------------

        self.quietModeCB.clicked['bool'].connect(lambda tog: self.saveAndRun(self.setQuietMode))
        self.defaultModeCB.clicked['bool'].connect(lambda tog: self.saveAndRun(self.setDefaultMode))
        self.extremeModeCB.clicked['bool'].connect(lambda tog: self.saveAndRun(self.setExtremeMode))
        if DEVICE.has_turbo_mode:
            self.turboModeCB.clicked['bool'].connect(lambda tog: self.saveAndRun(self.setTurboMode))

        # self.trackpadCB.clicked['bool'].connect(self.toggletrackpad)
        self.KBTimerCB.clicked['bool'].connect(self.saveAndRunWrap(self.togglekbauto))
        if DEVICE.has_lcd_overdrive:
            self.LCDOverdriveCB.clicked['bool'].connect(self.saveAndRunWrap(self.toggleLCDOverdrive))
        self.usbChargingCB.clicked['bool'].connect(self.saveAndRunWrap(self.toggleUSBCharging))
        self.chargeLimit.clicked['bool'].connect(self.saveAndRunWrap(self.togglePowerLimit))

    # Set the current fan and turbo mode
    def setFanMode(self):
        if self.cpuMode == int(ECS.CPU_AUTO_MODE.value, 0):
            self.cpuFanMode = PFS.Auto
            self.cpu_auto.setChecked(True)
        elif self.cpuMode == int(ECS.CPU_TURBO_MODE.value, 0) or self.cpuMode == int('0xA8', 0):
            self.cpuFanMode = PFS.Turbo
            self.cpu_turbo.setChecked(True)
            self.turboEnabled = True
        elif self.cpuMode == int(ECS.CPU_MANUAL_MODE.value, 0):
            self.cpuFanMode = PFS.Manual
            self.cpu_manual.setChecked(True)
        else:
            print("Warning: Unknow CPU fan mode value '" + str(self.cpuMode) + "'")
            # self.cpuauto()
        
        # Mask off bits outside the fan mode. On Predator, register 0x21 is
        # shared with LCD overdrive (bit 3) so the mask is 0xF0; on Nitro the
        # whole byte is the fan mode (mask 0xFF).
        gpuFanModeBits = self.gpuMode & DEVICE.gpu_mode_mask
        if gpuFanModeBits == int(ECS.GPU_AUTO_MODE.value, 0) or gpuFanModeBits == int('0x00', 0):
            self.gpuFanMode = PFS.Auto
            self.gpu_auto.setChecked(True)
        elif gpuFanModeBits == int(ECS.GPU_TURBO_MODE.value, 0):
            self.gpuFanMode = PFS.Turbo
            self.gpu_turbo.setChecked(True)
        elif gpuFanModeBits == int(ECS.GPU_MANUAL_MODE.value, 0):
            self.gpuFanMode = PFS.Manual
            self.gpu_manual.setChecked(True)
        else:
            print("Warning: Unknow GPU fan mode value '" + str(self.gpuMode) + "'")
            # self.gpuauto()

        # if cpuTurboEnabled and gpuTurboEnabled:
        # The fan turbo state exists on every model; only Predator also has a
        # matching Turbo *power mode* register to re-assert.
        if self.turboEnabled:
            self.global_turbo.setChecked(True)
            self.cpu_turbo.setChecked(True)
            self.gpu_turbo.setChecked(True)
            if DEVICE.has_turbo_mode:
                self.predatorMode = int(ECS.TURBOMODE.value, 0)
                self.setTurboMode()

    # Create a timer to update the UI
    def setUpdateUITimer(self):
        print("Setting up callback timer for %d(ms)" % UPDATE_INTERVAL)
        self.my_timer = QTimer()
        self.my_timer.timeout.connect(self.updatePredatorStatus)
        self.my_timer.start(UPDATE_INTERVAL)

    ## ----------------------------------------------------
    ## Read the various EC registers and update the GUI
    def checkPredatorStatus(self):
        # self.cb = self.ECHandler.ec_read(int(COOL_BOOST_CONTROL, 0)) == 1
        self.cpuMode = self.ECHandler.ec_read(int(ECS.CPU_FAN_MODE_CONTROL.value, 0))
        self.gpuMode = self.ECHandler.ec_read(int(ECS.GPU_FAN_MODE_CONTROL.value, 0))
        self.KB30Timeout = self.ECHandler.ec_read(int(ECS.KB_30_SEC_AUTO.value, 0))
        self.usbCharging = self.ECHandler.ec_read(int(ECS.POWEROFFUSBCHARGING.value, 0))
        if DEVICE.has_lcd_overdrive:
            self.displayOverdrive = self.ECHandler.ec_read(int(ECS.LCDOVERDRIVE.value, 0))
        self.predatorMode = self.ECHandler.ec_read(int(ECS.MODE.value, 0))
        self.batteryChargeLimit = self.ECHandler.ec_read(int(ECS.BATTERYCHARGELIMIT.value, 0))
        if DEVICE.has_trackpad_status:
            self.trackpad = self.ECHandler.ec_read(int(ECS.TRACKPADSTATUS.value, 0))

        self.cpuFanSpeed = self.ECHandler.ec_read(int(ECS.CPU_MANUAL_SPEED_CONTROL.value, 0))
        self.gpuFanSpeed = self.ECHandler.ec_read(int(ECS.GPU_MANUAL_SPEED_CONTROL.value, 0))
        self.cpuManualSlider.setSliderPosition(int(self.cpuFanSpeed / 10))
        self.gpuManualSlider.setSliderPosition(int(self.gpuFanSpeed / 10))

    ## ----------------------------------------------------
    ## Read the newest register updates
    def checkPowerTempFan(self):
        ## Refresh the EC registers first before reading values
        # -optimisation, read EC registers once per update, prevents hangs/unresponsive GUI 
        self.ECHandler.ec_refresh()

        self.cpuMode = self.ECHandler.ec_read(int(ECS.CPU_FAN_MODE_CONTROL.value, 0))
        self.gpuMode = self.ECHandler.ec_read(int(ECS.GPU_FAN_MODE_CONTROL.value, 0))
        self.powerPluggedIn = self.ECHandler.ec_read(int(ECS.POWERSTATUS.value, 0))
        self.onBatteryPower = self.ECHandler.ec_read(int(ECS.BATTERYSTATUS.value, 0))
        self.predatorMode = self.ECHandler.ec_read(int(ECS.MODE.value, 0))
        self.batteryChargeLimit = self.ECHandler.ec_read(int(ECS.BATTERYCHARGELIMIT.value, 0))

        self.cpuTemp = self.ECHandler.ec_read(int(ECS.CPUTEMP.value, 0))
        self.gpuTemp = self.ECHandler.ec_read(int(ECS.GPUTEMP.value, 0))
        self.sysTemp = self.ECHandler.ec_read(int(ECS.SYSTEMP.value, 0))

        cpufanspeedHighBits = self.ECHandler.ec_read(int(ECS.CPUFANSPEEDHIGHBITS.value, 0))
        cpufanspeedLowBits = self.ECHandler.ec_read(int(ECS.CPUFANSPEEDLOWBITS.value, 0))
        ## example
        # cpufanspeed = '0x068B'
        # 1675
        self.cpufanspeed = cpufanspeedLowBits << 8 | cpufanspeedHighBits

        gpufanspeedHighBits = self.ECHandler.ec_read(int(ECS.GPUFANSPEEDHIGHBITS.value, 0))
        gpufanspeedLowBits = self.ECHandler.ec_read(int(ECS.GPUFANSPEEDLOWBITS.value, 0))
        self.gpufanspeed = gpufanspeedLowBits << 8 | gpufanspeedHighBits
        # print("cpufanspeed: " + str(cpufanspeed))
        # print("gpufanspeed: " + gpufanspeed)

    ## ---------Radio Button callback functions------------
    def setQuietMode(self):
        self.ECHandler.ec_write(int(ECS.MODE.value, 0), int(ECS.QUIETMODE.value, 0))
        self.setGlobalAuto()

    def setDefaultMode(self):
        self.ECHandler.ec_write(int(ECS.MODE.value, 0), int(ECS.DEFAULTMODE.value, 0))
        self.setGlobalAuto() 

    def setExtremeMode(self):
        self.ECHandler.ec_write(int(ECS.MODE.value, 0), int(ECS.EXTREMEMODE.value, 0))
        self.setGlobalAuto()

    def setTurboMode(self):
        if DEVICE.has_turbo_mode:
            self.ECHandler.ec_write(int(ECS.MODE.value, 0), int(ECS.TURBOMODE.value, 0))
        self.setGlobalTurbo()

    def setGlobalAuto(self):
        if self.turboEnabled:
            self.turboEnabled = False

            self.cpuauto()
            self.gpuauto()

            self.global_auto.setChecked(True)
            self.cpu_auto.setChecked(True)
            self.gpu_auto.setChecked(True)

    def setGlobalTurbo(self):
        if not self.turboEnabled:        
            self.turboEnabled = True

            self.cpumax()
            self.gpumax()

            self.global_turbo.setChecked(True)
            self.cpu_turbo.setChecked(True)
            self.gpu_turbo.setChecked(True)

    def cpuauto(self):
        self.ECHandler.ec_write(int(ECS.CPU_FAN_MODE_CONTROL.value, 0), int(ECS.CPU_AUTO_MODE.value, 0))
        self.cpuFanMode = PFS.Auto
        self.ledset()

    def cpumax(self):
        self.ECHandler.ec_write(int(ECS.CPU_FAN_MODE_CONTROL.value, 0), int(ECS.CPU_TURBO_MODE.value, 0))
        self.cpuFanMode = PFS.Turbo
        self.ledset()

    def cpusetmanual(self):
        self.ECHandler.ec_write(int(ECS.CPU_FAN_MODE_CONTROL.value, 0), int(ECS.CPU_MANUAL_MODE.value, 0))
        self.cpuFanMode = PFS.Manual

    def cpumanual(self, level):
        # print(str(level * 10), end=', ')
        # print(hex(level * 10))
        self.ECHandler.ec_write(int(ECS.CPU_MANUAL_SPEED_CONTROL.value, 0), level * 10)        

    def gpuauto(self):
        self.ECHandler.ec_write(int(ECS.GPU_FAN_MODE_CONTROL.value, 0), int(ECS.GPU_AUTO_MODE.value, 0))
        self.gpuFanMode = PFS.Auto

    def gpumax(self):
        self.ECHandler.ec_write(int(ECS.GPU_FAN_MODE_CONTROL.value, 0), int(ECS.GPU_TURBO_MODE.value, 0))
        self.gpuFanMode = PFS.Turbo

    def gpusetmanual(self):
        self.ECHandler.ec_write(int(ECS.GPU_FAN_MODE_CONTROL.value, 0), int(ECS.GPU_MANUAL_MODE.value, 0))
        self.gpuFanMode = PFS.Manual        

    def gpumanual(self, level):
        # print(level * 10, end=', ')
        # print(hex(level * 10))
        self.ECHandler.ec_write(int(ECS.GPU_MANUAL_SPEED_CONTROL.value, 0), level * 10)

    ## Toggle coolboost register
    # def toggleCB(self, tog):
    #     print('CoolBoost Toggle: ', end='')
    #     if tog:
    #         print('On')
    #         self.ECHandler.ec_write(int(COOL_BOOST_CONTROL, 0), int(COOL_BOOST_ON, 0))
    #     else:
    #         print('Off')
    #         self.ECHandler.ec_write(int(COOL_BOOST_CONTROL, 0), int(COOL_BOOST_OFF, 0))

    # Toggle 30 seconds keyboard backlight timer
    def togglekbauto(self, tog):
        if not tog:
            self.ECHandler.ec_write(int(ECS.KB_30_SEC_AUTO.value, 0), int(ECS.KB_30_AUTO_OFF.value, 0))
        else:
            self.ECHandler.ec_write(int(ECS.KB_30_SEC_AUTO.value, 0), int(ECS.KB_30_AUTO_ON.value, 0))

    # Toggle LCD Overdrive
    # Register 0x21 is shared: upper nibble = GPU fan mode, bit 3 = LCD overdrive.
    # Always re-read and use bitwise set/clear so the fan-mode nibble is never touched.
    def toggleLCDOverdrive(self, tog):
        self.displayOverdrive = self.ECHandler.ec_read(int(ECS.LCDOVERDRIVE.value, 0))
        if tog:
            self.displayOverdrive = self.displayOverdrive | (1 << 3)
        else:
            self.displayOverdrive = self.displayOverdrive & ~(1 << 3)
        self.ECHandler.ec_write(int(ECS.LCDOVERDRIVE.value, 0), self.displayOverdrive)
    
    # USB charging whilst off
    def toggleUSBCharging(self, tog):
        if tog:
            self.ECHandler.ec_write(int(ECS.POWEROFFUSBCHARGING.value, 0), int(ECS.USBCHARGINGON.value, 0))
        else:
            self.ECHandler.ec_write(int(ECS.POWEROFFUSBCHARGING.value, 0), int(ECS.USBCHARGINGOFF.value, 0))

    ## We can toggle the register but it does nothing to actually disble the trackpad
    # def toggletrackpad(self, tog):
    #     if not tog:
    #         self.ECHandler.ec_write(int(ECS.TRACKPADSTATUS.value, 0), int(ECS.TRACKPADENABLED.value, 0))
    #     else:
    #         self.ECHandler.ec_write(int(ECS.TRACKPADSTATUS.value, 0), int(ECS.TRACKPADDISABLED.value, 0))

    # Toggle Power Limit
    def togglePowerLimit(self, tog):
        if tog:
            self.ECHandler.ec_write(int(ECS.BATTERYCHARGELIMIT.value, 0), int(ECS.BATTERYLIMITON.value, 0))
        else:
            self.ECHandler.ec_write(int(ECS.BATTERYCHARGELIMIT.value, 0), int(ECS.BATTERYLIMITOFF.value, 0))

    ## ----------------------------------------------------
    # Toggle the Turbo Led (only on devices that have one)
    def ledset(self):
        if not DEVICE.has_turbo_led:
            return
        turboLedEnabled = self.ECHandler.ec_read(int(ECS.TURBO_LED_CONTROL.value, 0)) == int(ECS.TURBO_LED_ON.value, 0)
        if self.turboEnabled:
            if not turboLedEnabled:
                self.ECHandler.ec_write(int(ECS.TURBO_LED_CONTROL.value, 0), int(ECS.TURBO_LED_ON.value, 0))     
        else:
            if turboLedEnabled:
                self.ECHandler.ec_write(int(ECS.TURBO_LED_CONTROL.value, 0), int(ECS.TURBO_LED_OFF.value, 0))         

    # Update the Battery status
    def setBatteryStatus(self):
        batteryStat = 'Discharging'
        if self.onBatteryPower == int(ECS.BATTERYPLUGGEDINANDCHARGING.value, 0):
            batteryStat = "Charging"
        elif self.onBatteryPower == int(ECS.BATTERYDRAINING.value, 0):
            batteryStat = "Discharging"
        elif self.onBatteryPower == int(ECS.BATTERYOFF.value, 0):
            batteryStat = "Battery Not In Use"
        else:
            print("Error read EC register for Battery Status: " + str(hex(self.onBatteryPower)))

        self.batteryStatusValue.setText(batteryStat)

        ## Set the battery charge indicator
        if self.batteryChargeLimit == int(ECS.BATTERYLIMITON.value, 0):
            self.batteryChargeLimitValue.setText("On")
        elif self.batteryChargeLimit == int(ECS.BATTERYLIMITOFF.value, 0):
            self.batteryChargeLimitValue.setText("Off")

    # Update the Predator state
    def setPredatorMode(self):
        # print("predatorModeValue: " + str(self.predatorMode))
        if self.predatorMode == int(ECS.QUIETMODE.value, 0):
            self.predatorModeValue.setText("Quiet\t")
            self.quietModeCB.setChecked(True)
        elif self.predatorMode == int(ECS.DEFAULTMODE.value, 0):
            self.predatorModeValue.setText("Default\t")
            self.defaultModeCB.setChecked(True)
        elif self.predatorMode == int(ECS.EXTREMEMODE.value, 0):
            self.predatorModeValue.setText("Extreme\t")
            self.extremeModeCB.setChecked(True)
        elif DEVICE.has_turbo_mode and self.predatorMode == int(ECS.TURBOMODE.value, 0):
            self.predatorModeValue.setText("Turbo\t")
            self.turboModeCB.setChecked(True)
        else:
            print("Error read EC register for Predator Mode: " + str(self.predatorMode))

        # self.predatorModeValue.adjustSize()

    ## ----------------------------------------------------
    ## Config persistence: remember fan/mode/toggle settings across restarts
    def saveConfig(self):
        try:
            os.makedirs(CONFIG_FOLDER, exist_ok=True)
            with open(CONFIG_FILE, "w") as f:
                f.write(f"{self.cpuMode}\n")
                f.write(f"{self.gpuMode}\n")
                f.write(f"{self.KB30Timeout}\n")
                f.write(f"{self.usbCharging}\n")
                f.write(f"{self.predatorMode}\n")
                f.write(f"{self.batteryChargeLimit}\n")
                f.write(f"{self.displayOverdrive}\n")
        except OSError as e:
            print("Could not save config: " + str(e))

    def loadConfig(self):
        if not os.path.exists(CONFIG_FILE):
            return
        try:
            with open(CONFIG_FILE) as f:
                lines = f.read().split()
            if len(lines) < 6:
                print("Config file is malformed, ignoring.")
                return
            self.cpuMode = int(lines[0])
            self.gpuMode = int(lines[1])
            self.KB30Timeout = int(lines[2])
            self.usbCharging = int(lines[3])
            self.predatorMode = int(lines[4])
            self.batteryChargeLimit = int(lines[5])
            if len(lines) >= 7 and DEVICE.has_lcd_overdrive:
                self.displayOverdrive = int(lines[6])
        except (OSError, ValueError) as e:
            print("Could not load config: " + str(e))
            return

        ## Re-apply the saved settings to the EC
        self.ECHandler.ec_write(int(ECS.CPU_FAN_MODE_CONTROL.value, 0), self.cpuMode)
        self.ECHandler.ec_write(int(ECS.GPU_FAN_MODE_CONTROL.value, 0), self.gpuMode)
        self.ECHandler.ec_write(int(ECS.KB_30_SEC_AUTO.value, 0), self.KB30Timeout)
        self.ECHandler.ec_write(int(ECS.POWEROFFUSBCHARGING.value, 0), self.usbCharging)
        self.ECHandler.ec_write(int(ECS.MODE.value, 0), self.predatorMode)
        self.ECHandler.ec_write(int(ECS.BATTERYCHARGELIMIT.value, 0), self.batteryChargeLimit)
        if DEVICE.has_lcd_overdrive:
            self.ECHandler.ec_write(int(ECS.LCDOVERDRIVE.value, 0), self.displayOverdrive)
        self.ECHandler.ec_refresh()

    ## ----------------------------------------------------
    ## RGB keyboard (acer-gkbbl) handlers
    def kbSelectColor(self):
        if not self.keyboardSupported:
            return
        color = QtWidgets.QColorDialog.getColor(
            initial=QtGui.QColor.fromRgb(*self.selected_color))
        if color.isValid():
            self.selected_color = (color.red(), color.green(), color.blue())

    def kbApplySettings(self):
        if not self.keyboardSupported:
            return
        mode = self.mode_combo.currentIndex()
        zone = self.zone_combo.currentIndex()
        speed = self.speed_spin.value()
        brightness = self.brightness_spin.value()
        direction = self.direction_combo.currentIndex() + 1
        red, green, blue = self.selected_color
        try:
            keyboard.set_mode(mode, zone, speed, brightness, direction, red, green, blue)
        except OSError as e:
            print("Could not write keyboard settings: " + str(e))

    def kbSaveConfig(self):
        if not self.keyboardSupported:
            return
        try:
            os.makedirs(CONFIG_FOLDER, exist_ok=True)
            with open(RGB_CONFIG_FILE, "w") as f:
                f.write(f"{self.mode_combo.currentIndex()}\n")
                f.write(f"{self.zone_combo.currentIndex()}\n")
                f.write(f"{self.speed_spin.value()}\n")
                f.write(f"{self.brightness_spin.value()}\n")
                f.write(f"{self.direction_combo.currentIndex()}\n")
                f.write(f"{self.selected_color[0]}\n")
                f.write(f"{self.selected_color[1]}\n")
                f.write(f"{self.selected_color[2]}\n")
        except OSError as e:
            print("Could not save rgb config: " + str(e))

    def kbLoadConfig(self):
        if not self.keyboardSupported or not os.path.exists(RGB_CONFIG_FILE):
            return
        try:
            with open(RGB_CONFIG_FILE) as f:
                lines = f.read().split()
            if len(lines) < 8:
                print("RGB config file is malformed, ignoring.")
                return
            self.mode_combo.setCurrentIndex(int(lines[0]))
            self.zone_combo.setCurrentIndex(int(lines[1]))
            self.speed_spin.setValue(int(lines[2]))
            self.brightness_spin.setValue(int(lines[3]))
            self.direction_combo.setCurrentIndex(int(lines[4]))
            self.selected_color = (int(lines[5]), int(lines[6]), int(lines[7]))
        except (OSError, ValueError) as e:
            print("Could not load rgb config: " + str(e))
            return
        self.kbApplySettings()

    def saveAndRun(self, function):
        function()
        self.saveState()

    def saveAndRunWrap(self, function):
        """Wrap a bool-taking checkbox handler so it also saves the config."""
        def wrapper(tog):
            function(tog)
            self.saveState()
        return wrapper

    def saveState(self):
        # Re-read the EC first so the saved values reflect the writes that
        # were just made (self.* are otherwise one toggle behind).
        self.ECHandler.ec_refresh()
        self.checkPredatorStatus()
        self.saveConfig()

    # Update the UI state
    def updatePredatorStatus(self):
        checkVoltage(self)
        # print(self.voltage)
        minmaxVoltages = str("%1.2f" % self.minrecordedVoltage) + " / " + str("%1.2f" % self.maxrecordedVoltage)
        # print(minmaxVoltages)
        self.voltageValue.setText(str("%1.2f" % self.voltage))
        self.voltageMinMaxValue.setText(minmaxVoltages)

        self.undervoltStatus.setText(self.undervolt)

        self.checkPowerTempFan()

        # print(self.cpuMode)
        # print(self.gpuMode)
        # print(int(ECS.CPU_TURBO_MODE.value, 0))
        # print(int(ECS.GPU_TURBO_MODE.value, 0))
        # print("-----------")

        # Mask off bits outside the fan mode (see setFanMode)
        gpuFanModeBits = self.gpuMode & DEVICE.gpu_mode_mask
        cpuTurbo = (self.cpuMode == int(ECS.CPU_TURBO_MODE.value, 0)
                    or self.cpuMode == int('0xA8', 0))
        if cpuTurbo and gpuFanModeBits == int(ECS.GPU_TURBO_MODE.value, 0):
            if not self.turboEnabled:
                print("Turbo enabled")
                self.setTurboMode()

        if self.cpuMode == int(ECS.CPU_AUTO_MODE.value, 0) and gpuFanModeBits == int(ECS.GPU_AUTO_MODE.value, 0):
            if self.turboEnabled:
                print("Turbo disabled")
                self.setDefaultMode()
           
        self.setBatteryStatus()
        self.setPredatorMode()

        self.voltageChart.update_data(float("%1.2f" %  self.voltage))
        self.cpuChart.update_data(self.cpuTemp)
        self.gpuChart.update_data(self.gpuTemp)
        self.sysChart.update_data(self.sysTemp)
        self.cpuFanChart.update_data(self.cpufanspeed)
        self.gpuFanChart.update_data(self.gpufanspeed)

        # print("Sensors: %s, %s, %s, %s, %s, %s, %s" % (str(self.cpufanspeed), str(self.gpufanspeed), 
        #     str(self.cpuTemp), str(self.gpuTemp), str(self.sysTemp), str(self.powerPluggedIn), str(batteryStat)))

        self.cpuFanSpeedValue.setText(str(self.cpufanspeed) + " RPM")
        self.gpuFanSpeedValue.setText(str(self.gpufanspeed) + " RPM")
        self.cpuTempValue.setText(str(self.cpuTemp) + "°")
        self.gpuTempValue.setText(str(self.gpuTemp) + "°")
        self.sysTempValue.setText(str(self.sysTemp) + "°")

        self.powerStatusValue.setText(str(self.powerPluggedIn))

        # self.updateUI(Ui_PredatorSense, str(self.cpufanspeed), str(self.gpufanspeed),
        #     str(self.cpuTemp), str(self.gpuTemp), str(self.sysTemp), str(self.powerPluggedIn), str(batteryStat))        

    ## ----------------------------------------------------
    # Exit the program cleanly
    def shutdown(self):
        print("Cleaning up..")
        self.ECHandler.shutdown_ec()
        print("Exiting")
        ## Hard exit: this runs from a Qt signal handler (button click / SIGINT),
        ## so raising SystemExit via sys.exit() would propagate through a C++
        ## frame and abort(). Bare exit() is only defined by the site module,
        ## which a PyInstaller bundle does not load (NameError in the binary).
        ## The EC handle is already closed above, so nothing to flush.
        os._exit(0)

app = QtWidgets.QApplication(sys.argv)

## Pin the default application font so the UI renders identically regardless of
## how the app is launched. sudo inherits the GNOME font (Ubuntu Sans 11) while
## pkexec gets a clean environment where Qt falls back to Sans Serif 9; the
## fixed-pixel layout was designed around the 9pt fallback.
app.setFont(QtGui.QFont("Sans Serif", 9))

## Load the bundled TT Squares font so rendering does not depend on system/user
## font installation (works under sudo, .desktop, PyInstaller). Only Regular is
## loaded so the CLI launch matches the .desktop launch (which only had Regular
## installed in ~/.local/share/fonts); requesting Light/Thin weights would
## otherwise render the UI noticeably thinner.
_fonts_dir = resource_path("fonts")
_font_file = os.path.join(_fonts_dir, "Squares Regular.otf")
if os.path.exists(_font_file):
    QtGui.QFontDatabase.addApplicationFont(_font_file)

application = MainWindow()

## Graceful shutdown on Ctrl-C: close the EC file handle before exiting.
signal.signal(signal.SIGINT, lambda signum, frame: application.shutdown())

app.setApplicationName(APP_TITLE)
application.setWindowTitle(APP_TITLE)
application.resize(application.WIDTH, application.HEIGHT)  # resizable: layouts adapt
if os.path.exists(APP_ICON):
    application.setWindowIcon(QtGui.QIcon(APP_ICON))
## Set global window opacity
# application.setWindowOpacity(0.97)

app.setStyle('Breeze')
# Dark theme implementation
palette = QPalette()
palette.setColor(QPalette.Window, QColor(53, 53, 53))
palette.setColor(QPalette.WindowText, Qt.white)
palette.setColor(QPalette.Base, QColor(25, 25, 25))
palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
palette.setColor(QPalette.ToolTipBase, Qt.black)
palette.setColor(QPalette.ToolTipText, Qt.white)
palette.setColor(QPalette.Text, Qt.white)
palette.setColor(QPalette.Button, QColor(53, 53, 53))
palette.setColor(QPalette.ButtonText, Qt.white)
palette.setColor(QPalette.BrightText, Qt.red)
palette.setColor(QPalette.Link, QColor(42, 130, 218))
palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
palette.setColor(QPalette.HighlightedText, Qt.black)
app.setPalette(palette)

application.show()

## --dump (used with --preview): print the capability-relevant widget state and exit
if "--dump" in sys.argv:
    print("--- preview widget state ---")
    print("window title      :", application.windowTitle())
    print("Turbo mode radio  :", "visible" if application.turboModeCB.isVisible() else "HIDDEN")
    print("Global turbo radio:", "visible" if application.global_turbo.isVisible() else "HIDDEN")
    print("LCD Overdrive CB  :", "visible" if application.LCDOverdriveCB.isVisible() else "HIDDEN")
    print("predatorModeValue :", application.predatorModeValue.text().strip())
    print("cpuFanMode        :", application.cpuFanMode.name)
    print("gpuFanMode        :", application.gpuFanMode.name)
    print("chargeLimit       :", application.batteryChargeLimitValue.text().strip())
    app.processEvents()
    application.ECHandler.shutdown_ec()
    sys.exit(0)

app.exec()
sys.exit()
