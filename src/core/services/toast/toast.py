import os
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QUrl
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication, QGraphicsOpacityEffect
from PyQt6.QtGui import QFont
from PyQt6.QtMultimedia import QSoundEffect
from core.config.app_config import AppConfig

class MsgToast(QWidget):
    _active_toasts = []
    BG_COLORS = {
        "info": "#2d7deb",
        "success": "#32b43c",
        "warning": "#e5b432",
        "error": "#eb3232",
        "default": "#2d2d2d"
    }
    COLORS = {
        "info": "#ffffff",
        "success": "#000000",
        "warning": "#000000",
        "error": "#ffffff",
        "default": "#ffffff"
    }
    SOUNDS = {
        "info": "info.wav",
        "success": "success.wav",
        "warning": "warning.wav",
        "error": "error.wav"
    }
    _loaded_sounds = {}

    def __init__(self, title, message, duration=2000, toast_type="default", parent=None):
        super().__init__(parent)  # parent = main_window ou None
        self.toast_type = toast_type
        self.duration = duration

        # Window flags adaptés pour Wayland
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        # Layout et labels
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(message_label)

        # Style selon le type de toast
        bg_color = self.BG_COLORS.get(toast_type, self.BG_COLORS["default"])
        color = self.COLORS.get(toast_type, self.COLORS["default"])
        self.setStyleSheet(
            f"background-color:{bg_color};color:{color};"
            f"border-radius:8px;border:1px solid {color};padding:10px;"
        )
        self.adjustSize()

        # Opacité pour fade in/out
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0)

        # Ajouter à la liste des toasts actifs
        MsgToast._active_toasts.append(self)
        

    def enterEvent(self, event):
        # Fige la tempo lors du hover
        if hasattr(self, '_hide_timer') and self._hide_timer.isActive():
            self._remaining = self._hide_timer.remainingTime()
            self._hide_timer.stop()
        event.accept()

    def leaveEvent(self, event):
        # Relance la tempo lors du leave
        if hasattr(self, '_remaining') and self._remaining > 0:
            self._hide_timer.start(self._remaining)
        event.accept()
    

    # --- Sons ---
    def _load_sound(self):
        path = os.path.join(os.path.dirname(__file__), self.SOUNDS.get(self.toast_type, ""))
        if not os.path.exists(path):
            return None
        if path in self._loaded_sounds:
            return self._loaded_sounds[path]
        effect = QSoundEffect()
        effect.setSource(QUrl.fromLocalFile(path))
        effect.setVolume(0.5)
        self._loaded_sounds[path] = effect
        return effect

    def play_sound(self):
        if not AppConfig.TOAST_SON:
            return
        effect = self._load_sound()
        if effect:
            effect.play()

    # --- Affichage ---
    def show_toast(self, x_offset=20, y_offset=20):
        self.play_sound()

        # Calcul position en haut à droite
        if self.parent():  # placement relatif à la fenêtre principale
            parent = self.parentWidget() or self.window()
            parent_geom = parent.geometry()
            x = parent_geom.right() - self.width() - x_offset
            y = parent_geom.top() + y_offset + sum(t.height() + 10 for t in MsgToast._active_toasts if t is not self)
        else:  # fallback si pas de parent
            screen = QApplication.instance().primaryScreen()
            geom = screen.geometry()
            x = geom.right() - self.width() - x_offset
            y = geom.top() + y_offset + sum(t.height() + 10 for t in MsgToast._active_toasts if t is not self)

        self.move(int(x), int(y))
        self.show()
        self.fade_in()
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.fade_out)
        self._hide_timer.start(self.duration)

    # --- Animations ---
    def fade_in(self):
        self.anim_in = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_in.setDuration(250)
        self.anim_in.setStartValue(0)
        self.anim_in.setEndValue(1)
        self.anim_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim_in.start()

    def fade_out(self):
        self.anim_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_out.setDuration(300)
        self.anim_out.setStartValue(1)
        self.anim_out.setEndValue(0)
        self.anim_out.finished.connect(self._on_close)
        self.anim_out.start()

    def _on_close(self):
        self.close()
        if self in MsgToast._active_toasts:
            MsgToast._active_toasts.remove(self)

    # --- Class methods pratiques ---
    @classmethod
    def info(cls, title, message, duration=2000 , parent=None):
        t = cls(title, message, duration, "info", parent)
        t.show_toast()
        return t

    @classmethod
    def success(cls, title, message, duration=2000, parent=None):
        t = cls(title, message, duration, "success", parent)
        t.show_toast()
        return t

    @classmethod
    def warning(cls, title, message, duration=2000, parent=None):
        t = cls(title, message, duration, "warning", parent)
        t.show_toast()
        return t

    @classmethod
    def error(cls, title, message, duration=2000, parent=None):
        t = cls(title, message, duration, "error", parent)
        t.show_toast()
        return t