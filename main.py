"""
ABG Analyzer Simulation - SBE3220 Medical Equipment II
FINAL VERSION - With working waveforms and simplified popup results window
"""

import sys
import math
import random
import time
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QGroupBox, QGridLayout,
    QProgressBar, QComboBox, QFrame, QSplitter, QTextEdit,
    QDialog, QDialogButtonBox  # Added for popup window
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QLinearGradient


# ─────────────────────────────────────────────
#  CONSTANTS & REFERENCE RANGES
# ─────────────────────────────────────────────
NORMAL = {
    "pH":   (7.35, 7.45),
    "pCO2": (35.0, 45.0),   # mmHg
    "pO2":  (80.0, 100.0),  # mmHg
    "HCO3": (22.0, 26.0),   # mEq/L
    "SaO2": (95.0, 100.0),  # %
}

PRESETS = {
    "Normal":                      {"pH": 7.40, "pCO2": 40.0, "pO2": 95.0},
    "Respiratory Acidosis":        {"pH": 7.25, "pCO2": 60.0, "pO2": 70.0},
    "Respiratory Alkalosis":       {"pH": 7.52, "pCO2": 28.0, "pO2": 100.0},
    "Metabolic Acidosis":          {"pH": 7.28, "pCO2": 38.0, "pO2": 90.0},
    "Metabolic Alkalosis":         {"pH": 7.50, "pCO2": 46.0, "pO2": 90.0},
    "Mixed Resp+Met Acidosis":     {"pH": 7.18, "pCO2": 58.0, "pO2": 60.0},
    "ARDS / Hypoxemia":            {"pH": 7.38, "pCO2": 42.0, "pO2": 45.0},
}


