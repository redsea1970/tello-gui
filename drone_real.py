"""
Обёртка над djitellopy для реального дрона Tello.

Полностью повторяет интерфейс DroneSim, поэтому GUI-приложение
не знает, с каким объектом работает — с эмулятором или с реальным дроном.
"""
import threading


class DroneReal:
    """Обёртка над djitellopy.Tello с тем же интерфейсом, что у DroneSim."""

    def __init__(self):
        # Импорт внутри — если djitellopy нет (или дрон недоступен),
        # падаем только при попытке создать объект.
        from djitellopy import Tello
        self._tello = Tello()
        self._flying = False
        self._streaming = False

    def connect(self):
        self._tello.connect()

    def takeoff(self):
        self._tello.takeoff()
        self._flying = True

    def land(self):
        self._tello.land()
        self._flying = False

    def emergency(self):
        self._tello.emergency()

    def move_forward(self, cm):
        self._tello.move_forward(cm)

    def move_back(self, cm):
        self._tello.move_back(cm)

    def move_left(self, cm):
        self._tello.move_left(cm)

    def move_right(self, cm):
        self._tello.move_right(cm)

    def move_up(self, cm):
        self._tello.move_up(cm)

    def move_down(self, cm):
        self._tello.move_down(cm)

    def rotate_clockwise(self, deg):
        self._tello.rotate_clockwise(deg)

    def rotate_counter_clockwise(self, deg):
        self._tello.rotate_counter_clockwise(deg)

    def get_battery(self):
        return self._tello.get_battery()

    def get_height(self):
        return self._tello.get_height()

    def streamon(self):
        self._tello.streamon()
        self._streaming = True

    def streamoff(self):
        self._tello.streamoff()
        self._streaming = False

    def get_frame(self):
        return self._tello.get_frame_read().frame
