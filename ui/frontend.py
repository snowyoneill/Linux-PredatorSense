# -*- coding: utf-8 -*-
import os

# Layout-based UI (no absolute geometry) so the window resizes and adapts to
# the font/DPI of whatever machine it runs on. Widget names are unchanged from
# the original pyuic5-generated frontend, so main.py keeps working as-is.

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtChart import QChart, QLineSeries, QAreaSeries, QChartView
from PyQt5.QtCore import Qt

stylesheet = '''
QWidget #tab, #monitoring_tab, #keyboard_tab {
    background-color: #252525;
}
QGroupBox {
    color: blue;
    font: bold;
    border: 1px solid silver;
    border-radius: 6px;
    margin-top: 6px;
}

QGroupBox#monitoring_box {
    border: 0px dotted gray;
    margin: 0 0 0 0;
}

QGroupBox #powerStatusLabel, #batteryStatusLabel, #batteryChargeLimitLabel, 
#predatorModeLabel, #cpuTempLabel, #gpuTempLabel, #sysTempLabel, #cpuFanSpeedLabel, 
#gpuFanSpeedLabel, #voltageLabel, #voltageMinMaxLabel, #voltageAverageLabel {
    color: gray;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top center;
    color: white;
}
'''

class CustomChart:
    def __init__(
        self,
        title="Voltage Chart",
        objectName="cusChart",
        sample_count=64,
        area_series_color="#80FF0000",
        line_series_color="#E74C3C",
        axis_x_label="Samples",
        axis_y_label="Voltage",
        axis_x_range=(0, 64),
        axis_y_range=(0.5, 1.2),
        **chart_kwargs,
    ):
        self.samples = [0.0] * sample_count
        self.sample_count = sample_count
        self.axis_y_range = axis_y_range

        # Create chart elements
        self.chart = QChart()
        self.chartView = QChartView(self.chart)
        self.upperSeries = QLineSeries()
        self.lowerSeries = QLineSeries()
        self.areaSeries = QAreaSeries(self.upperSeries, self.lowerSeries)
        self.lineSeries = QLineSeries()
        self.lineSeriesShadow = QLineSeries()

        # Add series to chart
        self.chart.addSeries(self.areaSeries)
        self.chart.addSeries(self.lineSeries)
        self.chart.addSeries(self.lineSeriesShadow)

        # Customize chart appearance
        self.chart.setTheme(QChart.ChartThemeDark)
        self.chart.setBackgroundRoundness(0)
        self.chart.legend().hide()
        self.chart.createDefaultAxes()
        self.chart.setMargins(QtCore.QMargins(0, 0, 0, 0))
        self.chart.layout().setContentsMargins(0, 0, 0, 0)
        self.chart.setTitle(title)
        self.chart.setTitleFont(QtGui.QFont("Arial", 8))

        ## Set series pen and brush colors
        self.areaSeries.setBrush(QtGui.QColor(area_series_color))

        pen = self.lineSeries.pen()
        pen.setBrush(QtGui.QColor(line_series_color))
        pen.setStyle(Qt.PenStyle.DotLine)
        self.lineSeries.setPen(pen)

        # Set axis labels and ranges
        axis_x = self.chart.axes(QtCore.Qt.Horizontal)[0]
        axis_x.setTitleText(axis_x_label)
        axis_x.setRange(*axis_x_range)
        axis_x.setLabelsFont(QtGui.QFont("Arial", 6))
        axis_x.setTickCount(int(sample_count / 4))
        axis_x.setLabelFormat("%d")

        axis_y = self.chart.axes(QtCore.Qt.Vertical)[0]
        axis_y.setTitleText(axis_y_label)
        axis_y.setRange(*axis_y_range)
        axis_y.setLabelsFont(QtGui.QFont("Arial", 6))
        axis_y.setTickCount(5) # Set how many tick lines you want to see

        self.chartView.setObjectName(objectName)
        self.chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        self.lineSeriesShadow.setPointLabelsVisible(True)
        self.lineSeriesShadow.setPointLabelsClipping(False)
        self.lineSeriesShadow.setPointLabelsFormat("@yPoint")

        # Apply additional chart customizations
        for key, value in chart_kwargs.items():
            setattr(self.chart, key, value)

    def update_data(self, sample):
        if len(self.samples) >= self.sample_count-1:
            self.samples.pop(0)
        self.samples.append(sample)

        self.upperSeries.clear()
        self.lowerSeries.clear()
        for i, value in enumerate(self.samples):
            self.upperSeries.append(i, value)
            self.lowerSeries.append(i, 0)

        ## HACK - to prevent chart redraw from clipping labels.
        #         Add 1 additional sample point to the end of the list whos y axis value 
        #         is greater than the max chart range. This enables the repaint to not 
        #         clip series labels whos y value > y max. The 1.2 part will help prevent labels 
        #         being cut off when graphs reach the max y range.
        self.upperSeries.append(i+1, self.axis_y_range[1]*1.2)
        self.lowerSeries.append(i+1, 0)

        self.lineSeries.clear()
        self.lineSeries.append(0, sample)
        self.lineSeries.append(self.sample_count - 1, sample)

        self.lineSeriesShadow.clear()
        self.lineSeriesShadow.append(20, sample)


