import json
import os
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from PyQt6.QtCore import QPointF
from core.services.toast.toast import MsgToast

from core.view.canvas_view import EtatGraphicsObject
from .base_mode_controller import BaseModeController
from core.model.states_model import StatesModel
from core.config.app_config import AppConfig

class StatesController(BaseModeController):
    def __init__(self, canvas, palette):
        super().__init__(canvas)
        self.palette = palette
        self.model = StatesModel()
        # Connexions palette
        self.palette.resetRequested.connect(self.reset_states)
        self.palette.loadRequested.connect(self.load_states)
        self.palette.saveRequested.connect(self.save_states)
        # Connexion canvas → palette
        self.canvas.stateDropped.connect(self.on_state_dropped)
        # Mise à jour initiale de la palette
        self.update_palette()

    def set_state_blocks_right_click(self, enabled: bool):
        """Active ou désactive le clic droit sur tous les blocs états du canvas."""
        for item in self.canvas.scene.items():
            if isinstance(item, EtatGraphicsObject):
                item.set_right_click_enabled(enabled)

    def update_canvas_reference(self):
        pass

    def get_drawn_state_codes(self):
        """Retourne la liste des codes des états déjà dessinés sur le canvas."""
        codes = set()
        for item in self.canvas.scene.items():
            if isinstance(item, EtatGraphicsObject):
                codes.add(item.code)
        return codes

    def update_palette(self):
        """Met à jour la palette avec la différence entre la liste de départ et les états dessinés."""
        all_states = self.model.all()
        drawn_codes = self.get_drawn_state_codes()
        # Filtrer les états non dessinés
        non_drawn_states = [etat for etat in all_states if etat.code not in drawn_codes]
        self.palette.fill_etat_list(non_drawn_states)

    def on_state_dropped(self, code, label, pos):
        
        """Slot appelé quand un état est déposé sur le canvas."""
        etat = self.model.get_by_code(code)

        if etat:
            from core.view.canvas_view import EtatGraphicsObject
            w = self.canvas.viewport().width()
            h = self.canvas.viewport().height()
            scale_x = w / AppConfig.REFERENCE_CANVAS_WIDTH if w > 0 else 1
            scale_y = h / AppConfig.REFERENCE_CANVAS_HEIGHT if h > 0 else 1
            item = EtatGraphicsObject(code, label, etat.w, etat.h)
            item.width = int(etat.w * scale_x)
            item.height = int(etat.h * scale_y)
            item.x = int(etat.x * scale_x - AppConfig.LEFT_MENU_WIDTH )
            item.y = int(etat.y * scale_y)
         
            item.setPos(pos)
            item.deleteRequested.connect(self.on_state_delete_requested)
            self.canvas.scene.addItem(item)
        self.update_palette()
        
    def on_resize_states(self, w, h):
        """
        Redimensionne le canvas et ses items.
        - Scale Qt pour l'affichage
        - Met à jour les positions/logiques x/y
        """
        
        if w <= 0 or h <= 0:
            return

        # Facteurs de scale par rapport à la taille de référence
        scale_x = w / AppConfig.REFERENCE_CANVAS_WIDTH
        scale_y = h / AppConfig.REFERENCE_CANVAS_HEIGHT

        # Réinitialiser toute transformation précédente
        self.canvas.resetTransform()
        # Appliquer scaling visuel Qt
        self.canvas.scale(scale_x, scale_y)

        # Mettre à jour les coordonnées logiques x/y de chaque item
        for item in self.canvas.scene.items():
            if isinstance(item, EtatGraphicsObject):
                # On part de la référence stockée
                #x_ref = getattr(item, "x_ref", item.pos().x())
                #y_ref = getattr(item, "y_ref", item.pos().y())

                #item.x = int(x_ref * scale_x)
                #item.y = int(y_ref * scale_y)

                # On peut synchroniser la position Qt si nécessaire
                #item.setPos(item.x, item.y)

                # Si tu veux ajuster width/height aussi
                item.width = int(getattr(item, "width_ref", item.width) * scale_x)
                item.height = int(getattr(item, "height_ref", item.height) * scale_y)
                item.handle_pos = QPointF(item.width - item.handle_size,
                                        item.height - item.handle_size)

                item.prepareGeometryChange()
                item.update()

        # Appliquer les effets interactifs (selection, handles…)
        self.canvas.apply_states_interactive()

        # Debug : contrôle des x, y
        #print(f"[DEBUG] Canvas scaled: scale_x={scale_x:.3f}, scale_y={scale_y:.3f}")
        #for item in self.canvas.scene.items():
        #    if isinstance(item, EtatGraphicsObject):
        #        print(f"Item {item.code}: x={item.x}, y={item.y}, w={item.width}, h={item.height}") 
        print(f"StatesController: on_resize_states")    

    # =========================
    # LOAD FROM DATA (sans FileDialog)
    # =========================
    def load_states_from_data(self, etats: list):
        """Charge les états depuis une liste de dicts (code, label, x, y, w, h)."""
        self.canvas.remove_all_state_blocks()
        for etat in etats:
            item = EtatGraphicsObject(
                etat["code"],
                etat["label"],
                etat["w"],
                etat["h"]
            )
            item.setPos(etat["x"], etat["y"])
            item.deleteRequested.connect(self.on_state_delete_requested)
            self.canvas.scene.addItem(item)
        self.canvas.apply_states_interactive()
        self.update_palette()

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

        self.canvas.remove_all_state_blocks()

        # Utiliser la taille courante du canvas pour un positionnement proportionnel
        w = self.canvas.viewport().width()
        h = self.canvas.viewport().height()
        scale_x = w / AppConfig.REFERENCE_CANVAS_WIDTH if w > 0 else 1
        scale_y = h / AppConfig.REFERENCE_CANVAS_HEIGHT if h > 0 else 1
        for etat in self.model.all():
            item = EtatGraphicsObject(
                etat.code,
                etat.label,
                etat.w,
                etat.h
            )
            item.setPos(
                etat.x,
                etat.y
            )
            item.deleteRequested.connect(self.on_state_delete_requested)
            self.canvas.scene.addItem(item)

        self.canvas.apply_states_interactive()
        self.update_palette()
        MsgToast.success("Reset", "Etats réinitialisés", parent=self.canvas.window())

    # =========================
    # LOAD
    # =========================
    def load_states(self):
        default_dir = os.path.join(os.path.dirname(__file__), '../data/etats')
        default_dir = os.path.abspath(default_dir)
        dialog = QFileDialog(self.palette, "Ouvrir états", default_dir)
        dialog.setNameFilter("JSON (*.json)")
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)

        if not dialog.exec():
            return

        file_path = dialog.selectedFiles()[0]

        with open(file_path, "r", encoding="utf-8") as f:
            etats = json.load(f)

        self.canvas.remove_all_state_blocks()

        for etat in etats:
            item = EtatGraphicsObject(
                etat["code"],
                etat["label"],
                etat["w"],
                etat["h"]
            )
            item.setPos(etat["x"], etat["y"])
            item.deleteRequested.connect(self.on_state_delete_requested)
            self.canvas.scene.addItem(item)
            
    def on_state_delete_requested(self, code):
        """Supprime le bloc état, toutes ses flèches connectées, et met à jour la palette."""
        from core.view.canvas_view import TransitionArrow

        for item in list(self.canvas.scene.items()):
            if isinstance(item, EtatGraphicsObject) and item.code == code:
                # Supprimer proprement toutes les flèches connectées à cet état
                for arrow in list(item.arrows):
                    try:
                        arrow._clear_handles()
                        # Désenregistrer la flèche depuis l'autre état
                        other = arrow.end_item if (arrow.start_item is item) else arrow.start_item
                        try:
                            if arrow in other.arrows:
                                other.arrows.remove(arrow)
                        except RuntimeError:
                            pass
                        if arrow.scene():
                            arrow.scene().removeItem(arrow)
                    except RuntimeError:
                        pass
                self.canvas.scene.removeItem(item)
                break
        self.update_palette()
        MsgToast.success("Suppression", f"État {code} supprimé.", parent=self.canvas.window())

    # =========================
    # SAVE
    # =========================
    def save_states(self):
        default_dir = os.path.join(os.path.dirname(__file__), '../data/etats')
        default_dir = os.path.abspath(default_dir)
        dialog = QFileDialog(self.palette, "Sauvegarder états", default_dir)
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

        MsgToast.success("Sauvegarde", "Etats sauvegardés", parent=self.canvas.window())

    def connect(self):
        print("States mode activated")
        self.update_palette()
        # Ne pas ouvrir de FileDialog automatiquement