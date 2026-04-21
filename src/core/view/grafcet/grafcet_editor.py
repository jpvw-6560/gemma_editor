"""
grafcet_editor.py — Éditeur Grafcet pleine-page.

Disposition :
  ┌─────────────────────────────────────────────────────┐
  │  Barre de titre                                     │
  ├──────────┬──────────────────────────────┬───────────┤
  │ Toolbox  │   QGraphicsView (scène)      │ Propriétés│
  │ (gauche) │                              │  (droite) │
  ├──────────┴──────────────────────────────┴───────────┤
  │  Barre du bas : Sauvegarder | Charger | Ajouter | ✖ │
  └─────────────────────────────────────────────────────┘

Signaux :
  closeRequested          — fermer l'éditeur
  addToProjectRequested   — émet le dict Grafcet vers AppController
"""
import json
import os

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
    QGraphicsView, QFrame, QStackedWidget, QLineEdit, QPlainTextEdit,
    QCheckBox, QFileDialog, QSizePolicy, QScrollBar,
    QGraphicsRectItem, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QFont, QBrush, QColor, QPen

from core.view.grafcet.grafcet_scene import GrafcetScene
from core.view.grafcet.grafcet_items import (
    EtapeItem, TransitionItem, LiaisonItem, TraitementItem,
    MacroItem, OrBarItem, ParallelBarItem, ConnectorItem,
)


# ══════════════════════════════════════════════════════════════════════════════
# Panneau de propriétés
# ══════════════════════════════════════════════════════════════════════════════

