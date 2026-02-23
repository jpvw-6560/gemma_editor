import os, json
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import QPropertyAnimation
from PyQt6.QtWidgets import (   QMainWindow, 
                                QWidget, 
                                QVBoxLayout, 
                                QHBoxLayout, 
                                QPushButton, 
                                QLabel, 
                                QGroupBox, 
                                QFileDialog, 
                                QMessageBox,
                                QDialog, 
                                QGraphicsOpacityEffect
                            )
from gemma.ui_qt.canvas.canvas_view import EtatGraphicsObject
from gemma.ui_qt.canvas.canvas_view import CanvasView
from gemma.ui_qt.presenters.canvas_presenter import CanvasPresenter
from gemma.ui_qt.right_menu import RightMenu

from gemma.infrastructure.router import Router
from gemma.infrastructure.routes import register_routes

# Palettes
from gemma.ui_qt.palettes.layout_palette import LayoutPalette
from gemma.ui_qt.palettes.etats_palette import EtatsPalette
from gemma.ui_qt.palettes.transitions_palette import TransitionsPalette

# Controllers
from gemma.ui_qt.controllers.layout_controller import LayoutController
from gemma.ui_qt.controllers.etats_controller import EtatsController
from gemma.ui_qt.controllers.transitions_controller import TransitionsController

from gemma.config.app_config import AppConfig

