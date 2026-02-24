import os
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication, QGraphicsOpacityEffect
from PyQt6.QtGui import QFont
import simpleaudio as sa
from gemma.config.app_config import AppConfig


class MsgToast(QWidget):
    _current = None

    BG_COLORS = {
        "info": "#2d7deb",
        "success": "#32b43c",
        "warning": "#e5b432",
        "error": "#eb3232",
        "default": "#2d2d2d",
    }

    COLORS = {
        "info": "#ffffff",
        "success": "#000000",
        "warning": "#000000",
        "error": "#e5b432",
        "default": "#ffffff",
    }

    SOUNDS = {
        "info": "info.wav",
        "success": "success.wav",
        "warning": "warning.wav",
        "error": "error.wav",
    }

    # Préchargement des sons
    _loaded_sounds = {}

    def __init__(self, title, message, duration=3500, toast_type="default"):
        super().__init__(None)
        self.toast_type = toast_type
        self.duration = duration

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        message_label = QLabel(message)
        message_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(message_label)

        bg_color = self.BG_COLORS.get(toast_type, self.BG_COLORS["default"])
        color = self.COLORS.get(toast_type, self.COLORS["default"])
        self.setStyleSheet(f"""
            background-color: {bg_color};
            color: {color};
            border-radius: 8px;
            border: 1px solid {color};
            padding: 10px;
        """)

        self.adjustSize()
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0)

    def play_sound(self):
        if not AppConfig.TOAST_SON:
            return

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        sound_file = self.SOUNDS.get(self.toast_type)
        if not sound_file:
            return

        sound_path = os.path.join(BASE_DIR, sound_file)
        if not os.path.exists(sound_path):
            return

        # Précharger le son si ce n'est pas déjà fait
        if sound_path not in self._loaded_sounds:
            try:
                self._loaded_sounds[sound_path] = sa.WaveObject.from_wave_file(sound_path)
            except Exception:
                return

        wave_obj = self._loaded_sounds[sound_path]
        wave_obj.play()  # Jouer le son de manière non bloquante

    def show_toast(self):
        self.play_sound()

        screen = QApplication.instance().primaryScreen().availableGeometry()
        x = screen.right() - self.width() - 20
        y = screen.top() + 20
        self.move(x, y)
        self.show()

        self.fade_in()
        QTimer.singleShot(self.duration, self.fade_out)

    def fade_in(self):
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(250)
        self.anim.setStartValue(0)
        self.anim.setEndValue(1)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.start()

    def fade_out(self):
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(300)
        self.anim.setStartValue(1)
        self.anim.setEndValue(0)
        self.anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self.anim.finished.connect(self.close)
        self.anim.start()

    @classmethod
    def show_message(cls, title, message, duration=3500, toast_type="default"):
        if cls._current:
            cls._current.close()
        cls._current = MsgToast(title, message, duration, toast_type)
        cls._current.show_toast()

    @classmethod
    def info(cls, title, message, duration=3500):
        cls.show_message(title, message, duration, "info")

    @classmethod
    def success(cls, title, message, duration=3500):
        cls.show_message(title, message, duration, "success")

    @classmethod
    def warning(cls, title, message, duration=3500):
        cls.show_message(title, message, duration, "warning")

    @classmethod
    def error(cls, title, message, duration=3500):
        cls.show_message(title, message, duration, "error")