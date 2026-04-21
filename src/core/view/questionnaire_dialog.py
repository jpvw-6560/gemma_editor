"""
QuestionnairDialog — Boîte de dialogue du questionnaire GEMMA.

Affiche les 13 questions de l'arbre de décision GEMMA, permet de répondre
Oui / Non / Sans-réponse à chacune, puis émet la liste des états résultants.
Les réponses sont persistées dans gemma_questionnaire.json.
"""

import json
import os
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# Chemin vers le JSON du questionnaire (relatif au répertoire de ce fichier)
_HERE = os.path.dirname(__file__)
QUESTIONNAIRE_JSON = os.path.normpath(
    os.path.join(_HERE, "..", "data", "gemma_questionnaire.json")
)


# ===========================================================
# Widget d'une ligne-question (Oui / Non / ?)
# ===========================================================
class QuestionRow(QWidget):
    """
    Affiche une question avec trois boutons radio simulés : Oui | Non | ?
    L'état courant est stocké en tant que True / False / None.
    """

    def __init__(self, question_data: dict, parent=None):
        super().__init__(parent)
        self._data = question_data
        self._answer: Optional[bool] = question_data.get("reponse")  # None | True | False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(8)

        # Numéro + titre
        num_label = QLabel(f"<b>{question_data['id']}.</b>")
        num_label.setFixedWidth(22)
        layout.addWidget(num_label)

        # Texte de la question
        self.q_label = QLabel(question_data["question"])
        self.q_label.setWordWrap(True)
        self.q_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.q_label, stretch=1)

        # Conditions typiques (tooltip)
        if question_data.get("conditions"):
            self.q_label.setToolTip(
                "Conditions typiques : " + ", ".join(question_data["conditions"])
            )

        # États produits
        etats_oui = question_data.get("etats_si_oui", [])
        etats_label = QLabel(f"→ {', '.join(etats_oui)}" if etats_oui else "")
        etats_label.setFixedWidth(130)
        etats_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(etats_label)

        # Boutons Oui / Non / ?
        self.btn_oui = QPushButton("Oui")
        self.btn_non = QPushButton("Non")
        self.btn_nc  = QPushButton("?")

        for btn in (self.btn_oui, self.btn_non, self.btn_nc):
            btn.setFixedWidth(44)
            btn.setCheckable(False)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_oui.clicked.connect(lambda: self._set_answer(True))
        self.btn_non.clicked.connect(lambda: self._set_answer(False))
        self.btn_nc.clicked.connect(lambda: self._set_answer(None))

        layout.addWidget(self.btn_oui)
        layout.addWidget(self.btn_non)
        layout.addWidget(self.btn_nc)

        self._refresh_buttons()

    # ----------------------------------------------------------
    def _set_answer(self, value: Optional[bool]):
        self._answer = value
        self._refresh_buttons()

    def _refresh_buttons(self):
        oui_style  = "background:#27ae60; color:white; font-weight:bold;" if self._answer is True  else ""
        non_style  = "background:#c0392b; color:white; font-weight:bold;" if self._answer is False else ""
        nc_style   = "background:#7f8c8d; color:white; font-weight:bold;" if self._answer is None  else ""
        self.btn_oui.setStyleSheet(oui_style)
        self.btn_non.setStyleSheet(non_style)
        self.btn_nc.setStyleSheet(nc_style)

    # ----------------------------------------------------------
    @property
    def answer(self) -> Optional[bool]:
        return self._answer

    @property
    def question_id(self) -> int:
        return self._data["id"]

    def states_result(self) -> list[str]:
        """Retourne les états à activer selon la réponse."""
        if self._answer is True:
            return list(self._data.get("etats_si_oui", []))
        if self._answer is False:
            return list(self._data.get("etats_si_non", []))
        return []

    def transitions_result(self) -> list[dict]:
        """Retourne les transitions à activer selon la réponse."""
        if self._answer is True:
            return list(self._data.get("transitions_si_oui", []))
        if self._answer is False:
            return list(self._data.get("transitions_si_non", []))
        return []


# ===========================================================
# Dialogue principal
# ===========================================================
class QuestionnaireDialog(QDialog):
    """
    Dialogue de questionnaire GEMMA.

    Signaux
    -------
    questionnaire_validated(list[str], list[dict])
        Émis à la validation : liste des codes d'états déduits,
        liste des transitions déduites.
    """

    questionnaire_validated = pyqtSignal(list, list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Questionnaire GEMMA — Définition des états")
        self.setMinimumWidth(700)
        self.setMinimumHeight(520)

        self._data = self._load_json()
        self._rows: list[QuestionRow] = []
        self._setup_ui()

    # ----------------------------------------------------------
    # JSON I/O
    # ----------------------------------------------------------
    def _load_json(self) -> dict:
        if os.path.isfile(QUESTIONNAIRE_JSON):
            with open(QUESTIONNAIRE_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"questions": []}

    def _save_json(self):
        """Persiste les réponses dans le JSON."""
        for row in self._rows:
            for q in self._data["questions"]:
                if q["id"] == row.question_id:
                    q["reponse"] = row.answer
                    break
        with open(QUESTIONNAIRE_JSON, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    # ----------------------------------------------------------
    # UI
    # ----------------------------------------------------------
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)

        # En-tête
        header = QLabel(
            "<b>Arbre de décision GEMMA</b> — Répondez aux questions pour déterminer "
            "les états et transitions à utiliser. Les réponses sont sauvegardées automatiquement."
        )
        header.setWordWrap(True)
        header.setStyleSheet("margin-bottom: 8px;")
        main_layout.addWidget(header)

        # Zone scrollable des questions
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(4)
        container_layout.setContentsMargins(4, 4, 4, 4)

        for q_data in self._data.get("questions", []):
            row = QuestionRow(q_data)
            self._rows.append(row)
            container_layout.addWidget(row)

        container_layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll, stretch=1)

        # Légende
        legend = QLabel(
            "<span style='color:#27ae60'>■</span> Oui — activer les états indiqués   "
            "<span style='color:#c0392b'>■</span> Non — pas ces états   "
            "<span style='color:#7f8c8d'>■</span> ? — sans réponse (ignoré)"
        )
        legend.setStyleSheet("font-size: 11px; margin-top: 6px;")
        main_layout.addWidget(legend)

        # Boutons de dialogue
        btn_box = QDialogButtonBox()
        btn_valider = btn_box.addButton("Valider → ajouter les états", QDialogButtonBox.ButtonRole.AcceptRole)
        btn_sauver  = btn_box.addButton("Enregistrer les réponses",    QDialogButtonBox.ButtonRole.ApplyRole)
        btn_annuler = btn_box.addButton("Annuler",                     QDialogButtonBox.ButtonRole.RejectRole)

        btn_valider.clicked.connect(self._on_validate)
        btn_annuler.clicked.connect(self.reject)
        btn_sauver.clicked.connect(self._on_save_only)

        main_layout.addWidget(btn_box)

    # ----------------------------------------------------------
    # Slots
    # ----------------------------------------------------------
    def _collect_results(self) -> tuple[list[str], list[dict]]:
        """Calcule la liste dédupliquée des états et transitions."""
        states_set: dict[str, None] = {}   # ordered set via dict
        transitions: list[dict] = []
        for row in self._rows:
            for code in row.states_result():
                states_set[code] = None
            transitions.extend(row.transitions_result())
        return list(states_set.keys()), transitions

    def _on_validate(self):
        self._save_json()
        states, transitions = self._collect_results()
        self.questionnaire_validated.emit(states, transitions)
        self.accept()

    def _on_save_only(self):
        self._save_json()