class MainWindow(QMainWindow):
            
        
    def __init__(self, container):
        super().__init__()
        self.setWindowTitle("GEMMA Editor")
        self.resize(1100, 650)
        self.app_name = "<Aucune application>"
        self.get_mode = None
        # Canvas central
        self.canvas = CanvasView()
        self.presenter = CanvasPresenter(self.canvas.scene, container.event_bus)


        # Initialisation du router
        self.router = Router()
        register_routes(self.router, self.canvas)

        # Chargement automatique de la dernière application utilisée
        

        # LeftMenu  dynamique
        self.left_menu = QWidget()
        self.left_menu.setFixedWidth(AppConfig.LEFT_MENU_WIDTH)
        left_layout = QVBoxLayout()
        self.left_menu.setLayout(left_layout)

        # RightMenu dynamique
        self.right_menu = RightMenu()
 

        # Titre principal
        title_label = QLabel("Gemma doctor")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 12px;")
        left_layout.addWidget(title_label)

        # Groupe Application : Charger/Sauvegarder
        app_group = QGroupBox("Application")
        app_layout = QVBoxLayout()

        self.app_courante = QLabel(f"[{self.app_name}]")
        self.app_courante.setStyleSheet("font-size: 13px; font-style: italic; margin-bottom: 8px; margin-left: 8px;")

        btn_app_charger = QPushButton("Charger")
        btn_app_sauvegarder = QPushButton("Sauvegarder")

        app_layout.addWidget(self.app_courante)
        app_layout.addWidget(btn_app_charger)
        app_layout.addWidget(btn_app_sauvegarder)
        app_group.setLayout(app_layout)

    
        

        left_layout.addWidget(app_group)
        
        # Container 'Gemma' avec boutons
        gemma_group = QGroupBox("Gemma")
        gemma_layout = QVBoxLayout()

        btn_layout = QPushButton("Layout")
        btn_etats = QPushButton("Etats")
        btn_transitions = QPushButton("Transitions")

        def activate_mode(mode):
            self.router.navigate(mode, container, self.right_menu)
            self.set_etats_editable(mode == "etats")
            # self.left_menu.setEnabled(mode == "layout")
            # Les commandes spécifiques
            if mode == "layout":
                pass
            elif mode == "etats":
                pass
            elif mode == "transitions":
                pass

        # État initial : tout inhibé
        self.left_menu.setEnabled(True)
        self.set_etats_editable(False)

        btn_layout.clicked.connect(lambda: activate_mode("layout"))
        btn_etats.clicked.connect(lambda: activate_mode("etats"))
        btn_transitions.clicked.connect(lambda: activate_mode("transitions"))
        btn_app_charger.clicked.connect(self.handle_charger_app)
        btn_app_sauvegarder.clicked.connect(self.sauvegarder_application)
        
        gemma_layout.addWidget(btn_layout)
        gemma_layout.addWidget(btn_etats)
        gemma_layout.addWidget(btn_transitions)

        gemma_group.setLayout(gemma_layout)
        left_layout.addWidget(gemma_group)

        # Container 'Actions' avec boutons
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout()
        btn_auditer = QPushButton("Auditer")
        btn_generer = QPushButton("Générer")
        actions_layout.addWidget(btn_auditer)
        actions_layout.addWidget(btn_generer)
        actions_group.setLayout(actions_layout)
        left_layout.addWidget(actions_group)

        left_layout.addStretch()

        # Layout principal
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.left_menu)
        main_layout.addWidget(self.canvas, 1)  # Canvas prend tout l'espace restant
        main_layout.addWidget(self.right_menu)

        wrapper = QWidget()
        wrapper.setLayout(main_layout)
        self.setCentralWidget(wrapper)
        self.charger_derniere_application() 

     
    def show_toast(self, message, timeout=2000):
        parent = self.centralWidget() or self

        toast = QLabel(message, parent)
        toast.setAlignment(Qt.AlignmentFlag.AlignCenter)
        toast.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        toast.setStyleSheet("""
            QLabel {
                background-color: rgba(40, 40, 40, 230);
                color: white;
                padding: 10px 20px;
                border-radius: 12px;
                font-size: 13px;
            }
        """)

        toast.adjustSize()

        # Limite largeur
        max_width = int(parent.width() * 0.6)
        if toast.width() > max_width:
            toast.setWordWrap(True)
            toast.setFixedWidth(max_width)
            toast.adjustSize()

        # Position centre bas
        x = (parent.width() - toast.width()) // 2
        y = parent.height() - toast.height() - 60
        toast.move(x, y)

        # Effet opacité
        effect = QGraphicsOpacityEffect(toast)
        toast.setGraphicsEffect(effect)

        toast.fade_in = QPropertyAnimation(effect, b"opacity")
        toast.fade_in.setDuration(200)
        toast.fade_in.setStartValue(0)
        toast.fade_in.setEndValue(1)

        toast.fade_out = QPropertyAnimation(effect, b"opacity")
        toast.fade_out.setDuration(400)
        toast.fade_out.setStartValue(1)
        toast.fade_out.setEndValue(0)
        toast.fade_out.finished.connect(toast.deleteLater)

        toast.show()
        toast.raise_()
        toast.fade_in.start()

        QTimer.singleShot(timeout, toast.fade_out.start)


    def set_etats_editable(self, editable: bool):
            # Désactive ou active la modification des états sur le canvas
            for item in self.canvas.scene.items():
                if isinstance(item, EtatGraphicsObject):
                    flags = item.flags()
                    if editable:
                        item.setFlags(
                            flags | item.GraphicsItemFlag.ItemIsMovable | item.GraphicsItemFlag.ItemIsSelectable
                        )
                    else:
                        item.setFlags(
                            flags & ~item.GraphicsItemFlag.ItemIsMovable & ~item.GraphicsItemFlag.ItemIsSelectable
                        )

    def charger_derniere_application(self):
        
        settings_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../data/settings.json'))
        applis_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../data/applis_gemma'))
        last_app = None
        # print(f"MainWindow: settings_path={settings_path}")
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    # print("MainWindow: settings.json trouvé, lecture en cours...")
                    settings = json.load(f)
                    # print(f"MainWindow: settings loaded: {settings}")
                    last_app = settings.get('last_app', '').strip()
                    # print(f"MainWindow: last_app={last_app}")
            except (json.JSONDecodeError, OSError) as e:
                QMessageBox.critical(self, "Erreur",
                             f"Erreur lecture settings : {e}")
                return
        else:
            print("settings.json introuvable")
            return

        if last_app:
            file_path = os.path.join(applis_dir, last_app)
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        app_data = json.load(f)
                    # Nettoyer le canvas
                    for item in list(self.canvas.scene.items()):
                        if type(item).__name__ == "EtatGraphicsObject":
                            self.canvas.scene.removeItem(item)
                    # Ajouter les états
                    etats = app_data.get('etats', [])
                    for etat in etats:
                        code = etat.get("code", "")
                        label = etat.get("label", "")
                        w = etat.get("w", 40)
                        h = etat.get("h", 30)
                        x = etat.get("x", 0)
                        y = etat.get("y", 0)
                        etat_item = self.canvas.scene.addItem(
                            __import__('gemma.ui_qt.canvas.canvas_view', fromlist=['EtatGraphicsObject']).EtatGraphicsObject(code, label, w, h)
                        )
                        item = self.canvas.scene.items()[0]
                        item.setPos(x, y)
                    # TODO: Ajouter les transitions si besoin
                    # Mettre à jour l'affichage
                    self.app_name = os.path.splitext(os.path.basename(file_path))[0]
                    # print("type:", type(self.app_courante))
                    self.app_courante.setText(f" [{self.app_name}]")
                    self.show_toast(f"Application chargée : {file_path}")
                except Exception as e:
                    QMessageBox.critical(self, "Erreur", f"Erreur lors du chargement : {e}")
            else:
                QMessageBox.warning(self, "Fichier manquant", f"Le fichier de la dernière application n'existe pas : {file_path}")

    def sauvegarder_application(self):
        applis_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '../../../data/applis_gemma')
        )
        os.makedirs(applis_dir, exist_ok=True)

        dialog = QFileDialog(self)
        dialog.setWindowTitle("Sauvegarder l'application")
        dialog.setDirectory(applis_dir)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dialog.setNameFilter("Applications GEMMA (*.json)")
        dialog.setDefaultSuffix("json")
        dialog.setFileMode(QFileDialog.FileMode.AnyFile)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dialog.resize(600, 400)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        file_path = dialog.selectedFiles()[0]

        # Récupération des états
        etats = []
        for item in self.canvas.scene.items():
            if isinstance(item, EtatGraphicsObject):
                pos = item.pos()
                rect = item.boundingRect()

                etats.append({
                    "code": getattr(item, "code", ""),
                    "label": getattr(item, "label", ""),
                    "x": int(pos.x()),
                    "y": int(pos.y()),
                    "w": int(rect.width()),
                    "h": int(rect.height())
                })

        data = {"etats": etats, "transitions": []}

        try:
            # Sauvegarde application
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # Mise à jour settings
            settings_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), '../../../data/settings.json')
            )

            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(
                    {"last_app": os.path.basename(file_path)},
                    f,
                    ensure_ascii=False,
                    indent=2
                )

            # Mise à jour UI
            self.app_name = os.path.splitext(os.path.basename(file_path))[0]
            self.app_courante.setText(f" : [{self.app_name}]")

            self.show_toast(f"Application sauvegardée sous : {file_path}")

        except (OSError, json.JSONDecodeError) as e:
            QMessageBox.critical(
                self,
                "Erreur",
                f"Erreur lors de la sauvegarde : {e}"
            )
    
    # Connexion du bouton Charger avec gestion du cas sans application
    def handle_charger_app(self):
        applis_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../data/applis_gemma'))
        if not os.path.exists(applis_dir) or not any(f.endswith('.json') for f in os.listdir(applis_dir)):
            self.show_toast("Aucune application à charger.")
            return
        dialog = QFileDialog(self)
        dialog.setWindowTitle("Charger une application")
        dialog.setDirectory(applis_dir)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        dialog.setNameFilter("Applications GEMMA (*.json)")
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dialog.resize(600, 400)
        if dialog.exec():
            file_path = dialog.selectedFiles()[0]
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    app_data = json.load(f)
                # Nettoyer le canvas
                for item in list(self.canvas.scene.items()):
                    if type(item).__name__ == "EtatGraphicsObject":
                        self.canvas.scene.removeItem(item)
                # Ajouter les états
                etats = app_data.get('etats', [])
                for etat in etats:
                    code = etat.get("code", "")
                    label = etat.get("label", "")
                    w = etat.get("w", 40)
                    h = etat.get("h", 30)
                    x = etat.get("x", 0)
                    y = etat.get("y", 0)
                    etat_item = self.canvas.scene.addItem(
                        __import__('gemma.ui_qt.canvas.canvas_view', fromlist=['EtatGraphicsObject']).EtatGraphicsObject(code, label, w, h)
                    )
                    item = self.canvas.scene.items()[0]
                    item.setPos(x, y)
                # TODO: Ajouter les transitions si besoin
                # Mettre à jour settings.json
                settings_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../data/settings.json'))
                with open(settings_path, "w", encoding="utf-8") as f:
                    json.dump({"last_app": os.path.basename(file_path)}, f, ensure_ascii=False, indent=2)
                # Mettre à jour l'affichage
                self.app_name = os.path.splitext(os.path.basename(file_path))[0]
                self.app_courante.setText(f"[{self.app_name}]")
                self.show_toast(f"Application chargée : {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur lors du chargement : {e}")

   