class _PropertiesPanel(QStackedWidget):
    """Panneau droit : édition des propriétés de l'item sélectionné."""

    itemEdited = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._item = None
        self._build_empty()
        self._build_etape()
        self._build_transition()
        self._build_traitement()
        self._build_macro()        # index 4
        self._build_connector()    # index 5

    # ── Pages ─────────────────────────────────────────────────────────────────
    def _build_empty(self):
        w = QWidget()
        vb = QVBoxLayout(w)
        lbl = QLabel("Sélectionnez un élément\npour éditer ses propriétés.")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color:#888; font-style:italic; font-size:11px; padding:10px;")
        vb.addStretch()
        vb.addWidget(lbl)
        vb.addStretch()
        self.addWidget(w)   # index 0

    def _build_etape(self):
        w = QWidget()
        w.setStyleSheet(
            "QLabel { color:#222; }"
            "QLineEdit { background:white; color:black; border:1px solid #bbb; padding:2px; }"
            "QPlainTextEdit { background:white; color:black; border:1px solid #bbb; padding:2px; }"
            "QCheckBox { color:#222; }"
        )
        vb = QVBoxLayout(w)
        vb.setContentsMargins(8, 8, 8, 8)
        vb.setSpacing(6)

        title = QLabel("⬜  Étape")
        title.setStyleSheet("font-weight:bold; font-size:13px; margin-bottom:4px; color:#1a5276;")
        vb.addWidget(title)

        vb.addWidget(QLabel("Numéro :"))
        self._e_num = QLineEdit()
        vb.addWidget(self._e_num)

        vb.addWidget(QLabel("Label :"))
        self._e_label = QLineEdit()
        vb.addWidget(self._e_label)

        vb.addWidget(QLabel("Actions (une par ligne) :"))
        self._e_actions = QPlainTextEdit()
        self._e_actions.setFixedHeight(90)
        self._e_actions.setFont(QFont("Courier New", 8))
        vb.addWidget(self._e_actions)

        self._e_init = QCheckBox("Étape initiale (double bord)")
        vb.addWidget(self._e_init)

        btn = QPushButton("✔  Appliquer")
        btn.setStyleSheet("background:#1a5276; color:white; font-weight:bold; padding:4px;")
        btn.clicked.connect(self._apply_etape)
        vb.addWidget(btn)
        vb.addStretch()
        self.addWidget(w)   # index 1

    def _build_transition(self):
        w = QWidget()
        w.setStyleSheet(
            "QLabel { color:#222; }"
            "QLineEdit { background:white; color:black; border:1px solid #bbb; padding:2px; }"
            "QCheckBox { color:#222; }"
        )
        vb = QVBoxLayout(w)
        vb.setContentsMargins(8, 8, 8, 8)
        vb.setSpacing(6)

        title = QLabel("— Transition")
        title.setStyleSheet("font-weight:bold; font-size:13px; margin-bottom:4px;")
        vb.addWidget(title)

        vb.addWidget(QLabel("Réceptivité :"))
        self._t_recept = QLineEdit()
        vb.addWidget(self._t_recept)

        btn = QPushButton("✔  Appliquer")
        btn.setStyleSheet("background:#1a5276; color:white; font-weight:bold; padding:4px;")
        btn.clicked.connect(self._apply_transition)
        vb.addWidget(btn)
        vb.addStretch()
        self.addWidget(w)   # index 2

    def _build_traitement(self):
        w = QWidget()
        w.setStyleSheet(
            "QLabel { color:#222; }"
            "QLineEdit { background:white; color:black; border:1px solid #bbb; padding:2px; }"
            "QPlainTextEdit { background:white; color:black; border:1px solid #bbb; padding:2px; }"
        )
        vb = QVBoxLayout(w)
        vb.setContentsMargins(8, 8, 8, 8)
        vb.setSpacing(6)

        title = QLabel("⊞  Traitement")
        title.setStyleSheet("font-weight:bold; font-size:13px; margin-bottom:4px; color:#7d3c98;")
        vb.addWidget(title)

        vb.addWidget(QLabel("Titre (en-tête) :"))
        self._tr_titre = QLineEdit()
        vb.addWidget(self._tr_titre)

        vb.addWidget(QLabel("Code (une équation par ligne) :"))
        self._tr_code = QPlainTextEdit()
        self._tr_code.setFixedHeight(110)
        self._tr_code.setFont(QFont("Courier New", 8))
        vb.addWidget(self._tr_code)

        hint = QLabel("X1 = étape n°1,  X2 = étape n°2…")
        hint.setStyleSheet("color:#888; font-size:9px; font-style:italic;")
        hint.setWordWrap(True)
        vb.addWidget(hint)

        btn = QPushButton("✔  Appliquer")
        btn.setStyleSheet("background:#7d3c98; color:white; font-weight:bold; padding:4px;")
        btn.clicked.connect(self._apply_traitement)
        vb.addWidget(btn)
        vb.addStretch()
        self.addWidget(w)   # index 3

    def _build_macro(self):
        w = QWidget()
        w.setStyleSheet(
            "QLabel { color:#222; }"
            "QLineEdit { background:white; color:black; border:1px solid #bbb; padding:2px; }"
        )
        vb = QVBoxLayout(w)
        vb.setContentsMargins(8, 8, 8, 8)
        vb.setSpacing(6)

        title = QLabel("M  Macro-étape")
        title.setStyleSheet("font-weight:bold; font-size:13px; margin-bottom:4px; color:#884ea0;")
        vb.addWidget(title)

        vb.addWidget(QLabel("Numéro :"))
        self._m_num = QLineEdit()
        vb.addWidget(self._m_num)

        vb.addWidget(QLabel("Label :"))
        self._m_label = QLineEdit()
        vb.addWidget(self._m_label)

        btn = QPushButton("✔  Appliquer")
        btn.setStyleSheet("background:#884ea0; color:white; font-weight:bold; padding:4px;")
        btn.clicked.connect(self._apply_macro)
        vb.addWidget(btn)
        vb.addStretch()
        self.addWidget(w)   # index 4

    def _build_connector(self):
        w = QWidget()
        w.setStyleSheet(
            "QLabel { color:#222; }"
            "QLineEdit { background:white; color:black; border:1px solid #bbb; padding:2px; }"
        )
        vb = QVBoxLayout(w)
        vb.setContentsMargins(8, 8, 8, 8)
        vb.setSpacing(6)

        title = QLabel("▽ / △  Renvoi")
        title.setStyleSheet("font-weight:bold; font-size:13px; margin-bottom:4px; color:#1a5276;")
        vb.addWidget(title)

        vb.addWidget(QLabel("Label (ex: X3) :"))
        self._c_label = QLineEdit()
        vb.addWidget(self._c_label)

        self._c_dir_hint = QLabel("Direction : ")
        self._c_dir_hint.setStyleSheet("color:#888; font-size:10px; font-style:italic;")
        self._c_dir_hint.setWordWrap(True)
        vb.addWidget(self._c_dir_hint)

        btn = QPushButton("✔  Appliquer")
        btn.setStyleSheet("background:#1a5276; color:white; font-weight:bold; padding:4px;")
        btn.clicked.connect(self._apply_connector)
        vb.addWidget(btn)
        vb.addStretch()
        self.addWidget(w)   # index 5

    # ── Mise à jour ────────────────────────────────────────────────────────────
    def show_item(self, item):
        self._item = item
        if item is None:
            self.setCurrentIndex(0)
        elif isinstance(item, EtapeItem):
            self._e_num.setText(str(item.numero))
            self._e_label.setText(item.label)
            self._e_actions.setPlainText("\n".join(item.actions))
            self._e_init.setChecked(item.initiale)
            self.setCurrentIndex(1)
        elif isinstance(item, TransitionItem):
            self._t_recept.setText(item.receptivite)
            self.setCurrentIndex(2)
        elif isinstance(item, TraitementItem):
            self._tr_titre.setText(item.titre)
            self._tr_code.setPlainText("\n".join(item.lignes))
            self.setCurrentIndex(3)
        elif isinstance(item, MacroItem):
            self._m_num.setText(str(item.numero))
            self._m_label.setText(item.label)
            self.setCurrentIndex(4)
        elif isinstance(item, ConnectorItem):
            self._c_label.setText(item.label)
            self._c_dir_hint.setText(
                f"Direction : {'sortie ▽' if item.direction == 'out' else 'entrée △'}"
            )
            self.setCurrentIndex(5)
        else:
            self.setCurrentIndex(0)

    # ── Application ───────────────────────────────────────────────────────────
    def _apply_etape(self):
        item = self._item
        if not isinstance(item, EtapeItem):
            return

        # Garder la hauteur actuelle avant modification
        old_height = item.height()
        old_bottom = item.y() + old_height

        # ── Validation du numéro ────────────────────────────────────────────
        num_ok = False
        try:
            new_num = int(self._e_num.text())
            # Vérifier l'unicité : chercher une autre étape avec ce numéro
            sc = item.scene()
            used_by_other = sc and any(
                isinstance(it, EtapeItem) and it is not item and it.numero == new_num
                for it in sc.items()
            )
            if used_by_other:
                self._e_num.setStyleSheet(
                    "background:#fdecea; color:#c0392b; border:1px solid #e74c3c;"
                )
                QMessageBox.warning(
                    self, "Numéro déjà utilisé",
                    f"Une autre étape porte déjà le numéro {new_num}.\n"
                    "Choisissez un numéro différent."
                )
                return
            else:
                self._e_num.setStyleSheet("")
                item.numero = new_num
                num_ok = True
        except ValueError:
            self._e_num.setStyleSheet(
                "background:#fdecea; color:#c0392b; border:1px solid #e74c3c;"
            )
            return
        item.label    = self._e_label.text()
        item.actions  = [l for l in self._e_actions.toPlainText().splitlines() if l.strip()]
        item.initiale = self._e_init.isChecked()

        new_height = item.height()
        delta = new_height - old_height

        item.prepareGeometryChange()
        item.update()

        # Décaler tous les items en dessous si la hauteur a changé
        sc = item.scene()
        if abs(delta) > 0.5 and sc:
            for other in sc.items():
                if other is item:
                    continue
                if isinstance(other, LiaisonItem):
                    continue
                if other.y() >= old_bottom - 2:
                    other.setPos(other.x(), other.y() + delta)
            # Rafraîchir toutes les liaisons
            if hasattr(sc, "_liaisons"):
                for lia in sc._liaisons:
                    lia.update_path()

        self.itemEdited.emit()

    def _apply_transition(self):
        item = self._item
        if not isinstance(item, TransitionItem):
            return
        item.receptivite = self._t_recept.text()
        item.update()
        self.itemEdited.emit()

    def _apply_traitement(self):
        item = self._item
        if not isinstance(item, TraitementItem):
            return
        item.titre  = self._tr_titre.text() or "Traitement"
        item.lignes = [l for l in self._tr_code.toPlainText().splitlines() if l.strip()]
        item.prepareGeometryChange()
        item.update()
        self.itemEdited.emit()
    def _apply_macro(self):
        item = self._item
        if not isinstance(item, MacroItem):
            return
        try:
            item.numero = int(self._m_num.text())
            self._m_num.setStyleSheet("")
        except ValueError:
            self._m_num.setStyleSheet("background:#fdecea;")
            return
        item.label = self._m_label.text()
        item.prepareGeometryChange()
        item.update()
        self.itemEdited.emit()

    def _apply_connector(self):
        item = self._item
        if not isinstance(item, ConnectorItem):
            return
        item.label = self._c_label.text()
        item.update()
        self.itemEdited.emit()

