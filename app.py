"""
Учебный GUI-пульт управления дроном Tello.

Pet-project по робототехнике. Работает в двух режимах:
1. Симуляция — без физического дрона (по умолчанию).
2. Реальный Tello — если дрон доступен по Wi-Fi.

Основа: учебное пособие ТГТУ «Программирование БПЛА» (Практические 2, 3).
"""
import sys
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QTimer

import cv2
import numpy as np


# Импортируем оба "бэкенда"
from drone_sim import DroneSim

try:
    from drone_real import DroneReal
    REAL_AVAILABLE = True
except Exception:
    REAL_AVAILABLE = False


class TelloGUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Учебный пульт управления Tello")
        self.resize(900, 700)

        # --- Выбор режима ---
        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItem("Симуляция (без дрона)")
        if REAL_AVAILABLE:
            self.mode_combo.addItem("Реальный Tello")
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)

        # --- Видео ---
        self.video_label = QtWidgets.QLabel("Нажмите «Подключить»")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet("background-color: #111; color: #eee;")

        # --- Кнопки ---
        self.btn_connect = QtWidgets.QPushButton("Подключить")
        self.btn_takeoff = QtWidgets.QPushButton("Взлёт")
        self.btn_land = QtWidgets.QPushButton("Посадка")
        self.btn_emergency = QtWidgets.QPushButton("Аварийная остановка")
        self.btn_connect.clicked.connect(self._on_connect)
        self.btn_takeoff.clicked.connect(self._on_takeoff)
        self.btn_land.clicked.connect(self._on_land)
        self.btn_emergency.clicked.connect(self._on_emergency)

        # --- Управление движением ---
        self.btn_fwd = QtWidgets.QPushButton("↑ Вперёд")
        self.btn_back = QtWidgets.QPushButton("↓ Назад")
        self.btn_left = QtWidgets.QPushButton("← Влево")
        self.btn_right = QtWidgets.QPushButton("→ Вправо")
        self.btn_up = QtWidgets.QPushButton("Вверх")
        self.btn_down = QtWidgets.QPushButton("Вниз")
        self.btn_rot_cw = QtWidgets.QPushButton("Поворот ↻")
        self.btn_rot_ccw = QtWidgets.QPushButton("Поворот ↺")

        for btn, cmd in [
            (self.btn_fwd,   lambda: self.drone.move_forward(20)),
            (self.btn_back,  lambda: self.drone.move_back(20)),
            (self.btn_left,  lambda: self.drone.move_left(20)),
            (self.btn_right, lambda: self.drone.move_right(20)),
            (self.btn_up,    lambda: self.drone.move_up(20)),
            (self.btn_down,  lambda: self.drone.move_down(20)),
            (self.btn_rot_cw,  lambda: self.drone.rotate_clockwise(20)),
            (self.btn_rot_ccw, lambda: self.drone.rotate_counter_clockwise(20)),
        ]:
            btn.clicked.connect(cmd)

        # --- Индикаторы ---
        self.lbl_battery = QtWidgets.QLabel("Батарея: —")
        self.lbl_height = QtWidgets.QLabel("Высота: —")
        self.lbl_status = QtWidgets.QLabel("Статус: ожидание")

        # --- Таймер для обновления кадра и телеметрии ---
        self.frame_timer = QTimer()
        self.frame_timer.timeout.connect(self._update_frame)
        self.frame_timer.setInterval(33)  # ~30 FPS

        self.telemetry_timer = QTimer()
        self.telemetry_timer.timeout.connect(self._update_telemetry)
        self.telemetry_timer.setInterval(1000)

        # --- Сборка layout ---
        self._build_layout()

        # --- Бэкенд ---
        self.drone = None
        self._on_mode_changed(0)

    # ---------------- UI ----------------
    def _build_layout(self):
        # Верхняя панель
        top = QtWidgets.QHBoxLayout()
        top.addWidget(QtWidgets.QLabel("Режим:"))
        top.addWidget(self.mode_combo)
        top.addStretch()
        top.addWidget(self.lbl_battery)
        top.addWidget(self.lbl_height)
        top.addWidget(self.lbl_status)

        # Панель управления полётом
        flight = QtWidgets.QHBoxLayout()
        flight.addWidget(self.btn_connect)
        flight.addWidget(self.btn_takeoff)
        flight.addWidget(self.btn_land)
        flight.addWidget(self.btn_emergency)

        # Панель движения
        move = QtWidgets.QGridLayout()
        move.addWidget(self.btn_fwd, 0, 1)
        move.addWidget(self.btn_left, 1, 0)
        move.addWidget(self.btn_right, 1, 2)
        move.addWidget(self.btn_back, 2, 1)
        move.addWidget(self.btn_up, 0, 3)
        move.addWidget(self.btn_down, 2, 3)
        move.addWidget(self.btn_rot_cw, 1, 3)
        move.addWidget(self.btn_rot_ccw, 1, 4)

        # Основной layout
        central = QtWidgets.QWidget()
        root = QtWidgets.QVBoxLayout(central)
        root.addLayout(top)
        root.addWidget(self.video_label, stretch=1)
        root.addLayout(flight)
        root.addLayout(move)
        self.setCentralWidget(central)

    # ---------------- Режимы ----------------
    def _on_mode_changed(self, idx):
        if idx == 0:
            self.drone = DroneSim()
        else:
            self.drone = DroneReal()
        self.lbl_status.setText("Статус: готов к подключению")

    # ---------------- Слоты кнопок ----------------
    def _on_connect(self):
        try:
            if hasattr(self.drone, "connect"):
                self.drone.connect()
            self.drone.streamon()
            self.frame_timer.start()
            self.telemetry_timer.start()
            self.lbl_status.setText("Статус: подключено")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", str(e))

    def _on_takeoff(self):
        try:
            self.drone.takeoff()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", str(e))

    def _on_land(self):
        try:
            self.drone.land()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", str(e))

    def _on_emergency(self):
        try:
            self.drone.emergency()
            self.frame_timer.stop()
            self.telemetry_timer.stop()
            self.lbl_status.setText("Статус: аварийная остановка")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", str(e))

    # ---------------- Кадр и телеметрия ----------------
    def _update_frame(self):
        if self.drone is None:
            return
        try:
            frame = self.drone.get_frame()
        except Exception:
            return
        if frame is None:
            return

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        qt_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_img).scaled(
            self.video_label.width(), self.video_label.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.video_label.setPixmap(pixmap)

    def _update_telemetry(self):
        if self.drone is None:
            return
        try:
            battery = self.drone.get_battery()
            height = self.drone.get_height()
            self.lbl_battery.setText(f"Батарея: {battery}%")
            self.lbl_height.setText(f"Высота: {height} см")
        except Exception:
            pass

    def closeEvent(self, event):
        try:
            if self.drone is not None:
                self.drone.streamoff()
                self.drone.land()
        except Exception:
            pass
        event.accept()


def main():
    app = QtWidgets.QApplication(sys.argv)
    w = TelloGUI()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
