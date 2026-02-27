from PyQt6.QtCore import Qt, QMimeData, QRectF, QUrl
from PyQt6.QtGui import QDrag, QColor, QBrush, QPainter, QCursor, QPixmap
from PyQt6.QtWidgets import (
    QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QMessageBox, QFileDialog
)

# Imports standards
import json
import os
# Imports gemma
from core.config.app_config import STATE_BLOCKS, AppConfig
from core.view.canvas_view import EtatGraphicsObject

# Toast messages
from core.services.toast.toast import MsgToast

class EtatListWidget(QListWidget):
    
    def mouseMoveEvent(self, event):

        if event.buttons() & Qt.MouseButton.LeftButton:
            self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
            pos = event.pos()
            item = self.itemAt(pos)
            if item:
                self.setCurrentItem(item)
                self.startDrag(Qt.DropAction.MoveAction)
        else:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        super().mouseMoveEvent(event)

    def startDrag(self, supportedActions):
        # print(f"Drag start: supportedActions={supportedActions}")
        pos = self.viewport().mapFromGlobal(self.cursor().pos())
        item = self.itemAt(pos)
        if item:
            # print(f"Drag start: {item.text()}")
            mime_data = QMimeData()
            code = item.data(Qt.ItemDataRole.UserRole)
            label = item.toolTip()
            mime_data.setText(f"{code}|{label}")
            drag = QDrag(self)
            drag.setMimeData(mime_data)
            # Création d'un rectangle blanc crème comme icône
            pixmap = QPixmap(60, 40)
            pixmap.fill(QColor(255, 250, 240))  # blanc crème
            painter = QPainter(pixmap)
            painter.setPen(QColor(180, 180, 180))
            painter.drawRect(0, 0, 59, 39)
            painter.end()
            drag.setPixmap(pixmap)
            # ...aucun curseur personnalisé pendant le drag...
            drag.exec(supportedActions)