# ─────────────────────────────────────────────
#  RESULTS POPUP WINDOW - SIMPLIFIED VERSION
# ─────────────────────────────────────────────
class ResultsPopup(QDialog):
    """Popup window to display ABG analysis results"""
    
    def __init__(self, results, parent=None):
        super().__init__(parent)
        self.results = results
        self.setWindowTitle("ABG Analysis Results")
        self.setMinimumSize(600, 500)
        # Enable maximize button
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #0a0f1e;
                color: #cce0f0;
            }
            QLabel {
                color: #cce0f0;
            }
            QGroupBox {
                border: 2px solid #1e3a5f;
                border-radius: 8px;
                margin-top: 14px;
                padding: 15px;
                font-weight: bold;
                color: #7ab8e8;
                font-size: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("📊 ARTERIAL BLOOD GAS ANALYSIS RESULTS")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #40aaff; padding: 10px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # MEASURED PARAMETERS SECTION
        params_group = QGroupBox("Measured Parameters")
        params_group.setStyleSheet("""
            QGroupBox {
                font-size: 13px;
                font-weight: bold;
            }
        """)
        params_layout = QGridLayout(params_group)
        params_layout.setSpacing(15)
        
        # Headers
        headers = ["Parameter", "Value", "Normal Range", "Status"]
        for col, header in enumerate(headers):
            label = QLabel(header)
            label.setStyleSheet("font-weight: bold; color: #00e5ff; font-size: 12px; padding: 5px;")
            label.setAlignment(Qt.AlignCenter)
            params_layout.addWidget(label, 0, col)
        
        # Data rows
        parameters = [
            ("pH", f"{self.results['pH']:.3f}", "7.35 - 7.45"),
            ("pCO₂", f"{self.results['pCO2']:.1f} mmHg", "35 - 45 mmHg"),
            ("pO₂", f"{self.results['pO2']:.1f} mmHg", "80 - 100 mmHg"),
            ("HCO₃⁻", f"{self.results['HCO3']:.1f} mEq/L", "22 - 26 mEq/L"),
            ("SaO₂", f"{self.results['SaO2']:.1f} %", "95 - 100 %"),
        ]
        
        def get_status(value, param_type):
            if param_type == "pH":
                if value < 7.35:
                    return "🔴 LOW", "#ff1744"
                elif value > 7.45:
                    return "🔴 HIGH", "#ff1744"
                else:
                    return "✅ NORMAL", "#00c853"
            elif param_type == "pCO2":
                if value < 35:
                    return "🔵 LOW", "#2979ff"
                elif value > 45:
                    return "🔴 HIGH", "#ff1744"
                else:
                    return "✅ NORMAL", "#00c853"
            elif param_type == "pO2":
                if value < 80:
                    return "⚠️ LOW", "#ff1744"
                else:
                    return "✅ NORMAL", "#00c853"
            elif param_type == "HCO3":
                if value < 22:
                    return "🔵 LOW", "#2979ff"
                elif value > 26:
                    return "🔴 HIGH", "#ff1744"
                else:
                    return "✅ NORMAL", "#00c853"
            else:  # SaO2
                if value < 95:
                    return "⚠️ LOW", "#ff1744"
                else:
                    return "✅ NORMAL", "#00c853"
        
        for row, (param, value, normal_range) in enumerate(parameters, start=1):
            # Parameter name
            param_label = QLabel(param)
            param_label.setStyleSheet("font-weight: bold; font-size: 12px; padding: 5px;")
            param_label.setAlignment(Qt.AlignCenter)
            params_layout.addWidget(param_label, row, 0)
            
            # Value
            value_label = QLabel(value)
            value_label.setStyleSheet("font-family: 'Courier New'; font-size: 14px; color: #00e5ff; font-weight: bold; padding: 5px;")
            value_label.setAlignment(Qt.AlignCenter)
            params_layout.addWidget(value_label, row, 1)
            
            # Normal range
            range_label = QLabel(normal_range)
            range_label.setStyleSheet("color: #7ab8e8; font-size: 12px; padding: 5px;")
            range_label.setAlignment(Qt.AlignCenter)
            params_layout.addWidget(range_label, row, 2)
            
            # Status
            if param == "pH":
                status_text, color = get_status(self.results['pH'], "pH")
            elif param == "pCO₂":
                status_text, color = get_status(self.results['pCO2'], "pCO2")
            elif param == "pO₂":
                status_text, color = get_status(self.results['pO2'], "pO2")
            elif param == "HCO₃⁻":
                status_text, color = get_status(self.results['HCO3'], "HCO3")
            else:  # SaO₂
                status_text, color = get_status(self.results['SaO2'], "SaO2")
                
            status_label = QLabel(status_text)
            status_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 12px; padding: 5px;")
            status_label.setAlignment(Qt.AlignCenter)
            params_layout.addWidget(status_label, row, 3)
        
        layout.addWidget(params_group)
        
        # CLINICAL INTERPRETATION SECTION
        interp_group = QGroupBox("Clinical Interpretation")
        interp_group.setStyleSheet("""
            QGroupBox {
                font-size: 13px;
                font-weight: bold;
            }
        """)
        interp_layout = QVBoxLayout(interp_group)
        
        interpretation = self._generate_interpretation()
        interp_text = QTextEdit()
        interp_text.setReadOnly(True)
        interp_text.setText(interpretation)
        interp_text.setStyleSheet("""
            QTextEdit {
                background-color: #050c1a;
                border: 2px solid #1e3a5f;
                border-radius: 8px;
                font-family: 'Courier New';
                font-size: 12px;
                color: #aad4ff;
                padding: 15px;
                line-height: 1.6;
            }
        """)
        interp_text.setMinimumHeight(200)
        interp_layout.addWidget(interp_text)
        layout.addWidget(interp_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #003366;
                color: #aad4ff;
                border: 2px solid #0055aa;
                border-radius: 6px;
                padding: 10px 25px;
                font-weight: bold;
                font-size: 12px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #0044aa;
            }
        """)
        close_btn.clicked.connect(self.accept)
        
        # Print button (optional)
        print_btn = QPushButton("🖨️ Print Report")
        print_btn.setStyleSheet("""
            QPushButton {
                background-color: #664d00;
                color: #ffd966;
                border: 2px solid #aa8800;
                border-radius: 6px;
                padding: 10px 25px;
                font-weight: bold;
                font-size: 12px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #886600;
            }
        """)
        print_btn.clicked.connect(self._print_report)
        
        button_layout.addStretch()
        button_layout.addWidget(print_btn)
        button_layout.addWidget(close_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
    
    def _print_report(self):
        """Simulate printing the report"""
        # In a real application, this would open a print dialog
        # Here we just show a message
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(self, "Print Report", 
                               "Report sent to printer.\n(This is a simulation)")
    
    def _generate_interpretation(self):
        """Generate clinical interpretation based on results"""
        pH = self.results['pH']
        pCO2 = self.results['pCO2']
        pO2 = self.results['pO2']
        HCO3 = self.results['HCO3']
        
        lines = []
        lines.append("═" * 50)
        lines.append("         ARTERIAL BLOOD GAS INTERPRETATION")
        lines.append("═" * 50)

        if 7.35 <= pH <= 7.45:
            lines.append("✅ pH: NORMAL (7.35–7.45)")
        elif pH < 7.35:
            lines.append("🔴 pH: ACIDOSIS (< 7.35)")
        else:
            lines.append("🔵 pH: ALKALOSIS (> 7.45)")

        if pCO2 < 35:
            lines.append("🔵 pCO₂: LOW → Respiratory Alkalosis")
        elif pCO2 > 45:
            lines.append("🔴 pCO₂: HIGH → Respiratory Acidosis")
        else:
            lines.append("✅ pCO₂: NORMAL (35–45 mmHg)")

        if HCO3 < 22:
            lines.append("🔴 HCO₃⁻: LOW → Metabolic Acidosis")
        elif HCO3 > 26:
            lines.append("🔵 HCO₃⁻: HIGH → Metabolic Alkalosis")
        else:
            lines.append("✅ HCO₃⁻: NORMAL (22–26 mEq/L)")

        if pO2 < 60:
            lines.append("⚠️  pO₂: CRITICAL → Severe Hypoxemia")
        elif pO2 < 80:
            lines.append("🟡 pO₂: LOW → Mild-Moderate Hypoxemia")
        else:
            lines.append("✅ pO₂: NORMAL (80–100 mmHg)")

        lines.append("─" * 50)
        lines.append("📋 DIAGNOSIS:")
        
        if pH < 7.35 and pCO2 > 45 and HCO3 >= 22:
            lines.append("   → Acute Respiratory Acidosis")
        elif pH < 7.35 and pCO2 > 45 and HCO3 > 26:
            lines.append("   → Chronic Respiratory Acidosis")
        elif pH > 7.45 and pCO2 < 35 and HCO3 <= 26:
            lines.append("   → Acute Respiratory Alkalosis")
        elif pH > 7.45 and pCO2 < 35 and HCO3 < 22:
            lines.append("   → Chronic Respiratory Alkalosis")
        elif pH < 7.35 and HCO3 < 22 and pCO2 <= 45:
            lines.append("   → Metabolic Acidosis")
        elif pH > 7.45 and HCO3 > 26 and pCO2 >= 35:
            lines.append("   → Metabolic Alkalosis")
        elif pH < 7.35 and pCO2 > 45 and HCO3 < 22:
            lines.append("   → Mixed Respiratory & Metabolic Acidosis")
        elif 7.35 <= pH <= 7.45:
            lines.append("   → Normal ABG")
        else:
            lines.append("   → Compensated / Mixed Disorder")
        
        lines.append("═" * 50)
        return "\n".join(lines)


# ─────────────────────────────────────────────
#  ELECTRODE MODELS WITH FULL PHYSICS
# ─────────────────────────────────────────────
class ElectrodeModels:
    """Complete physical models for all electrodes"""
    
    def __init__(self, temperature_celsius=37.0):
        self.T_celsius = temperature_celsius
        self.R = 8.314  # Gas constant (J/mol·K)
        self.F = 96485  # Faraday constant (C/mol)
        
        # Electrode-specific parameters
        self.ph_slope_efficiency = 0.97
        self.ph_asymmetry_potential = random.uniform(-2, 2)
        
        # Severinghaus parameters
        self.inner_HCO3 = 24.0
        self.pK1_37 = 6.1
        self.dpK_dT = -0.005
        
        # Clark electrode parameters
        self.electrode_area = 0.5
        self.membrane_thickness = 20e-4
        self.D0_25 = 2.0e-5
        self.Ea_D = 18000
        self.alpha_25 = 1.5e-3 / 760
        self.delta_H = 12000
        
    def set_temperature(self, temp_celsius):
        self.T_celsius = temp_celsius
    
    def nernst_pH(self, pH, add_noise=True):
        """pH electrode - Nernst equation"""
        if pH < 6.5 or pH > 8.0:
            pH = max(6.5, min(8.0, pH))
        
        T_kelvin = self.T_celsius + 273.15
        n = 1
        
        theoretical_slope = -(self.R * T_kelvin) / (n * self.F) * math.log(10) * 1000
        actual_slope = theoretical_slope * self.ph_slope_efficiency
        
        voltage = self.ph_asymmetry_potential + actual_slope * (pH - 7.0)
        
        if abs(voltage) > 100:
            voltage = max(-100, min(100, voltage))
        
        if add_noise:
            voltage += random.gauss(0, 0.05)
        
        return voltage
    
    def severinghaus_pCO2(self, pCO2_mmHg, add_noise=True):
        """pCO2 electrode - Severinghaus principle"""
        if pCO2_mmHg < 5 or pCO2_mmHg > 150:
            pCO2_mmHg = max(5, min(150, pCO2_mmHg))
        
        T_kelvin = self.T_celsius + 273.15
        
        alpha_37 = 0.0307
        temp_coeff_solubility = 0.015
        alpha_T = alpha_37 * (1 + temp_coeff_solubility * (self.T_celsius - 37.0))
        
        CO2_dissolved = alpha_T * pCO2_mmHg
        
        pK1_T = self.pK1_37 + self.dpK_dT * (self.T_celsius - 37.0)
        
        if CO2_dissolved > 0:
            inner_pH = pK1_T + math.log10(self.inner_HCO3 / CO2_dissolved)
        else:
            inner_pH = 8.5
        
        voltage = self.nernst_pH(inner_pH, add_noise=False)
        
        if abs(voltage) > 100:
            voltage = max(-100, min(100, voltage))
        
        if add_noise:
            voltage += random.gauss(0, 0.08)
        
        return voltage
    
    def clark_pO2(self, pO2_mmHg, flow_rate=1.0, add_noise=True):
        """pO2 electrode - Clark principle with overflow protection"""
        if pO2_mmHg < 0:
            pO2_mmHg = 0
        elif pO2_mmHg > 300:
            pO2_mmHg = 300
        
        T_kelvin = self.T_celsius + 273.15
        
        D_T = self.D0_25 * math.exp(-self.Ea_D/self.R * (1/T_kelvin - 1/298.15))
        Pm = D_T / self.membrane_thickness
        alpha_T = self.alpha_25 * math.exp(-self.delta_H/self.R * (1/T_kelvin - 1/298.15))
        
        n = 4
        area_cm2 = self.electrode_area / 100
        
        current_A = (n * self.F * area_cm2 * Pm * alpha_T * pO2_mmHg)
        current_nA = current_A * 1e9
        
        # Safety check for overflow
        if current_nA > 50:
            current_nA = pO2_mmHg * 0.05
            current_nA = min(30, current_nA)
        
        flow_factor = 0.8 + 0.2 * flow_rate
        current_nA *= flow_factor
        
        if pO2_mmHg < 30:
            depletion_factor = 0.9 + 0.1 * (pO2_mmHg / 30)
            current_nA *= max(0.5, depletion_factor)
        
        if add_noise:
            noise = random.gauss(0, 0.05 * current_nA)
            current_nA += noise
        
        return max(0, min(50, current_nA))


# ─────────────────────────────────────────────
#  IMPROVED WAVEFORM WIDGET WITH FULL FEATURES
# ─────────────────────────────────────────────
class WaveformWidget(QWidget):
    """Real-time waveform display with grid and labels"""
    
    def __init__(self, label="Signal", color="#00e5ff", unit="mV", 
                 y_range=(-80, 20), parent=None):
        super().__init__(parent)
        self.label = label
        self.color = QColor(color)
        self.unit = unit
        self.y_range = y_range
        self.data = [0.0] * 200
        self.setMinimumHeight(120)
        self.setMinimumWidth(350)
        self.setMaximumHeight(150)

    def push(self, value):
        """Add new data point"""
        # Ensure value is within display range
        if value < self.y_range[0]:
            value = self.y_range[0]
        elif value > self.y_range[1]:
            value = self.y_range[1]
        
        self.data.append(value)
        if len(self.data) > 200:
            self.data.pop(0)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        
        # Background
        bg = QLinearGradient(0, 0, 0, h)
        bg.setColorAt(0, QColor(10, 15, 30))
        bg.setColorAt(1, QColor(5, 10, 20))
        p.fillRect(self.rect(), QBrush(bg))

        # Draw grid
        pen = QPen(QColor(40, 60, 80), 1, Qt.DotLine)
        p.setPen(pen)
        
        # Horizontal grid lines (25%, 50%, 75%)
        for i in range(1, 4):
            y = int(h * i / 4)
            p.drawLine(0, y, w, y)
            # Add value labels
            p.setPen(QColor(80, 100, 120))
            p.setFont(QFont("Courier New", 7))
            value = self.y_range[1] - (i/4) * (self.y_range[1] - self.y_range[0])
            p.drawText(5, y-2, f"{value:.0f} {self.unit}")

        # Vertical grid lines (every 25% of width)
        for i in range(1, 4):
            x = int(w * i / 4)
            p.drawLine(x, 0, x, h)

        # Title label
        p.setPen(QColor(150, 180, 200))
        p.setFont(QFont("Courier New", 9, QFont.Bold))
        p.drawText(10, 20, self.label)

        # Current value
        if self.data:
            current = self.data[-1]
            p.setPen(self.color)
            p.setFont(QFont("Courier New", 10, QFont.Bold))
            value_text = f"{current:.2f} {self.unit}"
            text_width = p.fontMetrics().horizontalAdvance(value_text)
            p.drawText(w - text_width - 10, 20, value_text)

        if len(self.data) < 2:
            return

        # Draw waveform (last 150 points)
        y_min, y_max = self.y_range
        y_range_size = y_max - y_min if y_max != y_min else 1

        pen = QPen(self.color, 2)
        p.setPen(pen)
        pts = []
        
        # Get last 150 points for display
        display_data = self.data[-150:]
        
        for i, v in enumerate(display_data):
            x = int(i * w / 150)
            # Scale to widget height (with 10px margins)
            y = int(10 + (h - 20) * (1 - (v - y_min) / y_range_size))
            y = max(10, min(h - 10, y))
            pts.append((x, y))

        # Draw connected lines
        for i in range(1, len(pts)):
            p.drawLine(pts[i-1][0], pts[i-1][1], pts[i][0], pts[i][1])

        # Draw zero line if within range
        if y_min <= 0 <= y_max:
            zero_y = int(10 + (h - 20) * (1 - (0 - y_min) / y_range_size))
            pen = QPen(QColor(100, 100, 100), 1, Qt.DashLine)
            p.setPen(pen)
            p.drawLine(0, zero_y, w, zero_y)

        p.end()


# ─────────────────────────────────────────────
#  ADVANCED CIRCUIT SIMULATION WIDGET
# ─────────────────────────────────────────────
class CircuitWidget(QWidget):
    """Dynamic circuit visualization for ABG interface"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 350)
        self.signals = {"ph": 0.0, "pCO2": 0.0, "pO2": 0.0, "temp": 37.0}
        self._pulse = 0.0
        
    def update_signals(self, signals):
        self.signals = signals
        self._pulse += 0.2
        self.update()

    def _draw_component(self, p, x, y, label, color, is_opamp=False):
        p.setPen(QPen(QColor(color), 2))
        p.setBrush(QColor(15, 25, 45))
        if is_opamp:
            from PyQt5.QtCore import QPoint
            from PyQt5.QtGui import QPolygon
            pts = [QPoint(x, y-25), QPoint(x, y+25), QPoint(x+40, y)]
            p.drawPolygon(QPolygon(pts))
            p.setPen(QColor(255, 255, 255))
            p.setFont(QFont("Consolas", 6))
            p.drawText(x+5, y+3, label)
        else:
            p.drawRect(x, y-15, 60, 30)
            p.setPen(QColor(255, 255, 255))
            p.setFont(QFont("Consolas", 6, QFont.Bold))
            p.drawText(x+5, y+5, label)

    def _draw_resistor(self, p, x, y, horizontal=True):
        from PyQt5.QtCore import QPoint
        p.setPen(QPen(QColor("#ffaa00"), 1.5))
        if horizontal:
            pts = [QPoint(x,y), QPoint(x+10,y), QPoint(x+13,y-6), QPoint(x+19,y+6),
                   QPoint(x+25,y-6), QPoint(x+31,y+6), QPoint(x+37,y-6), QPoint(x+40,y), QPoint(x+50,y)]
        else:
            pts = [QPoint(x,y), QPoint(x,y+10), QPoint(x-6,y+13), QPoint(x+6,y+19),
                   QPoint(x-6,y+25), QPoint(x+6,y+31), QPoint(x-6,y+37), QPoint(x,y+40), QPoint(x,y+50)]
        for i in range(1, len(pts)):
            p.drawLine(pts[i-1], pts[i])

    def _draw_ground(self, p, x, y):
        p.setPen(QPen(QColor("#888888"), 1))
        p.drawLine(x, y, x, y+10)
        p.drawLine(x-8, y+10, x+8, y+10)
        p.drawLine(x-5, y+14, x+5, y+14)
        p.drawLine(x-2, y+18, x+2, y+18)

    def paintEvent(self, event):
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QPolygon
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        
        w, h = self.width(), self.height()
        p.setBrush(QColor(5, 5, 10))
        p.drawRect(self.rect())
        
        # Grid
        p.setPen(QColor(20, 20, 30))
        for i in range(0, w, 40): p.drawLine(i, 0, i, h)
        for i in range(0, h, 40): p.drawLine(0, i, w, i)
        
        p.setPen(QColor(100, 130, 160))
        p.setFont(QFont("Courier New", 8, QFont.Bold))
        p.drawText(10, 15, "SIGNAL PATH SCHEMATIC")

        # Pulse effect
        glow = (math.sin(self._pulse) + 1) / 2
        pulse_pen = QPen(QColor(0, 255, 255, int(150 + 100 * glow)), 2)
        
        # X coordinates
        x_src, x_af, x_mcu = 30, 160, 300
        y_ph, y_co2, y_o2 = 60, 160, 260
        
        # --- pH CHANNEL ---
        self._draw_component(p, x_src, y_ph, "pH EL.", "#00e5ff")
        p.setPen(pulse_pen); p.drawLine(x_src+60, y_ph, x_af, y_ph)
        # Voltage reading 1
        p.setPen(QColor(0, 229, 255))
        p.drawText(x_src+65, y_ph-10, f"{self.signals['ph']:+.1f}mV")
        
        self._draw_component(p, x_af, y_ph, "BUF", "#69f0ae", True)
        p.setPen(QPen(QColor("#00ff00"), 1.5)); p.drawLine(x_af+40, y_ph, x_mcu, y_ph)
        # Conditioned voltage
        p.setPen(QColor(0, 255, 0))
        p.drawText(x_af+45, y_ph-10, f"{(self.signals['ph']/1000 + 1.25):.3f}V")
        
        # --- pCO2 CHANNEL ---
        self._draw_component(p, x_src, y_co2, "CO2 EL.", "#00e5ff")
        p.setPen(QPen(QColor("#00e5ff"), 1)); p.drawLine(x_src+60, y_co2, x_src+90, y_co2)
        # Voltage reading 2
        p.setPen(QColor(0, 229, 255))
        p.drawText(x_src+65, y_co2-10, f"{self.signals['pCO2']:+.1f}mV")
        
        self._draw_resistor(p, x_src+90, y_co2)
        p.setPen(pulse_pen); p.drawLine(x_src+140, y_co2, x_af, y_co2)
        self._draw_component(p, x_af, y_co2, "BUF", "#69f0ae", True)
        p.setPen(QPen(QColor("#00ff00"), 1.5)); p.drawLine(x_af+40, y_co2, x_mcu, y_co2)
        # Conditioned voltage
        p.setPen(QColor(0, 255, 0))
        p.drawText(x_af+45, y_co2-10, f"{(self.signals['pCO2']/1000 + 1.25):.3f}V")

        # --- pO2 CHANNEL ---
        self._draw_component(p, x_src, y_o2, "O2 CAT.", "#ff9100")
        p.setPen(QPen(QColor("#ff9100"), 1)); p.drawLine(x_src+60, y_o2, x_af, y_o2)
        # Current reading
        p.setPen(QColor(255, 145, 0))
        p.drawText(x_src+65, y_o2-10, f"{self.signals['pO2']:.2f}nA")
        
        self._draw_component(p, x_af, y_o2, "TIA", "#ffccbc", True)
        p.setPen(QPen(QColor("#00ff00"), 1.5)); p.drawLine(x_af+40, y_o2, x_mcu, y_o2)
        # Conditioned voltage
        p.setPen(QColor(0, 255, 0))
        p.drawText(x_af+45, y_o2-10, f"{(self.signals['pO2'] * 0.05):.3f}V")
        
        # MCU Visualization
        p.setPen(QPen(QColor("#ffcc00"), 3))
        p.setBrush(QColor(10, 10, 10))
        p.drawRect(x_mcu, 40, 80, 280)
        p.setPen(QColor(255, 255, 255))
        p.setFont(QFont("Consolas", 7, QFont.Bold))
        p.drawText(x_mcu+5, 35, "ADC / μC")
        
        # Pin labels
        for i, lbl in enumerate(["A0", "A1", "A2"]):
            p.drawText(x_mcu+5, y_ph + i*100 + 5, lbl)

        p.end()


# ─────────────────────────────────────────────
#  GAUGE WIDGET
# ─────────────────────────────────────────────
class GaugeWidget(QWidget):
    def __init__(self, label, unit, lo, hi, normal_lo, normal_hi,
                 color_normal="#00c853", color_low="#2979ff", color_high="#ff1744",
                 parent=None):
        super().__init__(parent)
        self.label = label
        self.unit = unit
        self.lo = lo
        self.hi = hi
        self.normal_lo = normal_lo
        self.normal_hi = normal_hi
        self.color_normal = QColor(color_normal)
        self.color_low = QColor(color_low)
        self.color_high = QColor(color_high)
        self.value = (lo + hi) / 2
        self.setFixedSize(150, 150)

    def set_value(self, v):
        self.value = max(self.lo, min(self.hi, v))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2 + 10
        r = min(w, h) // 2 - 14

        # Background circle
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(12, 18, 35))
        p.drawEllipse(cx - r - 4, cy - r - 4, 2*r + 8, 2*r + 8)

        # Arc range: 210° to -30° (240° sweep)
        start_angle = 210
        span = 240

        # Normal zone arc (green)
        norm_start = start_angle - span * (self.normal_lo - self.lo) / (self.hi - self.lo)
        norm_span = -span * (self.normal_hi - self.normal_lo) / (self.hi - self.lo)
        pen = QPen(QColor(0, 100, 50), 6)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawArc(cx - r, cy - r, 2*r, 2*r,
                  int(norm_start * 16), int(norm_span * 16))

        # Outer arc (gray track)
        pen = QPen(QColor(40, 55, 75), 5)
        p.setPen(pen)
        p.drawArc(cx - r, cy - r, 2*r, 2*r,
                  int(start_angle * 16), int(-span * 16))

        # Value arc
        frac = (self.value - self.lo) / (self.hi - self.lo)
        if self.value < self.normal_lo:
            color = self.color_low
        elif self.value > self.normal_hi:
            color = self.color_high
        else:
            color = self.color_normal

        pen = QPen(color, 7)
        p.setPen(pen)
        val_span = -span * frac
        p.drawArc(cx - r, cy - r, 2*r, 2*r,
                  int(start_angle * 16), int(val_span * 16))

        # Needle
        angle_deg = start_angle - span * frac
        angle_rad = math.radians(angle_deg)
        nx = cx + (r - 12) * math.cos(angle_rad)
        ny = cy - (r - 12) * math.sin(angle_rad)
        pen = QPen(QColor(255, 255, 255), 2)
        p.setPen(pen)
        p.drawLine(cx, cy, int(nx), int(ny))
        p.setBrush(QColor(255, 255, 255))
        p.setPen(Qt.NoPen)
        p.drawEllipse(cx - 4, cy - 4, 8, 8)

        # Value text
        p.setPen(color)
        p.setFont(QFont("Courier New", 13, QFont.Bold))
        val_str = f"{self.value:.2f}" if self.label == "pH" else f"{self.value:.1f}"
        fm = p.fontMetrics()
        text_width = fm.horizontalAdvance(val_str)
        p.drawText(cx - text_width//2, cy + r - 20, val_str)

        # Label + unit
        p.setPen(QColor(160, 190, 210))
        p.setFont(QFont("Courier New", 8))
        lbl = f"{self.label} ({self.unit})"
        text_width = fm.horizontalAdvance(lbl)
        p.drawText(cx - text_width//2 + 5, cy - r + 14, lbl)

        p.end()


# ─────────────────────────────────────────────
#  CLINICAL CALCULATIONS
# ─────────────────────────────────────────────
def henderson_hasselbalch_HCO3(pH, pCO2):
    """Calculate HCO3- from Henderson-Hasselbalch equation."""
    if pCO2 <= 0:
        return 24.0
    HCO3 = 0.0307 * pCO2 * (10 ** (pH - 6.1))
    return round(HCO3, 1)


def calculate_SaO2(pO2_mmHg):
    """Oxygen-haemoglobin dissociation curve (Hill equation)."""
    if pO2_mmHg <= 0:
        return 0.0
    P50 = 26.8
    n = 2.7
    SaO2 = 100.0 * (pO2_mmHg ** n) / (pO2_mmHg ** n + P50 ** n)
    return round(min(100, SaO2), 1)


# ─────────────────────────────────────────────
#  ANALYSIS THREAD
# ─────────────────────────────────────────────
class AnalysisThread(QThread):
    progress_updated = pyqtSignal(int, str)
    result_ready = pyqtSignal(dict)

    def __init__(self, pH, pCO2, pO2, temperature=37.0):
        super().__init__()
        self.pH = pH
        self.pCO2 = pCO2
        self.pO2 = pO2
        self.temperature = temperature
        self.electrodes = ElectrodeModels(temperature)

    def run(self):
        steps = [
            (5,  "Initializing sensors..."),
            (10, "Aspirating blood sample..."),
            (20, "Calibrating pH electrode..."),
            (30, "Measuring pH (Nernst potential)..."),
            (40, "Measuring pCO₂ (Severinghaus principle)..."),
            (50, "Measuring pO₂ (Clark electrode)..."),
            (60, "Temperature correction at 37°C..."),
            (70, "Computing HCO₃⁻..."),
            (80, "Calculating SaO₂..."),
            (90, "Quality control checks..."),
            (100, "Analysis complete ✓"),
        ]
        
        for pct, msg in steps:
            time.sleep(0.1)  # Reduced for faster response
            self.progress_updated.emit(pct, msg)

        pH_measured = self.pH + random.gauss(0, 0.002)
        pCO2_measured = self.pCO2 + random.gauss(0, 0.2)
        pO2_measured = self.pO2 + random.gauss(0, 0.3)
        
        HCO3 = henderson_hasselbalch_HCO3(pH_measured, pCO2_measured)
        SaO2 = calculate_SaO2(pO2_measured)
        
        v_ph = self.electrodes.nernst_pH(pH_measured, add_noise=True)
        v_pco2 = self.electrodes.severinghaus_pCO2(pCO2_measured, add_noise=True)
        i_po2 = self.electrodes.clark_pO2(pO2_measured, flow_rate=1.0, add_noise=True)

        result = {
            "pH": round(pH_measured, 3),
            "pCO2": round(pCO2_measured, 1),
            "pO2": round(pO2_measured, 1),
            "HCO3": round(HCO3, 1),
            "SaO2": round(SaO2, 1),
            "v_ph": round(v_ph, 2),
            "v_pco2": round(v_pco2, 2),
            "i_po2": round(i_po2, 3)
        }
        
        self.result_ready.emit(result)


# ─────────────────────────────────────────────
#  MAIN WINDOW
# ─────────────────────────────────────────────
class ABGAnalyzer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ABG Analyzer Simulation — SBE3220 Medical Equipment II")
        self.setMinimumSize(1300, 900)
        self._apply_dark_theme()
        self._tick = 0
        self.electrodes = ElectrodeModels(temperature_celsius=37.0)
        self.current_results = None
        self.analysis_thread = None
        self._waveform_timer = QTimer()
        self._waveform_timer.timeout.connect(self._tick_waveforms)
        self._build_ui()
        self._waveform_timer.start(50)  # 20 fps - CRITICAL for waveforms!

    def _apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #0a0f1e; color: #cce0f0; }
            QGroupBox {
                border: 2px solid #1e3a5f;
                border-radius: 8px;
                margin-top: 14px;
                padding: 10px;
                font-weight: bold;
                color: #7ab8e8;
                font-size: 11px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QSlider::groove:horizontal {
                height: 8px; background: #1a2a40; border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #00aaff; width: 18px; height: 18px;
                margin: -5px 0; border-radius: 9px;
            }
            QSlider::sub-page:horizontal { background: #0066cc; border-radius: 4px; }
            QPushButton {
                background-color: #003366;
                color: #aad4ff;
                border: 2px solid #0055aa;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #0044aa; }
            QPushButton#analyze_btn {
                background-color: #006633;
                color: #aaffcc;
                border: 2px solid #00aa55;
                font-size: 13px;
                padding: 12px 30px;
            }
            QPushButton#analyze_btn:hover { background-color: #008844; }
            QComboBox {
                background-color: #0d1b2e; border: 2px solid #1e3a5f;
                border-radius: 5px; padding: 5px; color: #aad4ff;
            }
            QProgressBar {
                background-color: #0d1b2e; border: 2px solid #1e3a5f;
                border-radius: 5px; text-align: center; color: #aaffcc;
                height: 20px;
            }
            QProgressBar::chunk { background-color: #007744; border-radius: 5px; }
            QTextEdit {
                background-color: #050c1a; border: 2px solid #1e3a5f;
                border-radius: 5px; font-family: 'Courier New'; font-size: 11px;
                color: #aad4ff; padding: 8px;
            }
        """)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(8)
        root.setContentsMargins(15, 10, 15, 10)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("⬢ ABG ANALYZER 5000")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #40aaff;")
        sub = QLabel("Arterial Blood Gas Analysis System | SBE3220")
        sub.setStyleSheet("font-size: 10px; color: #5588aa;")
        
        self.temp_label = QLabel("🌡️ 37.0°C")
        self.temp_label.setStyleSheet("color: #ffaa00; font-weight: bold;")
        
        hdr.addWidget(title)
        hdr.addStretch()
        hdr.addWidget(self.temp_label)
        hdr.addSpacing(20)
        hdr.addWidget(sub)
        root.addLayout(hdr)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #1e3a5f; height: 2px;")
        root.addWidget(sep)

        # Main splitter
        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter, 1)

        # LEFT PANEL
        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setSpacing(10)

        # Preset selector
        preset_grp = QGroupBox("🩸 Clinical Presets")
        preset_lay = QVBoxLayout(preset_grp)
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(PRESETS.keys()))
        self.preset_combo.currentTextChanged.connect(self._load_preset)
        preset_lay.addWidget(self.preset_combo)
        
        self.preset_info = QLabel("Select a clinical scenario")
        self.preset_info.setStyleSheet("color: #888; font-style: italic;")
        preset_lay.addWidget(self.preset_info)
        left_lay.addWidget(preset_grp)

        # Sliders
        slider_grp = QGroupBox("🔬 Manual Parameter Control")
        sg = QGridLayout(slider_grp)

        self.sl_pH = QSlider(Qt.Horizontal)
        self.sl_pH.setRange(680, 780)
        self.sl_pH.setValue(740)
        
        self.sl_pCO2 = QSlider(Qt.Horizontal)
        self.sl_pCO2.setRange(150, 800)
        self.sl_pCO2.setValue(400)
        
        self.sl_pO2 = QSlider(Qt.Horizontal)
        self.sl_pO2.setRange(200, 1400)
        self.sl_pO2.setValue(950)

        self.lbl_pH = QLabel("7.40")
        self.lbl_pCO2 = QLabel("40.0")
        self.lbl_pO2 = QLabel("95.0")
        
        for lbl in [self.lbl_pH, self.lbl_pCO2, self.lbl_pO2]:
            lbl.setStyleSheet("font-family: 'Courier New'; font-size: 12px; color: #00e5ff; background-color: #0d1b2e; padding: 4px; border-radius: 4px;")
            lbl.setFixedWidth(60)
            lbl.setAlignment(Qt.AlignCenter)

        self.sl_pH.valueChanged.connect(
            lambda v: self.lbl_pH.setText(f"{v/100:.2f}"))
        self.sl_pCO2.valueChanged.connect(
            lambda v: self.lbl_pCO2.setText(f"{v/10:.1f}"))
        self.sl_pO2.valueChanged.connect(
            lambda v: self.lbl_pO2.setText(f"{v/10:.1f}"))

        sg.addWidget(QLabel("pH"), 0, 0)
        sg.addWidget(self.sl_pH, 0, 1)
        sg.addWidget(self.lbl_pH, 0, 2)
        sg.addWidget(QLabel("pCO₂ (mmHg)"), 1, 0)
        sg.addWidget(self.sl_pCO2, 1, 1)
        sg.addWidget(self.lbl_pCO2, 1, 2)
        sg.addWidget(QLabel("pO₂ (mmHg)"), 2, 0)
        sg.addWidget(self.sl_pO2, 2, 1)
        sg.addWidget(self.lbl_pO2, 2, 2)

        left_lay.addWidget(slider_grp)

        # Temperature control
        temp_grp = QGroupBox("🌡️ Temperature Settings")
        temp_lay = QHBoxLayout(temp_grp)
        self.temp_slider = QSlider(Qt.Horizontal)
        self.temp_slider.setRange(320, 410)
        self.temp_slider.setValue(370)
        self.temp_slider.setTickInterval(10)
        self.temp_slider.setTickPosition(QSlider.TicksBelow)
        self.temp_value = QLabel("37.0°C")
        self.temp_value.setStyleSheet("font-family: 'Courier New'; font-size: 12px; color: #00e5ff; background-color: #0d1b2e; padding: 4px; border-radius: 4px;")
        self.temp_value.setFixedWidth(60)
        self.temp_value.setAlignment(Qt.AlignCenter)
        
        self.temp_slider.valueChanged.connect(self._update_temperature)
        
        temp_lay.addWidget(QLabel("Patient Temp:"))
        temp_lay.addWidget(self.temp_slider)
        temp_lay.addWidget(self.temp_value)
        left_lay.addWidget(temp_grp)

        # Buttons - Only analyze button
        btn_layout = QHBoxLayout()
        self.analyze_btn = QPushButton("▶ ANALYZE SAMPLE")
        self.analyze_btn.setObjectName("analyze_btn")
        self.analyze_btn.clicked.connect(self._start_analysis)
        
        btn_layout.addWidget(self.analyze_btn)
        left_lay.addLayout(btn_layout)

        # Progress
        prog_grp = QGroupBox("⚙ Analysis Progress")
        pg = QVBoxLayout(prog_grp)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.status_lbl = QLabel("Ready — load a sample and press Analyze")
        self.status_lbl.setStyleSheet("color:#5588aa; font-size:10px;")
        pg.addWidget(self.progress_bar)
        pg.addWidget(self.status_lbl)
        left_lay.addWidget(prog_grp)

        # Electrode signals
        sig_grp = QGroupBox("⚡ Electrode Signals (Raw)")
        sig_layout = QGridLayout(sig_grp)
        
        self.lbl_nernst = QLabel("pH: --.-- mV")
        self.lbl_sev = QLabel("pCO₂: --.-- mV")
        self.lbl_clark = QLabel("pO₂: --.--- nA")
        
        self.lbl_ph_principle = QLabel("Nernst: E = E₀ + (RT/nF)ln[H⁺]")
        self.lbl_pco2_principle = QLabel("Severinghaus: CO₂ + H₂O ⇌ H₂CO₃ ⇌ H⁺ + HCO₃⁻")
        self.lbl_po2_principle = QLabel("Clark: O₂ + 4e⁻ + 2H₂O → 4OH⁻")
        
        for w in [self.lbl_ph_principle, self.lbl_pco2_principle, self.lbl_po2_principle]:
            w.setStyleSheet("font-size:9px; color:#5588aa; font-family:'Courier New';")
        
        row = 0
        sig_layout.addWidget(QLabel("pH Electrode:"), row, 0)
        sig_layout.addWidget(self.lbl_nernst, row, 1)
        sig_layout.addWidget(self.lbl_ph_principle, row, 2)
        
        row += 1
        sig_layout.addWidget(QLabel("pCO₂ Electrode:"), row, 0)
        sig_layout.addWidget(self.lbl_sev, row, 1)
        sig_layout.addWidget(self.lbl_pco2_principle, row, 2)
        
        row += 1
        sig_layout.addWidget(QLabel("pO₂ Electrode:"), row, 0)
        sig_layout.addWidget(self.lbl_clark, row, 1)
        sig_layout.addWidget(self.lbl_po2_principle, row, 2)
        
        left_lay.addWidget(sig_grp)
        left_lay.addStretch()
        splitter.addWidget(left)

        # CENTER PANEL - WITH WAVEFORMS
        mid = QWidget()
        mid_lay = QVBoxLayout(mid)
        mid_lay.setSpacing(10)

        # Gauges
        gauge_grp = QGroupBox("📊 Measured Parameters")
        gauge_lay = QHBoxLayout(gauge_grp)
        self.gauge_pH = GaugeWidget("pH", "", 6.8, 7.8, 7.35, 7.45)
        self.gauge_pCO2 = GaugeWidget("pCO₂", "mmHg", 15, 80, 35, 45)
        self.gauge_pO2 = GaugeWidget("pO₂", "mmHg", 20, 140, 80, 100, color_low="#ff6d00")
        self.gauge_HCO3 = GaugeWidget("HCO₃⁻", "mEq/L", 10, 40, 22, 26)
        
        for g in [self.gauge_pH, self.gauge_pCO2, self.gauge_pO2, self.gauge_HCO3]:
            gauge_lay.addWidget(g)
        mid_lay.addWidget(gauge_grp)

        # WAVEFORMS - CRITICAL SECTION
        wave_grp = QGroupBox("〰 Real-Time Electrode Signals")
        wave_lay = QVBoxLayout(wave_grp)
        
        # Create waveform widgets with appropriate ranges
        self.wave_pH = WaveformWidget("pH Electrode", "#00e5ff", "mV", (-80, 20))
        self.wave_pCO2 = WaveformWidget("pCO₂ Electrode", "#69f0ae", "mV", (-80, 20))
        self.wave_pO2 = WaveformWidget("pO₂ Electrode", "#ff9100", "nA", (0, 15))
        
        wave_lay.addWidget(self.wave_pH)
        wave_lay.addWidget(self.wave_pCO2)
        wave_lay.addWidget(self.wave_pO2)
        mid_lay.addWidget(wave_grp, 1)

        # CIRCUIT PANEL
        circuit_grp = QGroupBox("🛰️ Hardware Interface Schematic")
        circuit_lay = QVBoxLayout(circuit_grp)
        self.circuit_view = CircuitWidget()
        circuit_lay.addWidget(self.circuit_view)
        
        splitter.addWidget(mid)
        splitter.addWidget(circuit_grp)

        # RIGHT PANEL - Simplified with just a placeholder
        right = QWidget()
        right_lay = QVBoxLayout(right)

        # Info about popup results
        info_grp = QGroupBox("ℹ️ Analysis Results")
        info_lay = QVBoxLayout(info_grp)
        
        info_label = QLabel("Results will appear in a\nseparate popup window\nafter analysis completes.")
        info_label.setStyleSheet("font-size: 14px; color: #7ab8e8; padding: 20px;")
        info_label.setAlignment(Qt.AlignCenter)
        info_lay.addWidget(info_label)
        
        # Add a note about the popup
        note_label = QLabel("Click 'ANALYZE SAMPLE' to begin")
        note_label.setStyleSheet("font-size: 12px; color: #00e5ff; font-style: italic;")
        note_label.setAlignment(Qt.AlignCenter)
        info_lay.addWidget(note_label)
        
        right_lay.addWidget(info_grp)
        
        # Add some spacing
        right_lay.addStretch()

        splitter.addWidget(right)
        splitter.setSizes([350, 550, 350])

        # Reference ranges
        ref_grp = QGroupBox("📖 Normal Reference Ranges")
        ref_lay = QHBoxLayout(ref_grp)
        refs = [
            ("pH", "7.35 – 7.45"),
            ("pCO₂", "35 – 45 mmHg"),
            ("pO₂", "80 – 100 mmHg"),
            ("HCO₃⁻", "22 – 26 mEq/L"),
            ("SaO₂", "95 – 100 %"),
            ("Base Excess", "-2 to +2 mEq/L"),
        ]
        for name, val in refs:
            box = QWidget()
            bl = QVBoxLayout(box)
            bl.setSpacing(2)
            n = QLabel(name)
            n.setStyleSheet("font-size:10px; color:#5588aa;")
            v = QLabel(val)
            v.setStyleSheet("font-family:'Courier New'; font-size:11px; color:#00c853; font-weight:bold;")
            bl.addWidget(n, 0, Qt.AlignCenter)
            bl.addWidget(v, 0, Qt.AlignCenter)
            ref_lay.addWidget(box)
        root.addWidget(ref_grp)

    def _update_temperature(self, value):
        temp = value / 10.0
        self.temp_value.setText(f"{temp:.1f}°C")
        self.temp_label.setText(f"🌡️ {temp:.1f}°C")
        self.electrodes.set_temperature(temp)

    def _load_preset(self, name):
        p = PRESETS[name]
        self.sl_pH.setValue(int(p["pH"] * 100))
        self.sl_pCO2.setValue(int(p["pCO2"] * 10))
        self.sl_pO2.setValue(int(p["pO2"] * 10))
        
        descriptions = {
            "Normal": "Healthy adult, room air",
            "Respiratory Acidosis": "Hypoventilation, COPD",
            "Respiratory Alkalosis": "Hyperventilation, anxiety",
            "Metabolic Acidosis": "DKA, renal failure",
            "Metabolic Alkalosis": "Vomiting, diuretics",
            "Mixed Resp+Met Acidosis": "Cardiac arrest, sepsis",
            "ARDS / Hypoxemia": "Severe lung injury",
        }
        self.preset_info.setText(descriptions.get(name, ""))

    def _tick_waveforms(self):
        """Update waveform displays - CRITICAL for real-time display"""
        self._tick += 1
        
        # Get current values from sliders
        pH = self.sl_pH.value() / 100
        pCO2 = self.sl_pCO2.value() / 10
        pO2 = self.sl_pO2.value() / 10
        
        # Get electrode signals with noise
        v_pH = self.electrodes.nernst_pH(pH, add_noise=True)
        v_pCO2 = self.electrodes.severinghaus_pCO2(pCO2, add_noise=True)
        i_pO2 = self.electrodes.clark_pO2(pO2, flow_rate=1.0, add_noise=True)
        
        # Push to waveforms
        self.wave_pH.push(v_pH)
        self.wave_pCO2.push(v_pCO2)
        self.wave_pO2.push(i_pO2)
        
        # Update circuit view
        self.circuit_view.update_signals({
            "ph": v_pH, "pCO2": v_pCO2, "pO2": i_pO2, "temp": self.temp_slider.value()/10.0
        })

        # Update signal labels
        self.lbl_nernst.setText(f"pH: {v_pH:+.2f} mV")
        self.lbl_sev.setText(f"pCO₂: {v_pCO2:+.2f} mV")
        self.lbl_clark.setText(f"pO₂: {i_pO2:.3f} nA")

    def _start_analysis(self):
        pH = self.sl_pH.value() / 100
        pCO2 = self.sl_pCO2.value() / 10
        pO2 = self.sl_pO2.value() / 10
        temp = self.temp_slider.value() / 10.0

        self.analyze_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_lbl.setText("Starting analysis...")

        # Create and start the analysis thread
        self.analysis_thread = AnalysisThread(pH, pCO2, pO2, temp)
        self.analysis_thread.progress_updated.connect(self._on_progress)
        self.analysis_thread.result_ready.connect(self._on_result)
        self.analysis_thread.finished.connect(self._on_analysis_finished)
        self.analysis_thread.start()

    def _on_progress(self, pct, msg):
        self.progress_bar.setValue(pct)
        self.status_lbl.setText(msg)
        # Force UI update
        QApplication.processEvents()

    def _on_result(self, res):
        """Handle analysis results - show popup window"""
        print("Results received, showing popup...")  # Debug print
        self.current_results = res

        # Update gauges in main window
        self.gauge_pH.set_value(res["pH"])
        self.gauge_pCO2.set_value(res["pCO2"])
        self.gauge_pO2.set_value(res["pO2"])
        self.gauge_HCO3.set_value(res["HCO3"])

        # Update electrode signals
        if "v_ph" in res:
            self.lbl_nernst.setText(f"pH: {res['v_ph']:+.2f} mV")
        if "v_pco2" in res:
            self.lbl_sev.setText(f"pCO₂: {res['v_pco2']:+.2f} mV")
        if "i_po2" in res:
            self.lbl_clark.setText(f"pO₂: {res['i_po2']:.3f} nA")

        self.status_lbl.setText("Analysis complete! Opening results...")

        # Show results in popup window
        self.show_results_popup(res)

    def show_results_popup(self, results):
        """Create and show the results popup window"""
        popup = ResultsPopup(results, self)
        popup.exec_()  # This makes it modal - user must close it before returning to main window

    def _on_analysis_finished(self):
        """Called when analysis thread finishes"""
        self.analyze_btn.setEnabled(True)
        self.analysis_thread = None


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 9))
    app.setStyle('Fusion')
    
    win = ABGAnalyzer()
    win.show()
    
    sys.exit(app.exec_())