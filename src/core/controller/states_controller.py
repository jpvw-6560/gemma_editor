import json
import os
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from core.services.toast.toast import MsgToast

from core.view.canvas_view import EtatGraphicsObject
from .base_mode_controller import BaseModeController
from core.model.states_model import StatesModel

class StatesController(BaseModeController):

    def __init__(self, canvas, palette):
        super().__init__(canvas)
        self.palette = palette
        self.model = StatesModel()

        # Connexion au signal resize du canvas
        self.canvas.resizeStatesRequested.connect(self.on_resize_states)

        # Connexions palette
        self.palette.resetRequested.connect(self.reset_states)
        self.palette.loadRequested.connect(self.load_states)
        self.palette.saveRequested.connect(self.save_states)

        # Connexion canvas → palette
        self.canvas.stateDropped.connect(self.palette.remove_state_item)

    def on_resize_states(self, w, h):
        self.canvas.remove_all_states()
        # Adapter dynamiquement la taille/position des états selon w/h
        for etat in self.model.all():
            from core.view.canvas_view import EtatGraphicsObject
            # Exemple de redimensionnement proportionnel (à adapter selon logique métier)
            scale_x = w / 1600 if w > 0 else 1
            scale_y = h / 900 if h > 0 else 1
            item = EtatGraphicsObject(
                etat.code,
                etat.label,
                int(getattr(etat, "w", 40) * scale_x),
                int(getattr(etat, "h", 30) * scale_y)
            )
            item.setPos(
                int(getattr(etat, "x", 0) * scale_x),
                int(getattr(etat, "y", 0) * scale_y)
            )
            self.canvas.scene.addItem(item)

    # =========================
    # RESET
    # =========================
    def reset_states(self):
        reply = QMessageBox.question(
            self.palette,
            "Confirmation",
            "Voulez-vous réinitialiser les états ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        self.canvas.remove_all_states()


        for etat in self.model.all():
            item = EtatGraphicsObject(
                etat.code,
                etat.label,
                getattr(etat, "w", 40),
                getattr(etat, "h", 30)
            )
            item.setPos(getattr(etat, "x", 0), getattr(etat, "y", 0))
            self.canvas.scene.addItem(item)

        self.palette.fill_etat_list(self.model.all())
        MsgToast.success("Reset", "Etats réinitialisés", parent=self.palette)

    # =========================
    # LOAD
    # =========================
    def load_states(self):
        dialog = QFileDialog(self.palette)
        dialog.setNameFilter("JSON (*.json)")
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)

        if not dialog.exec():
            return

        file_path = dialog.selectedFiles()[0]

        with open(file_path, "r", encoding="utf-8") as f:
            etats = json.load(f)

        self.canvas.remove_all_states()

        codes_ajoutes = set()

        for etat in etats:
            item = EtatGraphicsObject(
                etat["code"],
                etat["label"],
                etat["w"],
                etat["h"]
            )
            item.setPos(etat["x"], etat["y"])
            self.canvas.scene.addItem(item)
            codes_ajoutes.add(etat["code"])

        self.palette.fill_etat_list()

        for code in codes_ajoutes:
            self.palette.remove_state_item(code)

        MsgToast.success("Chargement", "Etats chargés", parent=self.palette)

    # =========================
    # SAVE
    # =========================
    def save_states(self):
        dialog = QFileDialog(self.palette)
        dialog.setNameFilter("JSON (*.json)")
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)

        if not dialog.exec():
            return

        file_path = dialog.selectedFiles()[0]

        etats = []

        for item in self.canvas.scene.items():
            if isinstance(item, EtatGraphicsObject):
                pos = item.pos()
                rect = item.boundingRect()
                etats.append({
                    "code": item.code,
                    "label": item.label,
                    "x": int(pos.x()),
                    "y": int(pos.y()),
                    "w": int(rect.width()),
                    "h": int(rect.height())
                })

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(etats, f, indent=2, ensure_ascii=False)

        MsgToast.success("Sauvegarde", "Etats sauvegardés", parent=self.palette)

    def connect(self):
        print("States mode activated")

        # Remplir la palette dans l'ordre normal
        self.palette.fill_etat_list(self.model.all())
        # Ne pas ouvrir de FileDialog automatiquement