class EtatsPalette(QWidget):
    def __init__(self, project=None, canvas=None):
        super().__init__()
        self.project = project
        self.canvas = canvas
        self.setup_ui()

    def setup_ui(self):    
        layout = QVBoxLayout()
        title = QLabel("Etats")
        title.setStyleSheet(
            "font-size: 18px; font-weight: bold; margin-top: 8px;"
        )
        layout.addWidget(title)

        title_liste = QLabel("Liste des états")
        title_liste.setStyleSheet(
            "font-size: 14px; font-weight: bold; margin-top: 8px; margin-left: 4px;"
        )
        layout.addWidget(title_liste)

        # =========================
        # Liste des états
        # =========================
        self.etat_list = EtatListWidget()
        self.etat_list.setDragEnabled(True)  # 🔥 indispensable
        self.etat_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.etat_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.etat_list.setMouseTracking(True)  # Pour le hover

        self.fill_etat_list()
        layout.addWidget(self.etat_list)
        
        self.setLayout(layout)

        # Connexions hover
        self.etat_list.itemEntered.connect(self.on_item_hover)
        self.etat_list.viewport().installEventFilter(self)

        # Ajout des boutons commandes
        #------------------------------- Menu des commandes -------------------------------
        btn_layout = QVBoxLayout()
        
        self.btn_reinit = QPushButton("Réinitialiser")
        self.btn_charger = QPushButton("Ouvrir")
        self.btn_sauvegarder = QPushButton("Enregistrer")
        
       
        btn_layout.addWidget(self.btn_reinit)
        btn_layout.addWidget(self.btn_charger)
        btn_layout.addWidget(self.btn_sauvegarder)
     
        layout.addLayout(btn_layout)

        layout.addStretch()
        #-----------------------------------------------------------------------------------
        # Connexion des boutons
       
        self.btn_reinit.clicked.connect(self.handle_reinit)
        self.btn_charger.clicked.connect(self.handle_charger)
        self.btn_sauvegarder.clicked.connect(self.handle_sauvegarder)

        # Connexion au canvas pour suppression après drop
        if canvas is not None:
            canvas.stateDropped.connect(self.remove_state_item)

    def handle_reset(self):
        
        reply = QMessageBox.question(self, "Confirmation", "Voulez-vous vraiment réinitialiser la liste et supprimer tous les états du canvas ?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            # Vider les blocs état du canvas
            if hasattr(self, 'canvas') and self.canvas is not None:
                scene = self.canvas.scene
                for item in list(scene.items()):
                    # Supprimer uniquement les objets EtatGraphicsObject
                    if type(item).__name__ == "EtatGraphicsObject":
                        scene.removeItem(item)
            self.etat_list.clear()
            self.fill_etat_list()

    def handle_reinit(self):
        reply = QMessageBox.question(self, "Confirmation", "Voulez-vous vraiment réinitialiser tous les états sur le canvas ?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            
            if self.canvas is not None:
                scene = self.canvas.scene
                for item in list(scene.items()):
                    if type(item).__name__ == "EtatGraphicsObject":
                        scene.removeItem(item)

                # Ajouter les états chargés
                codes_ajoutes = set()
                for etat in STATE_BLOCKS:
                    code = etat.get("code", "")
                    label = etat.get("label", "")
                    w = etat.get("w", 40)
                    h = etat.get("h", 30)
                    x = etat.get("x", 0)
                    y = etat.get("y", 0)
                    etat_item = EtatGraphicsObject(code, label, w, h)
                    etat_item.setPos(x, y)
                    scene.addItem(etat_item)
                    codes_ajoutes.add(code)
                # Mettre à jour la liste des états restants
                self.etat_list.clear()
                for block in STATE_BLOCKS:
                    code = block["code"]
                    label = block["label"]
                    if code not in codes_ajoutes:
                        item = QListWidgetItem(f"Etat {code}")
                        item.setData(Qt.ItemDataRole.UserRole, code)
                        item.setToolTip(label)
                        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                        item.setBackground(QBrush(Qt.GlobalColor.black))
                        item.setForeground(QBrush(Qt.GlobalColor.white))
                        self.etat_list.addItem(item)
                
                MsgToast.success("Chargement", f"Application chargée depuis app_config", parent=self.window())

    def handle_charger(self):
        if not self.canvas or not self.canvas.scene:
            print("Aucun canvas pour charger les états")
            MsgToast.error("Erreur", "Aucun canvas pour charger les états", parent=self.window())
            return

        # Dossier par défaut
        base_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
        data_dir = os.path.abspath(os.path.join(base_dir, "../../../data/etats"))

        dialog = QFileDialog(self)
        dialog.setWindowTitle("Charger des états")
        dialog.setDirectory(data_dir)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        dialog.setNameFilter("Fichiers JSON (*.json)")
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dialog.selectFile("etats.json")
        dialog.resize(600, 400)

        if dialog.exec():
            file_path = dialog.selectedFiles()[0]
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    etats = json.load(f)
            except Exception as e:
                print(f"Erreur lors du chargement : {e}")
                MsgToast.error("Erreur", f"Erreur lors du chargement : {e}", parent=self.window())
                return

            scene = self.canvas.scene
            # Nettoyer les états existants
            for item in list(scene.items()):
                if type(item).__name__ == "EtatGraphicsObject":
                    scene.removeItem(item)

            # Ajouter les états chargés
            codes_ajoutes = set()
            for etat in etats:
                code = etat.get("code", "")
                label = etat.get("label", "")
                w = etat.get("w", 40)
                h = etat.get("h", 30)
                x = etat.get("x", 0)
                y = etat.get("y", 0)
                etat_item = EtatGraphicsObject(code, label, w, h)
                etat_item.setPos(x, y)
                scene.addItem(etat_item)
                codes_ajoutes.add(code)
            # Mettre à jour la liste des états restants
            self.etat_list.clear()
            for block in STATE_BLOCKS:
                code = block["code"]
                label = block["label"]
                if code not in codes_ajoutes:
                    item = QListWidgetItem(f"Etat {code}")
                    item.setData(Qt.ItemDataRole.UserRole, code)
                    item.setToolTip(label)
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                    item.setBackground(QBrush(Qt.GlobalColor.black))
                    item.setForeground(QBrush(Qt.GlobalColor.white))
                    self.etat_list.addItem(item)
            print(f"Chargement terminé depuis {file_path}")
            MsgToast.success("Chargement", f"Chargement terminé", parent=self.window())

    def handle_sauvegarder(self):
        if not self.canvas or not self.canvas.scene:
            print("Aucune scène à sauvegarder")
            MsgToast.error("Erreur", "Aucune scène à sauvegarder", parent=self.window())
            return

        scene = self.canvas.scene
        etats = []

        for item in scene.items():
            if type(item).__name__ == "EtatGraphicsObject":
                pos = item.pos()  # mieux que sceneBoundingRect pour sauvegarder
                rect = item.boundingRect()

                etats.append({
                    "code": getattr(item, "code", ""),
                    "label": getattr(item, "label", ""),
                    "x": int(pos.x()),
                    "y": int(pos.y()),
                    "w": int(rect.width()),
                    "h": int(rect.height())
                })

        # ---- dossier sécurisé ----
        base_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
        data_dir = os.path.abspath(os.path.join(base_dir, "../../../data/etats"))
        os.makedirs(data_dir, exist_ok=True)  # évite crash si dossier absent

        # ---- boîte de dialogue ----
        dialog = QFileDialog(self)
        dialog.setWindowTitle("Enregistrer les états")
        dialog.setDirectory(data_dir)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dialog.setNameFilter("Fichiers JSON (*.json)")
        dialog.setDefaultSuffix("json")
        dialog.setFileMode(QFileDialog.FileMode.AnyFile)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dialog.selectFile("etats.json")
        dialog.resize(600, 400)


        if dialog.exec():
            file_path = dialog.selectedFiles()[0]

            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(etats, f, ensure_ascii=False, indent=2)

                # print(f"Sauvegarde terminée dans {file_path}")
                MsgToast.error("Sauvegarde", f"Sauvegarde terminée", parent=self.window())
            except Exception as e:
                print(f"Erreur de sauvegarde : {e}")
                MsgToast.error("Erreur", f"Erreur lors de la sauvegarde : {e}", parent=self.window())

    def handle_sauvegarder_en(self):
        print("sauvegarde dans dossier choisi")
        MsgToast.error("Sauvegarde", "Fonctionnalité non encore implémentée", parent=self.window())
        pass

    def fill_etat_list(self):
        self.etat_list.clear()
        for block in STATE_BLOCKS:
            code = block["code"]
            label = block["label"]
            item = QListWidgetItem(f"Etat {code}")
            item.setData(Qt.ItemDataRole.UserRole, code)
            item.setToolTip(label)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            item.setBackground(QBrush(Qt.GlobalColor.black))
            item.setForeground(QBrush(Qt.GlobalColor.white))
            self.etat_list.addItem(item)


    def remove_state_item(self, code):
        # Supprime l'item de la liste dont le code correspond
        for i in range(self.etat_list.count()):
            item = self.etat_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == code:
                self.etat_list.takeItem(i)
                break

    def on_item_hover(self, item):
        # Reset visuel de la liste
        self.reset_list_visuals()
        # Couleur sur item survolé
        item.setBackground(QBrush(Qt.GlobalColor.lightGray))
        item.setForeground(QBrush(Qt.GlobalColor.black))

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if obj == self.etat_list.viewport():
            if event.type() == QEvent.Type.Leave:
                self.reset_list_visuals()
        return super().eventFilter(obj, event)

    def reset_list_visuals(self):
        for i in range(self.etat_list.count()):
            item = self.etat_list.item(i)
            item.setBackground(QBrush(Qt.GlobalColor.black))
            item.setForeground(QBrush(Qt.GlobalColor.white))

    def refresh_states(self):
        self.etat_list.clear()
        if self.project and hasattr(self.project, 'states'):
            for state in self.project.states:
                item = QListWidgetItem(state.name)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsDragEnabled)
                self.etat_list.addItem(item)
