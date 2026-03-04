from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton, QFileDialog, QMessageBox
from PyQt6.QtCore import pyqtSignal
import os


class TransitionsPalette(QWidget):
    # Signaux pour actions à connecter dans le contrôleur
    resetRequested = pyqtSignal()
    openRequested = pyqtSignal(str)
    saveRequested = pyqtSignal(str)
    initBaseRequested = pyqtSignal()
    addTransitionRequested = pyqtSignal()


    def __init__(self, container=None):
        super().__init__()
        layout = QVBoxLayout()

        # Titre
        title = QLabel("Transitions")
        title.setStyleSheet("font-weight: bold; font-size: 16px; margin-bottom: 10px;")
        layout.addWidget(title)

        # Bouton toggle de tri
        self.sort_mode = "origin"
        self.btn_sort = QPushButton("Trier")
        self.btn_sort.setToolTip("Alterner le tri par origine/destination")
        self.btn_sort.clicked.connect(self.toggle_sort_mode)
        layout.addWidget(self.btn_sort)

        # Liste des transitions
        from PyQt6.QtWidgets import QListWidget
        self.transitions_list = QListWidget()
        self.transitions_list.setFixedHeight(120)
        layout.addWidget(self.transitions_list)

        # Bouton Réinitialiser
        btn_reset = QPushButton("Réinitialiser")
        btn_reset.setToolTip("Supprime toutes les transitions (confirmation)")
        btn_reset.clicked.connect(self._on_reset)
        layout.addWidget(btn_reset)

        # Bouton +Transition
        btn_add_transition = QPushButton("+Transition")
        btn_add_transition.setToolTip("Ajouter une transition entre deux états")
        btn_add_transition.clicked.connect(self._on_add_transition)
        layout.addWidget(btn_add_transition)

        # Bouton Initialiser la base
        btn_init_base = QPushButton("Initialiser")
        btn_init_base.setToolTip("Insère les transitions \nles plus courantes \npour démarrer rapidement")
        btn_init_base.clicked.connect(self._on_init_base)
        layout.addWidget(btn_init_base)

        # Bouton Ouvrir
        btn_open = QPushButton("Ouvrir…")
        btn_open.setToolTip("Ouvrir un fichier de transitions")
        btn_open.clicked.connect(self._on_open)
        layout.addWidget(btn_open)

        # Bouton Enregistrer
        btn_save = QPushButton("Enregistrer…")
        btn_save.setToolTip("Enregistrer les transitions")
        btn_save.clicked.connect(self._on_save)
        layout.addWidget(btn_save)

        layout.addStretch()
        self.setLayout(layout)

        # Répertoire transitions par défaut
        self.transitions_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data", "transitions"
        )

    def set_transitions_list(self, transitions):
        """Met à jour la liste des transitions affichée dans la palette, triée selon le mode."""
        self.transitions_list.clear()
        if self.sort_mode == "origin":
            sorted_transitions = sorted(transitions, key=lambda t: (t[0], t[1]))
        else:
            sorted_transitions = sorted(transitions, key=lambda t: (t[1], t[0]))
        for t in sorted_transitions:
            self.transitions_list.addItem(f"{t[0]} → {t[1]}")

    def toggle_sort_mode(self):
        """Alterner le mode de tri et mettre à jour la liste."""
        if self.sort_mode == "origin":
            self.sort_mode = "destination"
            self.btn_sort.setText("Trier par origine")
        else:
            self.sort_mode = "origin"
            self.btn_sort.setText("Trier par destination")
        # Rafraîchir la liste si transitions déjà présentes
        if hasattr(self, 'transitions_list') and self.transitions_list.count() > 0:
            # Récupérer les transitions affichées
            transitions = [self.transitions_list.item(i).text().split(" → ") for i in range(self.transitions_list.count())]
            # Reconvertir en tuples
            transitions = [(t[0], t[1]) for t in transitions]
            self.set_transitions_list(transitions)

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

    def _on_add_transition(self):
        self.addTransitionRequested.emit()
        pass