# ══════════════════════════════════════════════════════════════════════════════
# GrafcetEditor — widget pleine-page
# ══════════════════════════════════════════════════════════════════════════════

class GrafcetEditor(QWidget):
    """
    Éditeur Grafcet pleine-page. S'ouvre via show_fullpage() de MainWindow.

    Signaux :
      closeRequested          — fermer sans toucher au projet
      addToProjectRequested   — émet le dict Grafcet sérialisé
    """
    closeRequested        = pyqtSignal()
    addToProjectRequested = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = GrafcetScene()
        self._project_dir = None  # dossier du projet courant, fourni par AppController
        self._setup_ui()

    # ── Construction UI ───────────────────────────────────────────────────────
    def _setup_ui(self):
        root_vb = QVBoxLayout(self)
        root_vb.setContentsMargins(0, 0, 0, 0)
        root_vb.setSpacing(0)

        # Titre
        root_vb.addWidget(self._make_title_bar())

        # Corps : toolbox | canvas | propriétés
        body = QWidget()
        body_hb = QHBoxLayout(body)
        body_hb.setContentsMargins(0, 0, 0, 0)
        body_hb.setSpacing(0)
        body_hb.addWidget(self._make_toolbox())
        body_hb.addWidget(self._make_canvas_view(), 1)  # crée self._view
        body_hb.addWidget(self._make_props_panel())
        # Activer la sélection par défaut (Nécessite self._view)
        self._select_tool(GrafcetScene.TOOL_SELECT)
        root_vb.addWidget(body, 1)

        # Barre du bas
        root_vb.addWidget(self._make_bottom_bar())

        # Connexions scène ↔ panneau propriétés
        self._scene.itemSelectionChanged.connect(self._props.show_item)

    def _make_title_bar(self) -> QWidget:
        bar = QWidget()
        bar.setStyleSheet("background:#1a5276;")
        hb = QHBoxLayout(bar)
        hb.setContentsMargins(10, 5, 10, 5)
        lbl = QLabel("⊞  Éditeur Grafcet")
        lbl.setStyleSheet("color:white; font-weight:bold; font-size:14px;")
        hb.addWidget(lbl)
        hb.addStretch()
        # Nom du grafcet (éditable)
        self._name_edit = QLineEdit("Nouveau Grafcet")
        self._name_edit.setFixedWidth(200)
        self._name_edit.setStyleSheet(
            "background:#2471a3; color:white; border:1px solid #5dade2; "
            "padding:2px 6px; font-size:12px;"
        )
        hb.addWidget(self._name_edit)
        return bar

    def _make_toolbox(self) -> QWidget:
        tb = QWidget()
        tb.setFixedWidth(100)
        tb.setStyleSheet("background:#2c3e50;")
        vb = QVBoxLayout(tb)
        vb.setContentsMargins(4, 8, 4, 8)
        vb.setSpacing(4)

        self._tool_btns: dict[str, QPushButton] = {}
        tools = [
            ("↖",  "Sélection",     GrafcetScene.TOOL_SELECT),
            ("□",  "Étape",          GrafcetScene.TOOL_ETAPE),
            ("M",   "Macro",          GrafcetScene.TOOL_MACRO),
            ("—",  "Transition",    GrafcetScene.TOOL_TRANSITION),
            ("=↓", "Div. OU",       GrafcetScene.TOOL_OR_BAR),
            ("=↑", "Conv. OU",      GrafcetScene.TOOL_OR_BAR_CONV),
            ("≡↓", "Div. ET",       GrafcetScene.TOOL_PARALLEL_BAR),
            ("≡↑", "Conv. ET",      GrafcetScene.TOOL_PARALLEL_BAR_CONV),
            ("↕",  "Liaison",        GrafcetScene.TOOL_LIAISON),
            ("⊞",  "Traitement",    GrafcetScene.TOOL_TRAITEMENT),
            ("▽",  "Renvoi→",       GrafcetScene.TOOL_CONNECTOR_OUT),
            ("△",  "Renvoi←",       GrafcetScene.TOOL_CONNECTOR_IN),
        ]
        style_normal  = (
            "QPushButton { color:white; font-size:10px; border:1px solid #555; "
            "background:#34495e; border-radius:3px; }"
            "QPushButton:checked { background:#e67e22; border:2px solid #f39c12; }"
        )
        for icon, label, tool_id in tools:
            btn = QPushButton(f"{icon}\n{label}")
            btn.setCheckable(True)
            btn.setFixedHeight(44)
            btn.setStyleSheet(style_normal)
            btn.clicked.connect(lambda _chk, t=tool_id: self._select_tool(t))
            vb.addWidget(btn)
            self._tool_btns[tool_id] = btn

        # Séparateur
        vb.addSpacing(6)
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:#555;")
        vb.addWidget(sep)
        vb.addSpacing(4)

        # Bouton supprimer
        btn_del = QPushButton("🗑\nSupprimer")
        btn_del.setFixedHeight(50)
        btn_del.setStyleSheet(
            "color:#e74c3c; font-size:10px; border:1px solid #555; "
            "background:#34495e; border-radius:3px;"
        )
        btn_del.clicked.connect(self._scene.delete_selected)
        vb.addWidget(btn_del)
        vb.addStretch()
        return tb

    def _make_canvas_view(self) -> QGraphicsView:
        view = QGraphicsView(self._scene)
        view.setRenderHint(view.renderHints())
        view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        view.setStyleSheet("background:white; border:none;")
        # Grille de fond légère
        view.setBackgroundBrush(QBrush(QColor("#f9f9f9")))
        self._view = view
        return view

    def _make_props_panel(self) -> QWidget:
        self._props = _PropertiesPanel()
        self._props.setFixedWidth(220)
        self._props.setStyleSheet(
            "background:#f8f9fa; border-left:1px solid #ddd;"
        )
        return self._props

    def _make_bottom_bar(self) -> QWidget:
        bar = QWidget()
        bar.setStyleSheet("background:#ecf0f1; border-top:1px solid #bdc3c7;")
        hb = QHBoxLayout(bar)
        hb.setContentsMargins(8, 6, 8, 6)
        hb.setSpacing(6)

        btns = [
            ("💾  Sauvegarder",        "#27ae60", self._save),
            ("📂  Charger",            "#2980b9", self._load),
            ("➕  Ajouter au projet",  "#8e44ad", self._add_to_project),
            ("✖  Fermer",              "#c0392b", self.closeRequested.emit),
        ]
        for label, color, slot in btns:
            btn = QPushButton(label)
            btn.setStyleSheet(
                f"background:{color}; color:white; font-weight:bold; padding:4px 10px;"
            )
            btn.clicked.connect(slot)
            hb.addWidget(btn)

        hb.addStretch()
        return bar

    # ── Sélection d'outil ─────────────────────────────────────────────────────
    def _select_tool(self, tool: str):
        self._scene.set_tool(tool)
        for t, btn in self._tool_btns.items():
            btn.setChecked(t == tool)
        if tool == GrafcetScene.TOOL_SELECT:
            self._view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        else:
            self._view.setDragMode(QGraphicsView.DragMode.NoDrag)

    # ── Répertoire projet ─────────────────────────────────────────────
    def set_project_dir(self, path: str):
        """Indique le dossier du projet courant (pour la sauvegarde/chargement)."""
        self._project_dir = path

    def _grafcets_dir(self) -> str:
        """Retourne le dossier grafcets/ du projet, ou ~ si aucun projet n'est ouvert."""
        if self._project_dir:
            import os as _os
            d = _os.path.join(self._project_dir, "grafcets")
            _os.makedirs(d, exist_ok=True)
            return d
        return os.path.expanduser("~")

    # ── Sauvegarder / Charger ─────────────────────────────────────────────────
    def _save(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Sauvegarder le Grafcet",
            os.path.join(self._grafcets_dir(), f"{self._name_edit.text()}.json"),
            "JSON (*.json);;Tous (*.*)",
        )
        if not path:
            return
        data = self._scene.to_dict()
        data["nom"] = self._name_edit.text()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Charger un Grafcet",
            self._grafcets_dir(),
            "JSON (*.json);;Tous (*.*)",
        )
        if not path:
            return
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        self._scene.from_dict(data)
        self._name_edit.setText(data.get("nom", "Grafcet"))

    # ── Ajouter au projet ─────────────────────────────────────────────────────
    def _add_to_project(self):
        data = self._scene.to_dict()
        data["nom"] = self._name_edit.text()
        self.addToProjectRequested.emit(data)
