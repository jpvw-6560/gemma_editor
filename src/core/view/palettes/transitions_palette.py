from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
                              QFileDialog, QMessageBox, QListWidget,
                              QListWidgetItem, QMenu, QInputDialog, QFrame)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor
import os


class TransitionsPalette(QWidget):
    # Signaux pour actions à connecter dans le contrôleur
    resetRequested = pyqtSignal()
    openRequested = pyqtSignal(str)
    saveRequested = pyqtSignal(str)
    initBaseRequested = pyqtSignal()
    addTransitionRequested = pyqtSignal()
    validateRequested = pyqtSignal()
    simulateRequested = pyqtSignal()
    exportDiagramRequested = pyqtSignal()
    deleteTransitionRequested = pyqtSignal(str, str)   # (origine, destination)
    transitionSelected = pyqtSignal(str, str)           # (origine, destination)
    conditionEditRequested = pyqtSignal(str, str, str)  # (origine, destination, condition)
    questionnaireRequested = pyqtSignal()
    mettreAJourRequested      = pyqtSignal()
    sauvegarderFlechesRequested = pyqtSignal()


    def __init__(self, container=None):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(2, 8, 8, 8)   # marge gauche réduite
        layout.setSpacing(4)

        # Titre
        title = QLabel("Transitions")
        title.setStyleSheet("font-weight: bold; font-size: 16px; margin-bottom: 6px;")
        layout.addWidget(title)

        # Bouton toggle de tri
        self.sort_mode = "origin"
        self.btn_sort = QPushButton("Trier")
        self.btn_sort.setToolTip("Alterner le tri par origine/destination")
        self.btn_sort.clicked.connect(self.toggle_sort_mode)
        layout.addWidget(self.btn_sort)

        # Liste des transitions
        self.transitions_list = QListWidget()
        self.transitions_list.setMinimumHeight(240)
        self.transitions_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.transitions_list.customContextMenuRequested.connect(self._on_list_context_menu)
        self.transitions_list.itemClicked.connect(self._on_item_clicked)
        self.transitions_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.transitions_list)

        # Bouton questionnaire en tête
        btn_questionnaire = QPushButton("🔎 Questionnaire GEMMA")
        btn_questionnaire.setToolTip(
            "Arbre de décision : répondez aux questions pour\n"
            "déterminer les états et transitions GEMMA à utiliser."
        )
        btn_questionnaire.clicked.connect(self.questionnaireRequested.emit)
        layout.addWidget(btn_questionnaire)

        for label, tooltip, slot in [
            ("Réinitialiser",  "Supprime toutes les transitions (confirmation)",                       self._on_reset),
            ("+Transition",    "Ajouter une transition entre deux états",                              self._on_add_transition),
            ("Initialiser",    "Insère les transitions\nles plus courantes\npour démarrer rapidement",  self._on_init_base),
            ("Ouvrir…",        "Ouvrir un fichier de transitions",                                     self._on_open),
            ("Enregistrer…",   "Enregistrer les transitions",                                          self._on_save),
        ]:
            btn = QPushButton(label)
            btn.setToolTip(tooltip)
            btn.clicked.connect(slot)
            btn.setVisible(False)
            layout.addWidget(btn)

        # Boutons réservés au développement/maintenance — cachés en production
        self.btn_mettre_a_jour = QPushButton("Mettre à jour")
        self.btn_mettre_a_jour.setToolTip("Charge les flèches depuis fleches.json\n(remplace les flèches existantes)")
        self.btn_mettre_a_jour.clicked.connect(self._on_mettre_a_jour)
        self.btn_mettre_a_jour.setVisible(False)
        layout.addWidget(self.btn_mettre_a_jour)

        self.btn_sauvegarder_fleches = QPushButton("Save → fleches.json")
        self.btn_sauvegarder_fleches.setToolTip("Sauvegarde les flèches actuelles\ndans fleches.json")
        self.btn_sauvegarder_fleches.clicked.connect(self._on_sauvegarder_fleches)
        self.btn_sauvegarder_fleches.setVisible(False)
        layout.addWidget(self.btn_sauvegarder_fleches)

        # Bouton Vérifier masqué (déplacé vers menu gauche Actions/Auditer)
        self.btn_verifier = QPushButton("Vérifier")
        self.btn_verifier.clicked.connect(self._on_validate)
        self.btn_verifier.setVisible(False)
        layout.addWidget(self.btn_verifier)

        layout.addStretch()
        self.setLayout(layout)

        # Répertoire transitions par défaut
        self.transitions_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data", "transitions"
        )

    def set_transitions_list(self, transitions):
        """Met à jour la liste. Chaque élément est (origin, end) ou (origin, end, condition)."""
        # Normaliser en triplets pour garantir la présence de la condition
        self._last_transitions = [
            (t[0], t[1], t[2] if len(t) > 2 else "") for t in transitions
        ]
        self.transitions_list.clear()
        if self.sort_mode == "origin":
            sorted_transitions = sorted(self._last_transitions, key=lambda t: (t[0], t[1]))
        else:
            sorted_transitions = sorted(self._last_transitions, key=lambda t: (t[1], t[0]))
        for origin, end, condition in sorted_transitions:
            text = f"{origin} → {end}"
            if condition:
                text += f"  [{condition}]"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, (origin, end, condition))
            self.transitions_list.addItem(item)

    def color_transitions_list(self, colors: dict):
        """
        Colorie les items de la liste après validation.
        colors : dict { (origin, end): str }  ex. { ("A1","A2"): "#ffcccc" }
        """
        white = QColor("#ffffff")
        for i in range(self.transitions_list.count()):
            item = self.transitions_list.item(i)
            data = item.data(Qt.ItemDataRole.UserRole)
            # UserRole est un triplet (origin, end, condition) — extraire la clé (origin, end)
            key = (data[0], data[1]) if data else None
            if key and key in colors:
                item.setBackground(QColor(colors[key]))
                item.setForeground(white)
            else:
                # Réinitialiser au style par défaut du widget
                item.setData(Qt.ItemDataRole.BackgroundRole, None)
                item.setData(Qt.ItemDataRole.ForegroundRole, None)

    def toggle_sort_mode(self):
        """Alterner le mode de tri et mettre à jour la liste."""
        if self.sort_mode == "origin":
            self.sort_mode = "destination"
            self.btn_sort.setText("Trier par origine")
        else:
            self.sort_mode = "origin"
            self.btn_sort.setText("Trier par destination")
        # Rafraîchir depuis la liste mémorisée (avec conditions)
        if getattr(self, '_last_transitions', None):
            self.set_transitions_list(self._last_transitions)

    def _on_item_clicked(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            self.transitionSelected.emit(data[0], data[1])

    def _on_item_double_clicked(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        origin, dest = data[0], data[1]
        current_cond = data[2] if len(data) > 2 else ""
        cond, ok = QInputDialog.getText(
            self, "Condition de transition",
            f"Condition de franchissement de  {origin} → {dest} :",
            text=current_cond
        )
        if ok:
            self.conditionEditRequested.emit(origin, dest, cond.strip())

    def _on_list_context_menu(self, pos):
        item = self.transitions_list.itemAt(pos)
        if item is None:
            return
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        origin, dest = data[0], data[1]
        menu = QMenu(self)
        action_del = menu.addAction(f"Supprimer  {origin} → {dest}")
        chosen = menu.exec(self.transitions_list.viewport().mapToGlobal(pos))
        if chosen is action_del:
            self.deleteTransitionRequested.emit(origin, dest)

    def _on_reset(self):
        reply = QMessageBox.question(self, "Confirmation", "Supprimer toutes les transitions ?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.resetRequested.emit()

    def _on_open(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Ouvrir transitions", self.transitions_dir, "*.json")
        if file_path:
            self.openRequested.emit(file_path)

    def _on_save(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Enregistrer transitions", self.transitions_dir, "*.json")
        if file_path:
            self.saveRequested.emit(file_path)

    def _on_init_base(self):
        self.initBaseRequested.emit()

    def _on_mettre_a_jour(self):
        self.mettreAJourRequested.emit()

    def _on_sauvegarder_fleches(self):
        self.sauvegarderFlechesRequested.emit()

    def _on_add_transition(self):
        self.addTransitionRequested.emit()
        pass

    def _on_validate(self):
        self.validateRequested.emit()

    def _on_simulate(self):
        self.simulateRequested.emit()

    def _on_export_diagram(self):
        self.exportDiagramRequested.emit()