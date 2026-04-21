"""
NewProjectDialog — Boîte de dialogue de création d'un nouveau projet GEMMA.

Collecte le nom (obligatoire) et une description libre (optionnelle)
avant de valider la création du projet.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)


class NewProjectDialog(QDialog):
    """Dialogue de création d'un nouveau projet GEMMA."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nouveau projet GEMMA")
        self.setMinimumWidth(380)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # ── Nom du projet ──────────────────────────────────────────────────
        layout.addWidget(QLabel("<b>Nom du projet</b> <small>(requis)</small>"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("ex : Mon_Automatisme")
        layout.addWidget(self._name_edit)

        # ── Description ────────────────────────────────────────────────────
        layout.addWidget(QLabel("<b>Description</b> <small>(optionnelle)</small>"))
        self._desc_edit = QTextEdit()
        self._desc_edit.setPlaceholderText("Décrivez brièvement le projet…")
        self._desc_edit.setFixedHeight(90)
        layout.addWidget(self._desc_edit)

        # ── Boutons OK / Annuler ───────────────────────────────────────────
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._ok_btn.setEnabled(False)
        self._name_edit.textChanged.connect(self._update_ok_btn)

    # ── Logique interne ────────────────────────────────────────────────────
    def _update_ok_btn(self, text: str):
        self._ok_btn.setEnabled(bool(text.strip()))

    def _on_accept(self):
        if self._name_edit.text().strip():
            self.accept()

    # ── Accesseurs publics ─────────────────────────────────────────────────
    def project_name(self) -> str:
        return self._name_edit.text().strip()

    def project_description(self) -> str:
        return self._desc_edit.toPlainText().strip()
