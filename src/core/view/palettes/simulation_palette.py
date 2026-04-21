"""
Palette de simulation GEMMA.

Affiche :
  - l'état actif courant
  - les transitions sortantes avec un bouton "Simple BP" pour chacune
  - des boutons Init / Reset / Quitter
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QScrollArea,
)
from PyQt6.QtCore import pyqtSignal, Qt


class SimulationPalette(QWidget):
    # ─── Signaux ────────────────────────────────────────────────────────────────
    initRequested  = pyqtSignal()           # bouton Init
    resetRequested = pyqtSignal()           # bouton Reset (retour A1)
    quitRequested  = pyqtSignal()           # bouton Quitter
    bpFired        = pyqtSignal(str, str)   # (dest_code, condition)

    def __init__(self):
        super().__init__()
        self._setup_ui()

    # ─── Construction de l'UI ────────────────────────────────────────────────────
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 8, 4, 8)
        layout.setSpacing(4)

        # ---------- Titre ----------
        title = QLabel("● SIMULATION")
        title.setStyleSheet(
            "font-weight:bold; font-size:13px; color:#e74c3c;"
            "padding-bottom:2px;"
        )
        layout.addWidget(title)

        self._sep(layout)

        # ---------- État actif ----------
        self.lbl_state = QLabel("État : —")
        self.lbl_state.setStyleSheet("font-weight:bold; font-size:12px;")
        self.lbl_state.setWordWrap(True)
        layout.addWidget(self.lbl_state)

        self.lbl_desc = QLabel("")
        self.lbl_desc.setStyleSheet(
            "font-size:10px; font-style:italic; color:#555;"
        )
        self.lbl_desc.setWordWrap(True)
        layout.addWidget(self.lbl_desc)

        # ---------- Init / Reset ----------
        row = QHBoxLayout()
        row.setSpacing(4)
        self.btn_init = QPushButton("Init (A1)")
        self.btn_init.setToolTip("Initialise la simulation — active l'état A1")
        self.btn_init.setStyleSheet(
            "background-color:#27ae60; color:white; font-weight:bold;"
        )
        self.btn_init.clicked.connect(self.initRequested.emit)

        self.btn_reset = QPushButton("Reset")
        self.btn_reset.setToolTip("Revient à l'état A1")
        self.btn_reset.clicked.connect(self.resetRequested.emit)

        row.addWidget(self.btn_init)
        row.addWidget(self.btn_reset)
        layout.addLayout(row)

        self._sep(layout)

        # ---------- Zone des transitions (scrollable) ----------
        lbl_t = QLabel("Transitions :")
        lbl_t.setStyleSheet("font-weight:bold; font-size:11px;")
        layout.addWidget(lbl_t)

        self._trans_container = QWidget()
        self._trans_layout = QVBoxLayout(self._trans_container)
        self._trans_layout.setContentsMargins(0, 0, 0, 0)
        self._trans_layout.setSpacing(4)

        scroll = QScrollArea()
        scroll.setWidget(self._trans_container)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(scroll, 1)

        # ---------- Bouton Quitter ----------
        self._sep(layout)
        self.btn_quit = QPushButton("◼ Quitter sim.")
        self.btn_quit.setStyleSheet(
            "background-color:#c0392b; color:white; font-weight:bold;"
        )
        self.btn_quit.setToolTip("Arrête la simulation et retourne au mode édition")
        self.btn_quit.clicked.connect(self.quitRequested.emit)
        layout.addWidget(self.btn_quit)

    # ─── Mise à jour dynamique ───────────────────────────────────────────────────
    def update_state(self, code: str, desc: str, outgoing: list):
        """
        Met à jour l'affichage.
        outgoing : list of (dest_code, dest_label, condition_str)
        """
        if code:
            self.lbl_state.setText(f"État : {code}")
            self.lbl_desc.setText(desc)
        else:
            self.lbl_state.setText("État : —")
            self.lbl_desc.setText("")

        self._clear_transitions()

        for dest_code, dest_label, condition in outgoing:
            frame = QFrame()
            frame.setFrameShape(QFrame.Shape.Box)
            frame.setStyleSheet(
                "QFrame { border:1px solid #aaa; border-radius:3px; "
                "background:#f9f9f9; } "
            )
            vb = QVBoxLayout(frame)
            vb.setContentsMargins(4, 4, 4, 4)
            vb.setSpacing(2)

            # Destination
            lbl_dest = QLabel(f"→ {dest_code}")
            lbl_dest.setStyleSheet("font-weight:bold; font-size:11px; border:none;")
            vb.addWidget(lbl_dest)

            # Libellé destination (tronqué)
            if dest_label:
                short = dest_label[:28] + ("…" if len(dest_label) > 28 else "")
                lbl_name = QLabel(short)
                lbl_name.setStyleSheet(
                    "font-size:9px; color:#333; font-style:italic; border:none;"
                )
                lbl_name.setWordWrap(True)
                vb.addWidget(lbl_name)

            # Condition
            if condition:
                lbl_cond = QLabel(f"⚙ {condition}")
                lbl_cond.setStyleSheet(
                    "font-size:10px; color:#8e44ad; font-style:italic; border:none;"
                )
                lbl_cond.setWordWrap(True)
                vb.addWidget(lbl_cond)

            # Bouton BP : libellé = condition (tronquée) ou fallback
            _cond_short = condition[:22] + "…" if len(condition or "") > 22 else condition or "BP"
            btn_bp = QPushButton(f"⚡ {_cond_short}")
            btn_bp.setStyleSheet(
                "background-color:#2980b9; color:white; font-weight:bold; border:none;"
            )
            btn_bp.setToolTip(
                f"Simule la condition « {condition or '—'} »\n"
                f"→ active l'état {dest_code}"
            )
            btn_bp.clicked.connect(
                lambda _, dc=dest_code, cond=condition: self.bpFired.emit(dc, cond)
            )
            vb.addWidget(btn_bp)

            self._trans_layout.addWidget(frame)

        if not outgoing and code:
            lbl_empty = QLabel("(Aucune transition\ndisponible)")
            lbl_empty.setStyleSheet(
                "font-size:10px; color:#888; font-style:italic;"
            )
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._trans_layout.addWidget(lbl_empty)

    # ─── Helpers ─────────────────────────────────────────────────────────────────
    @staticmethod
    def _sep(layout):
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:#ccc;")
        layout.addWidget(sep)

    def _clear_transitions(self):
        while self._trans_layout.count():
            item = self._trans_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
