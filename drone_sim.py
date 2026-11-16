"""
Эмулятор дрона Tello для учебного GUI-пульта.

Генерирует синтетический видеопоток и эмулирует команды
(взлёт, посадка, движение, повороты). Работает без физического дрона.

Используется как fallback, если реальный дрон недоступен.
"""
import time
import threading
import numpy as np
import cv2


class DroneSim:
    """Эмулятор дрона Tello."""

    def __init__(self):
        self._flying = False
        self._streaming = False
        self._frame = None
        self._lock = threading.Lock()
        self._thread = None
        self._battery = 100
        self._height = 0
        # Положение "дрона" в виртуальном мире — для визуализации
        self._pos = np.array([0.0, 0.0, 1.0])  # x, y, z
        self._yaw = 0.0
        self._last_tick = time.time()

    # --- Управление полётом ---
    def takeoff(self):
        if not self._flying:
            self._flying = True
            self._height = 80  # см
            self._pos[2] = 1.0
            print("[SIM] Взлёт выполнен")

    def land(self):
        if self._flying:
            self._flying = False
            self._height = 0
            self._pos[2] = 0.05
            print("[SIM] Посадка выполнена")

    def emergency(self):
        self._flying = False
        self._height = 0
        self._pos[2] = 0.05
        print("[SIM] Аварийная остановка")

    def move_forward(self, cm):
        if self._flying:
            self._pos[0] += cm / 100.0 * np.cos(np.radians(self._yaw))
            self._pos[1] += cm / 100.0 * np.sin(np.radians(self._yaw))
            print(f"[SIM] Вперёд на {cm} см")

    def move_back(self, cm):
        self.move_forward(-cm)

    def move_left(self, cm):
        if self._flying:
            self._pos[0] -= cm / 100.0 * np.sin(np.radians(self._yaw))
            self._pos[1] += cm / 100.0 * np.cos(np.radians(self._yaw))
            print(f"[SIM] Влево на {cm} см")

    def move_right(self, cm):
        self.move_left(-cm)

    def move_up(self, cm):
        if self._flying:
            self._pos[2] += cm / 100.0
            self._height += cm
            print(f"[SIM] Вверх на {cm} см")

    def move_down(self, cm):
        self.move_up(-cm)

    def rotate_clockwise(self, deg):
        if self._flying:
            self._yaw = (self._yaw + deg) % 360
            print(f"[SIM] Поворот по часовой на {deg}°")

    def rotate_counter_clockwise(self, deg):
        self.rotate_clockwise(-deg)

    # --- Телеметрия ---
    def get_battery(self):
        # Медленно убывает, чтобы был "живой" интерфейс
        self._battery = max(0, self._battery - 0.05)
        return int(self._battery)

    def get_height(self):
        return self._height

    # --- Видеопоток ---
    def streamon(self):
        if self._streaming:
            return
        self._streaming = True
        self._thread = threading.Thread(target=self._render_loop, daemon=True)
        self._thread.start()
        print("[SIM] Видеопоток включён")

    def streamoff(self):
        self._streaming = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        print("[SIM] Видеопоток выключен")

    def get_frame(self):
        with self._lock:
            if self._frame is None:
                return self._render_frame()
            return self._frame.copy()

    def _render_loop(self):
        while self._streaming:
            frame = self._render_frame()
            with self._lock:
                self._frame = frame
            time.sleep(1.0 / 30.0)

    def _render_frame(self):
        """Рисует синтетический кадр 640x480 с прицелом и телеметрией."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # "Небо" сверху, "земля" снизу — грубая имитация горизонта
        frame[:240, :] = (40, 20, 10)        # небо — тёмно-синее (BGR)
        frame[240:, :] = (30, 50, 20)        # земля — тёмно-зелёная

        # Линии перспективы
        for i in range(-10, 11):
            x_offset = i * 60
            cv2.line(
                frame,
                (320 + x_offset // 4, 240),
                (320 + x_offset, 480),
                (60, 80, 40),
                1,
            )

        # Прицел в центре
        cx, cy = 320, 240
        cv2.line(frame, (cx - 40, cy), (cx - 10, cy), (0, 255, 0), 2)
        cv2.line(frame, (cx + 10, cy), (cx + 40, cy), (0, 255, 0), 2)
        cv2.line(frame, (cx, cy - 40), (cx, cy - 10), (0, 255, 0), 2)
        cv2.line(frame, (cx, cy + 10), (cx, cy + 40), (0, 255, 0), 2)
        cv2.circle(frame, (cx, cy), 3, (0, 255, 0), -1)

        # Телеметрия
        status = "FLYING" if self._flying else "LANDED"
        color = (0, 255, 0) if self._flying else (0, 0, 255)
        cv2.putText(frame, f"STATUS: {status}", (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(frame, f"BATTERY: {int(self._battery)}%", (20, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(frame, f"HEIGHT: {self._height} cm", (20, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(frame, f"YAW: {self._yaw:.0f} deg", (20, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        # Положение "дрона" на мини-карте
        mini = np.zeros((100, 100, 3), dtype=np.uint8)
        mini[:] = (20, 20, 20)
        # Робот в центре
        cv2.circle(mini, (50, 50), 4, (0, 255, 0), -1)
        # Направление
        dx = int(30 * np.sin(np.radians(self._yaw)))
        dy = int(-30 * np.cos(np.radians(self._yaw)))
        cv2.line(mini, (50, 50), (50 + dx, 50 + dy), (0, 255, 0), 2)
        frame[360:460, 520:620] = mini

        # Время
        cv2.putText(frame, time.strftime("%H:%M:%S"), (540, 470),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        return frame