class Ui_PredatorSense(object):

    # Used as the initial size hint; the window itself is resizable.
    WIDTH = 520
    HEIGHT = 720

    def setupUI(self, PredatorSense):

        ## Create window
        PredatorSense.setObjectName("PredatorSense")
        PredatorSense.setWindowTitle("Predator Sense™")
        PredatorSense.setWindowModality(QtCore.Qt.NonModal)
        PredatorSense.resize(self.WIDTH, self.HEIGHT)
        # The Temps / Fan RPM boxes center their value across the full box
        # width while the label stays pinned left, so shrinking a box below the
        # design width would slide the value under the label. Keep the window
        # at least as large as the design size (it can still grow).
        PredatorSense.setMinimumSize(self.WIDTH, self.HEIGHT)

        font = QtGui.QFont()
        font.setFamily("TT Squares")
        font.setWeight(QtGui.QFont.Light)

        boldfont = QtGui.QFont()
        boldfont.setFamily("DejaVu Sans")
        boldfont.setWeight(QtGui.QFont.Black)

        ## Root layout: the tab widget fills the dialog and resizes with it.
        self.rootLayout = QtWidgets.QVBoxLayout(PredatorSense)
        self.rootLayout.setContentsMargins(6, 6, 6, 6)

        self.fan_control_tab = QtWidgets.QTabWidget(PredatorSense)
        self.fan_control_tab.setAccessibleName("Predator Sense")
        self.fan_control_tab.setObjectName("tabWidget")
        self.rootLayout.addWidget(self.fan_control_tab)

        self.tab = QtWidgets.QWidget(PredatorSense)
        self.tab.setObjectName("tab")
        self.monitoring_tab = QtWidgets.QWidget(PredatorSense)
        self.monitoring_tab.setObjectName("monitoring_tab")
        self.keyboard_tab = QtWidgets.QWidget(PredatorSense)
        self.keyboard_tab.setObjectName("keyboard_tab")

        self.fan_control_tab.addTab(self.tab, "Home")
        self.fan_control_tab.addTab(self.monitoring_tab, "Monitoring")
        self.fan_control_tab.addTab(self.keyboard_tab, "Keyboard")

        self.tab.setStyleSheet(stylesheet)
        self.monitoring_tab.setStyleSheet(stylesheet)
        self.keyboard_tab.setStyleSheet(stylesheet)

        ##================ HOME TAB (grid layout) ================##

        self.homeLayout = QtWidgets.QGridLayout(self.tab)
        self.homeLayout.setContentsMargins(8, 8, 8, 8)
        self.homeLayout.setSpacing(8)
        # Equal stretch so the three columns share surplus width evenly.
        # Without this the CPU Fan column absorbs the extra width while GPU Fan
        # stays at its size hint, so resizing makes the two fan boxes diverge.
        for col in range(3):
            self.homeLayout.setColumnStretch(col, 1)

        ##------------Brand logo-------------##
        # The original app painted PredatorLogo.png as a tab background image;
        # a centered label keeps it inside the layout instead. Nitro machines
        # get no logo (main.py leaves brand_logo as None).
        logo_path = getattr(self, "brand_logo", None)
        if logo_path and os.path.exists(logo_path):
            self.brandLogo = QtWidgets.QLabel(self.tab)
            self.brandLogo.setObjectName("brandLogo")
            self.brandLogo.setPixmap(QtGui.QPixmap(logo_path))
            self.homeLayout.addWidget(self.brandLogo, 0, 0, 1, 3, Qt.AlignHCenter)

        ##------------Status-------------##

        self.status_box = QtWidgets.QGroupBox(self.tab)
        self.status_box.setFont(boldfont)
        self.status_box.setObjectName("status_box")
        statusForm = QtWidgets.QFormLayout(self.status_box)
        statusForm.setContentsMargins(10, 10, 10, 6)

        self.powerStatusLabel = QtWidgets.QLabel(self.status_box)
        self.powerStatusLabel.setObjectName("powerStatusLabel")
        self.powerStatusLabel.setText("Power Status  :")
        self.powerStatusValue = QtWidgets.QLabel(self.status_box)
        self.powerStatusValue.setObjectName("powerStatusValue")

        self.batteryStatusLabel = QtWidgets.QLabel(self.status_box)
        self.batteryStatusLabel.setObjectName("batteryStatusLabel")
        self.batteryStatusLabel.setText("Battery Status:")
        self.batteryStatusValue = QtWidgets.QLabel(self.status_box)
        self.batteryStatusValue.setObjectName("batteryStatusValue")

        self.batteryChargeLimitLabel = QtWidgets.QLabel(self.status_box)
        self.batteryChargeLimitLabel.setObjectName("batteryChargeLimitLabel")
        self.batteryChargeLimitLabel.setText("Charge Limit   :")
        self.batteryChargeLimitValue = QtWidgets.QLabel(self.status_box)
        self.batteryChargeLimitValue.setObjectName("batteryChargeLimitValue")

        self.predatorModeLabel = QtWidgets.QLabel(self.status_box)
        self.predatorModeLabel.setObjectName("predatorModeLabel")
        self.predatorModeLabel.setText("Predator Mode:")
        self.predatorModeValue = QtWidgets.QLabel(self.status_box)
        self.predatorModeValue.setObjectName("predatorModeValue")
        self.predatorModeValue.setText("Extreme")

        statusForm.addRow(self.powerStatusLabel, self.powerStatusValue)
        statusForm.addRow(self.batteryStatusLabel, self.batteryStatusValue)
        statusForm.addRow(self.batteryChargeLimitLabel, self.batteryChargeLimitValue)
        statusForm.addRow(self.predatorModeLabel, self.predatorModeValue)

        self.powerStatusLabel.setFont(boldfont)
        self.batteryStatusLabel.setFont(boldfont)
        self.batteryChargeLimitLabel.setFont(boldfont)
        self.predatorModeLabel.setFont(boldfont)

        self.powerStatusValue.setFont(font)
        self.batteryStatusValue.setFont(font)
        self.batteryChargeLimitValue.setFont(font)
        self.predatorModeValue.setFont(font)

        ##---------Predator Mode---------##

        self.predMode = QtWidgets.QGroupBox(self.tab)
        self.predMode.setFont(boldfont)
        self.predMode.setObjectName("predMode")
        predModeLayout = QtWidgets.QVBoxLayout(self.predMode)
        predModeLayout.setContentsMargins(10, 6, 10, 6)
        predModeLayout.setSpacing(1)

        self.quietModeCB = QtWidgets.QRadioButton(self.predMode)
        self.quietModeCB.setFont(font)
        self.quietModeCB.setObjectName("quietModeCB")
        self.defaultModeCB = QtWidgets.QRadioButton(self.predMode)
        self.defaultModeCB.setFont(font)
        self.defaultModeCB.setObjectName("defaultModeCB")
        self.extremeModeCB = QtWidgets.QRadioButton(self.predMode)
        self.extremeModeCB.setFont(font)
        self.extremeModeCB.setObjectName("extremeModeCB")
        self.turboModeCB = QtWidgets.QRadioButton(self.predMode)
        self.turboModeCB.setFont(font)
        self.turboModeCB.setObjectName("turboModeCB")

        for widget in (self.quietModeCB, self.defaultModeCB,
                       self.extremeModeCB, self.turboModeCB):
            # Breeze gives each radio a ~24px size hint; cap it so the rows
            # sit tighter and leave more height for the Undervolt box.
            widget.setFixedHeight(20)
            predModeLayout.addWidget(widget)
        predModeLayout.addStretch()

        self.homeLayout.addWidget(self.status_box, 1, 0, 1, 2)
        self.homeLayout.addWidget(self.predMode, 1, 2)

        ##--------Temperatures----------##

        self.temp_box = QtWidgets.QGroupBox(self.tab)
        self.temp_box.setFont(boldfont)
        self.temp_box.setObjectName("temp_box")
        # Label and value share one grid cell: the label is pinned to the left
        # edge while the value is centered across the full box width, under the
        # box title. (A QFormLayout could only center the pair as a group.)
        tempGrid = QtWidgets.QGridLayout(self.temp_box)
        tempGrid.setContentsMargins(10, 10, 10, 6)
        tempGrid.setHorizontalSpacing(0)
        tempGrid.setColumnStretch(0, 1)

        self.cpuTempLabel = QtWidgets.QLabel(self.temp_box)
        self.cpuTempLabel.setObjectName("cpuTempLabel")
        self.cpuTempLabel.setText("CPU:")
        self.cpuTempValue = QtWidgets.QLabel(self.temp_box)
        self.cpuTempValue.setObjectName("cpuTempValue")
        self.cpuTempValue.setFont(font)

        self.gpuTempLabel = QtWidgets.QLabel(self.temp_box)
        self.gpuTempLabel.setObjectName("gpuTempLabel")
        self.gpuTempLabel.setText("GPU:")
        self.gpuTempValue = QtWidgets.QLabel(self.temp_box)
        self.gpuTempValue.setObjectName("gpuTempValue")
        self.gpuTempValue.setFont(font)

        self.sysTempLabel = QtWidgets.QLabel(self.temp_box)
        self.sysTempLabel.setObjectName("sysTempLabel")
        self.sysTempLabel.setText("SYS:")
        self.sysTempValue = QtWidgets.QLabel(self.temp_box)
        self.sysTempValue.setObjectName("sysTempValue")
        self.sysTempValue.setFont(font)

        for row, (lbl, val) in enumerate(((self.cpuTempLabel, self.cpuTempValue),
                                          (self.gpuTempLabel, self.gpuTempValue),
                                          (self.sysTempLabel, self.sysTempValue))):
            tempGrid.addWidget(lbl, row, 0, Qt.AlignLeft | Qt.AlignVCenter)
            tempGrid.addWidget(val, row, 0, Qt.AlignHCenter | Qt.AlignVCenter)
        # Keep rows packed at the top instead of spreading over the box height
        # (the box is stretched taller to match the Misc box beside it).
        tempGrid.setRowStretch(3, 1)

        self.cpuTempLabel.setFont(boldfont)
        self.gpuTempLabel.setFont(boldfont)
        self.sysTempLabel.setFont(boldfont)
        self.cpuTempValue.setFont(font)
        self.gpuTempValue.setFont(font)
        self.sysTempValue.setFont(font)

        ##-----------Fan RPM------------##

        self.fan_box = QtWidgets.QGroupBox(self.tab)
        self.fan_box.setFont(boldfont)
        self.fan_box.setObjectName("fan_box")
        fanGrid = QtWidgets.QGridLayout(self.fan_box)
        fanGrid.setContentsMargins(10, 10, 10, 6)
        fanGrid.setHorizontalSpacing(0)
        fanGrid.setColumnStretch(0, 1)

        self.cpuFanSpeedLabel = QtWidgets.QLabel(self.fan_box)
        self.cpuFanSpeedLabel.setObjectName("cpuFanSpeedLabel")
        self.cpuFanSpeedLabel.setText("CPU:")
        self.cpuFanSpeedValue = QtWidgets.QLabel(self.fan_box)
        self.cpuFanSpeedValue.setObjectName("cpuFanSpeedValue")
        self.cpuFanSpeedValue.setFont(font)

        self.gpuFanSpeedLabel = QtWidgets.QLabel(self.fan_box)
        self.gpuFanSpeedLabel.setObjectName("gpuFanSpeedLabel")
        self.gpuFanSpeedLabel.setText("GPU:")
        self.gpuFanSpeedValue = QtWidgets.QLabel(self.fan_box)
        self.gpuFanSpeedValue.setObjectName("gpuFanSpeedValue")
        self.gpuFanSpeedValue.setFont(font)

        for row, (lbl, val) in enumerate(((self.cpuFanSpeedLabel, self.cpuFanSpeedValue),
                                          (self.gpuFanSpeedLabel, self.gpuFanSpeedValue))):
            fanGrid.addWidget(lbl, row, 0, Qt.AlignLeft | Qt.AlignVCenter)
            fanGrid.addWidget(val, row, 0, Qt.AlignHCenter | Qt.AlignVCenter)
        fanGrid.setRowStretch(2, 1)

        self.cpuFanSpeedLabel.setFont(boldfont)
        self.gpuFanSpeedLabel.setFont(boldfont)
        self.cpuFanSpeedValue.setFont(font)
        self.gpuFanSpeedValue.setFont(font)

        ##-------------Misc--------------##

        self.KB_box = QtWidgets.QGroupBox(self.tab)
        self.KB_box.setFont(boldfont)
        self.KB_box.setObjectName("KB_box")
        kbLayout = QtWidgets.QVBoxLayout(self.KB_box)
        kbLayout.setContentsMargins(10, 6, 10, 6)
        kbLayout.setSpacing(1)

        self.KBTimerCB = QtWidgets.QCheckBox(self.KB_box)
        self.KBTimerCB.setFont(font)
        self.KBTimerCB.setObjectName("global_KBTimer")

        self.LCDOverdriveCB = QtWidgets.QCheckBox(self.KB_box)
        self.LCDOverdriveCB.setFont(font)
        self.LCDOverdriveCB.setObjectName("LCDOverdrive")

        self.usbChargingCB = QtWidgets.QCheckBox(self.KB_box)
        self.usbChargingCB.setFont(font)
        self.usbChargingCB.setObjectName("usbCharging")

        self.chargeLimit = QtWidgets.QCheckBox(self.KB_box)
        self.chargeLimit.setFont(font)
        self.chargeLimit.setObjectName("ChargeLimit")

        for widget in (self.KBTimerCB, self.LCDOverdriveCB,
                       self.usbChargingCB, self.chargeLimit):
            # Same as the Mode box: cap the ~24px Breeze checkbox height.
            widget.setFixedHeight(20)
            kbLayout.addWidget(widget)
        kbLayout.addStretch()

        self.homeLayout.addWidget(self.temp_box, 2, 0)
        self.homeLayout.addWidget(self.fan_box, 2, 1)
        self.homeLayout.addWidget(self.KB_box, 2, 2)

        ##----------Undervolt-----------##

        self.undervolt_box = QtWidgets.QGroupBox(self.tab)
        self.undervolt_box.setFont(boldfont)
        self.undervolt_box.setObjectName("undervolt_box")
        self.undervoltLayout = QtWidgets.QVBoxLayout(self.undervolt_box)
        self.undervoltLayout.setContentsMargins(10, 10, 10, 10)
        self.undervoltLayout.setObjectName("undervoltLayout")

        voltRow = QtWidgets.QHBoxLayout()
        self.voltageLabel = QtWidgets.QLabel(self.undervolt_box)
        self.voltageLabel.setText("Voltage:")
        self.voltageLabel.setObjectName("voltageLabel")
        self.voltageValue = QtWidgets.QLabel(self.undervolt_box)
        self.voltageValue.setObjectName("voltageValue")
        self.voltageMinMaxLabel = QtWidgets.QLabel(self.undervolt_box)
        self.voltageMinMaxLabel.setText("Min / Max:")
        self.voltageMinMaxLabel.setObjectName("voltageMinMaxLabel")
        self.voltageMinMaxValue = QtWidgets.QLabel(self.undervolt_box)
        self.voltageMinMaxValue.setObjectName("voltageMinMaxValue")
        voltRow.addWidget(self.voltageLabel)
        voltRow.addWidget(self.voltageValue)
        voltRow.addSpacing(20)
        voltRow.addWidget(self.voltageMinMaxLabel)
        voltRow.addWidget(self.voltageMinMaxValue)
        voltRow.addStretch()

        self.voltageLabel.setFont(boldfont)
        self.voltageMinMaxLabel.setFont(boldfont)
        self.voltageValue.setFont(font)
        self.voltageMinMaxValue.setFont(font)

        self.undervoltStatus = QtWidgets.QTextBrowser(self.undervolt_box)
        self.undervoltStatus.setObjectName("undervoltStatus")
        self.undervoltStatus.setMinimumHeight(130)
        self.undervoltStatus.setFont(font)

        self.undervoltLayout.addLayout(voltRow)
        self.undervoltLayout.addWidget(self.undervoltStatus)

        self.homeLayout.addWidget(self.undervolt_box, 3, 0, 1, 3)

        ##----------Fan controls-------------##

        self.global_box = QtWidgets.QGroupBox(self.tab)
        self.global_box.setFont(boldfont)
        self.global_box.setObjectName("global_box")
        self.horizontalLayout = QtWidgets.QVBoxLayout(self.global_box)
        self.horizontalLayout.setContentsMargins(10, 10, 10, 6)
        self.horizontalLayout.setObjectName("horizontalLayout")

        self.global_auto = QtWidgets.QRadioButton(self.global_box)
        self.global_auto.setFont(font)
        self.global_auto.setChecked(True)
        self.global_auto.setObjectName("global_auto")
        self.horizontalLayout.addWidget(self.global_auto)

        self.global_turbo = QtWidgets.QRadioButton(self.global_box)
        self.global_turbo.setFont(font)
        self.global_turbo.setObjectName("global_turbo")
        self.horizontalLayout.addWidget(self.global_turbo)

        self.horizontalLayout.addStretch()

        def build_fan_box(title):
            box = QtWidgets.QGroupBox(self.tab)
            box.setFont(boldfont)
            box.setTitle(title)
            outer = QtWidgets.QHBoxLayout(box)
            outer.setContentsMargins(10, 10, 10, 6)
            radios = QtWidgets.QWidget(box)
            radioLayout = QtWidgets.QVBoxLayout(radios)
            radioLayout.setContentsMargins(0, 0, 0, 0)
            # Stretch above and below so the radios sit vertically centered
            # in the box, like the original fixed-geometry layout.
            radioLayout.addStretch()
            auto = QtWidgets.QRadioButton(radios)
            auto.setChecked(True)
            manual = QtWidgets.QRadioButton(radios)
            turbo = QtWidgets.QRadioButton(radios)
            for w in (auto, manual, turbo):
                w.setFont(font)
                radioLayout.addWidget(w)
            radioLayout.addStretch()
            slider = QtWidgets.QSlider(box)
            slider.setEnabled(False)
            slider.setTickInterval(1)
            slider.setTickPosition(QtWidgets.QSlider.TicksAbove)
            slider.setMaximum(10)
            slider.setProperty("value", 3)
            slider.setOrientation(QtCore.Qt.Vertical)
            outer.addWidget(radios)
            outer.addWidget(slider)
            return box, auto, manual, turbo, slider

        (self.cpu_box, self.cpu_auto, self.cpu_manual, self.cpu_turbo,
         self.cpuManualSlider) = build_fan_box("CPU Fan")
        self.cpu_box.setObjectName("cpu_box")
        self.cpu_auto.setObjectName("cpu_auto")
        self.cpu_manual.setObjectName("cpu_manual")
        self.cpu_turbo.setObjectName("cpu_turbo")
        self.cpuManualSlider.setObjectName("cpuManualSlider")

        (self.gpu_box, self.gpu_auto, self.gpu_manual, self.gpu_turbo,
         self.gpuManualSlider) = build_fan_box("GPU Fan")
        self.gpu_box.setObjectName("gpu_box")
        self.gpu_auto.setObjectName("gpu_auto")
        self.gpu_manual.setObjectName("gpu_manual")
        self.gpu_turbo.setObjectName("gpu_turbo")
        self.gpuManualSlider.setObjectName("gpuManualSlider")

        ##------Middle column (buttons + Global)------##
        # Mirrors the original layout: Reset and Undervolt on top, the Global
        # box in the middle, and Exit pinned to the bottom -- all stacked in the
        # column between the CPU and GPU fan boxes.
        self.middle_box = QtWidgets.QWidget(self.tab)
        middleLayout = QtWidgets.QVBoxLayout(self.middle_box)
        middleLayout.setContentsMargins(0, 0, 0, 0)

        self.reset_button = QtWidgets.QPushButton(self.middle_box)
        self.reset_button.setFont(font)
        self.reset_button.setObjectName("restPushButton")
        self.reset_button.setText("Reset")
        self.undervolt_button = QtWidgets.QPushButton(self.middle_box)
        self.undervolt_button.setFont(font)
        self.undervolt_button.setObjectName("undervoltPushButton")
        self.undervolt_button.setText("Undervolt")
        self.exit_button = QtWidgets.QPushButton(self.middle_box)
        self.exit_button.setFont(boldfont)
        self.exit_button.setObjectName("pushButton")
        self.exit_button.setText("Exit")

        # Offset selector: index N == -N*20 mV (0, -20 ... -700). Sits directly
        # above the Undervolt button so the value and the action are adjacent;
        # no label needed since each item reads e.g. "-140 mV".
        self.undervolt_dropdown = QtWidgets.QComboBox(self.middle_box)
        self.undervolt_dropdown.setObjectName("undervolt_dropdown")
        self.undervolt_dropdown.setFont(font)
        for mv in range(0, 701, 20):
            self.undervolt_dropdown.addItem("0 mV" if mv == 0 else "-%d mV" % mv)
        self.undervolt_dropdown.setCurrentIndex(0)
        # Editable so values between the 20 mV presets (e.g. -85 mV) can be
        # typed directly. The validator accepts an optional minus, up to 3
        # digits and an optional " mV" suffix; the range is clamped in
        # main.applySelectedUndervolt before it reaches the MSR.
        self.undervolt_dropdown.setEditable(True)
        self.undervolt_dropdown.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        # An editable combo embeds a QLineEdit that keeps Qt's default white
        # Base / black Text instead of the app's dark palette, and its popup
        # window defaults to a white Window role (white-on-white items).
        # Give the combo, its line edit and its popup the tab's own #252525.
        dark = QtGui.QPalette()
        dark.setColor(QtGui.QPalette.Window, QtGui.QColor(37, 37, 37))
        dark.setColor(QtGui.QPalette.Base, QtGui.QColor(37, 37, 37))
        dark.setColor(QtGui.QPalette.Text, QtCore.Qt.white)
        dark.setColor(QtGui.QPalette.Button, QtGui.QColor(37, 37, 37))
        dark.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.white)
        dark.setColor(QtGui.QPalette.Highlight, QtGui.QColor(42, 130, 218))
        dark.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.black)
        self.undervolt_dropdown.setPalette(dark)
        self.undervolt_dropdown.lineEdit().setPalette(dark)
        # The popup is a separate top-level window, so the tab's stylesheet
        # never reaches it and the style engine paints it white. A stylesheet
        # on the combo itself would work but also replaces the native frame
        # and arrow, so style the popup view (and its container frame)
        # directly instead.
        popupQss = ("background-color: #252525; color: white;"
                    " selection-background-color: #2a82da; selection-color: black;")
        self.undervolt_dropdown.view().setStyleSheet(popupQss)
        self.undervolt_dropdown.view().setPalette(dark)
        container = self.undervolt_dropdown.view().parentWidget()
        if container is not None:
            container.setStyleSheet("QFrame { background-color: #252525; }")
            container.setPalette(dark)
        # The popup container is a separate top-level window; it paints the
        # area around the item view with its own Window colour.
        if self.undervolt_dropdown.view().parentWidget() is not None:
            self.undervolt_dropdown.view().parentWidget().setPalette(dark)
        validator = QtGui.QRegularExpressionValidator(
            QtCore.QRegularExpression(r"-?\d{0,3}( ?mV)?"), self.undervolt_dropdown)
        self.undervolt_dropdown.setValidator(validator)

        # The controls in this column are narrower than the column itself:
        # each sits at a fixed width, centred, with the leftover space left
        # empty on both sides. 2/3 of the column's design width (158px) keeps
        # them aligned and leaves ~1/3 as whitespace on the sides.
        middleWidgets = (self.reset_button, self.undervolt_dropdown,
                         self.undervolt_button, self.global_box,
                         self.exit_button)
        middleWidth = 105
        for widget in middleWidgets:
            widget.setFixedWidth(middleWidth)
            row = QtWidgets.QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.addStretch(1)
            row.addWidget(widget)
            row.addStretch(1)
            middleLayout.addLayout(row)
            # Offset selector belongs with the Undervolt button it feeds.
            if widget is self.reset_button:
                middleLayout.addSpacing(4)
            # Pin Exit to the bottom of the column.
            if widget is self.global_box:
                middleLayout.addStretch()

        self.homeLayout.addWidget(self.cpu_box, 4, 0)
        self.homeLayout.addWidget(self.middle_box, 4, 1)
        self.homeLayout.addWidget(self.gpu_box, 4, 2)
        self.homeLayout.setRowStretch(5, 1)

        ##--------MONITORING TAB--------##

        self.voltageChart = CustomChart("Voltage", "voltage_box", 64, "#80ff0000", "#E74C3C", "", "", (0, 63), (0.5, 1.2))
        self.cpuChart = CustomChart("CPU Temp", "cpuchart_box", 64, "#800000ff", "#0E86D4", "", "", (0, 63), (0, 110))
        self.gpuChart = CustomChart("GPU Temp", "gpuchart_box", 64, "#8000ff00", "#0E8600", "", "", (0, 63), (0, 110))
        self.sysChart = CustomChart("SYS Temp", "syschart_box", 64, "#8000ffff", "#0Effff", "", "", (0, 63), (0, 110))
        self.cpuFanChart = CustomChart("CPU Fan", "cpufanchart_box", 64, "#800080ff", "#0E80ff", "", "", (0, 63), (0, 6000))
        self.gpuFanChart = CustomChart("GPU Fan", "gpufanchart_box", 64, "#8000ff80", "#0Eff80", "", "", (0, 63), (0, 6000))

        self.chart_box = QtWidgets.QGroupBox(self.monitoring_tab)
        self.chart_box.setObjectName("monitoring_box")
        monitoringLayout = QtWidgets.QVBoxLayout(self.monitoring_tab)
        monitoringLayout.setContentsMargins(0, 0, 0, 0)
        monitoringLayout.addWidget(self.chart_box)

        self.vchart = QtWidgets.QVBoxLayout(self.chart_box)
        self.vchart.setSpacing(0)
        self.vchart.setContentsMargins(0, 0, 0, 0)
        self.vchart.addWidget(self.voltageChart.chartView)
        self.vchart.addWidget(self.cpuChart.chartView)
        self.vchart.addWidget(self.gpuChart.chartView)
        self.vchart.addWidget(self.sysChart.chartView)
        self.vchart.addWidget(self.cpuFanChart.chartView)
        self.vchart.addWidget(self.gpuFanChart.chartView)
        self.chart_box.setLayout(self.vchart)

        ##---------KEYBOARD TAB---------##

        self.keyboard_box = QtWidgets.QGroupBox(self.keyboard_tab)
        self.keyboard_box.setFont(boldfont)
        self.keyboard_box.setObjectName("keyboard_box")
        keyboardLayout = QtWidgets.QVBoxLayout(self.keyboard_tab)
        keyboardLayout.setContentsMargins(8, 8, 8, 8)
        keyboardLayout.addWidget(self.keyboard_box)

        kbForm = QtWidgets.QFormLayout(self.keyboard_box)
        kbForm.setContentsMargins(10, 12, 10, 10)

        self.mode_combo = QtWidgets.QComboBox(self.keyboard_box)
        self.mode_combo.setObjectName("mode_combo")
        self.mode_combo.setFont(font)
        self.mode_combo.addItems(["Static", "Breath", "Neon", "Wave", "Shifting", "Zoom"])

        self.zone_combo = QtWidgets.QComboBox(self.keyboard_box)
        self.zone_combo.setObjectName("zone_combo")
        self.zone_combo.setFont(font)
        self.zone_combo.addItems(["all", "1", "2", "3", "4"])

        self.speed_spin = QtWidgets.QSlider(self.keyboard_box)
        self.speed_spin.setObjectName("speed_spin")
        self.speed_spin.setFont(font)
        self.speed_spin.setOrientation(QtCore.Qt.Horizontal)
        self.speed_spin.setRange(0, 9)
        self.speed_spin.setValue(4)

        self.brightness_spin = QtWidgets.QSlider(self.keyboard_box)
        self.brightness_spin.setObjectName("brightness_spin")
        self.brightness_spin.setFont(font)
        self.brightness_spin.setOrientation(QtCore.Qt.Horizontal)
        self.brightness_spin.setRange(0, 100)
        self.brightness_spin.setValue(100)

        self.direction_combo = QtWidgets.QComboBox(self.keyboard_box)
        self.direction_combo.setObjectName("direction_combo")
        self.direction_combo.setFont(font)
        self.direction_combo.addItems(["Right to left", "Left to right"])

        self.mode_label = QtWidgets.QLabel(self.keyboard_box)
        self.mode_label.setObjectName("mode_label")
        self.zone_label = QtWidgets.QLabel(self.keyboard_box)
        self.zone_label.setObjectName("zone_label")
        self.speed_label = QtWidgets.QLabel(self.keyboard_box)
        self.speed_label.setObjectName("speed_label")
        self.brightness_label = QtWidgets.QLabel(self.keyboard_box)
        self.brightness_label.setObjectName("brightness_label")
        self.direction_label = QtWidgets.QLabel(self.keyboard_box)
        self.direction_label.setObjectName("direction_label")
        for lbl in (self.mode_label, self.zone_label, self.speed_label,
                    self.brightness_label, self.direction_label):
            lbl.setFont(boldfont)

        kbForm.addRow(self.mode_label, self.mode_combo)
        kbForm.addRow(self.zone_label, self.zone_combo)
        kbForm.addRow(self.speed_label, self.speed_spin)
        kbForm.addRow(self.brightness_label, self.brightness_spin)
        kbForm.addRow(self.direction_label, self.direction_combo)

        kbButtonRow = QtWidgets.QHBoxLayout()
        self.color_button = QtWidgets.QPushButton(self.keyboard_box)
        self.color_button.setObjectName("color_button")
        self.color_button.setFont(font)
        self.apply_button = QtWidgets.QPushButton(self.keyboard_box)
        self.apply_button.setObjectName("apply_button")
        self.apply_button.setFont(font)
        self.save_button = QtWidgets.QPushButton(self.keyboard_box)
        self.save_button.setObjectName("save_button")
        self.save_button.setFont(font)
        self.load_button = QtWidgets.QPushButton(self.keyboard_box)
        self.load_button.setObjectName("load_button")
        self.load_button.setFont(font)
        for btn in (self.color_button, self.apply_button,
                    self.save_button, self.load_button):
            kbButtonRow.addWidget(btn)
        kbForm.addRow(kbButtonRow)

        ##--- capability flags (set by main.py before setupUI) ---##
        # Predator-only widgets are hidden on machines that lack the register.
        # NOTE: only the Turbo *power mode* radio is Predator-only. The Global
        # "Turbo" radio is the fan max-speed mode, which Nitro machines have too.
        if not getattr(self, "has_turbo_mode", True):
            self.turboModeCB.setVisible(False)
        if not getattr(self, "has_lcd_overdrive", True):
            self.LCDOverdriveCB.setVisible(False)
        # main.py removes the keyboard tab entirely when the machine has no
        # acer-gkbbl devices.

        ## ----------------------------------------------------
        # Signal wiring that used to live in the generated file

        self.global_turbo.clicked['bool'].connect(self.cpu_turbo.setChecked)
        self.global_turbo.clicked['bool'].connect(self.gpu_turbo.setChecked)
        self.global_auto.clicked['bool'].connect(self.cpu_auto.setChecked)
        self.global_auto.clicked['bool'].connect(self.gpu_auto.setChecked)

        self.cpu_manual.toggled['bool'].connect(self.cpuManualSlider.setEnabled)
        self.gpu_manual.toggled['bool'].connect(self.gpuManualSlider.setEnabled)

        # Prevents the user from disabling max cpu or gpu fan mode individually when global turbo mode is enabled
        self.global_turbo.toggled['bool'].connect(self.cpu_auto.setDisabled)
        self.global_turbo.toggled['bool'].connect(self.cpu_manual.setDisabled)
        self.global_turbo.toggled['bool'].connect(self.gpu_auto.setDisabled)
        self.global_turbo.toggled['bool'].connect(self.gpu_manual.setDisabled)

        ## ----------------------------------------------------
        # Set button text and window titles 

        # Window title
        PredatorSense.setWindowTitle("Linux PredatorSense")

        # Power Status
        self.powerStatusValue.setText("0")
        self.batteryStatusValue.setText("Battery Not In Use")
        self.batteryChargeLimitValue.setText("Off")
        self.predatorModeValue.setText("Default")

        # Predator mode box
        self.predMode.setTitle("Mode")
        self.quietModeCB.setText("Quiet")
        self.defaultModeCB.setText("Default")
        self.extremeModeCB.setText("Extreme")
        self.turboModeCB.setText("Turbo")

        # Fan box
        self.fan_box.setTitle("Fan RPM")

        # Temp box
        self.temp_box.setTitle("Temps")

        self.cpuFanSpeedValue.setText("6000" + " RPM")
        self.gpuFanSpeedValue.setText("6000" + " RPM")
        self.cpuTempValue.setText("100" + "°")
        self.gpuTempValue.setText("100" + "°")
        self.sysTempValue.setText("100" + "°")

        # Misc box
        self.KB_box.setTitle("Misc")
        self.KBTimerCB.setText("KB Timeout")
        self.LCDOverdriveCB.setText("LCD Overdrive")
        self.usbChargingCB.setText("USB Charging")
        self.chargeLimit.setText("Charge Limit")

        # Status box
        self.status_box.setTitle("Status")

        # Undervolt box
        self.undervolt_box.setTitle("Undervolt")

        self.voltageValue.setText("0.00")
        self.voltageMinMaxValue.setText("0.00")

        # Global box
        self.global_box.setTitle("Global")
        self.global_auto.setText("Auto")
        self.global_turbo.setText("Turbo")

        # CPU box
        self.cpu_auto.setText("Auto")
        self.cpu_manual.setText("Manual")
        self.cpu_turbo.setText("Max speed")

        # GPU box
        self.gpu_auto.setText("Auto")
        self.gpu_manual.setText("Manual")
        self.gpu_turbo.setText("Max speed")

        # Keyboard box
        self.keyboard_box.setTitle("Keyboard")
        self.mode_label.setText("Mode:")
        self.zone_label.setText("Zone:")
        self.speed_label.setText("Speed:")
        self.brightness_label.setText("Brightness:")
        self.direction_label.setText("Direction:")
        self.color_button.setText("Select Color")
        self.apply_button.setText("Apply")
        self.save_button.setText("Save")
        self.load_button.setText("Load")
        self.fan_control_tab.setTabText(self.fan_control_tab.indexOf(self.keyboard_tab), "Keyboard")
