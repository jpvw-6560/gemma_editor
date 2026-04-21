"""
generation_palette.py — Affichage interactif des Grafcets générés (GS, GC, GPN).

Chaque onglet contient un GrafcetScene éditable avec toolbox complète.
Les étapes et transitions sont positioinnées automatiquement en colonne.
"""
import os
import json
from collections import defaultdict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTabWidget, QFileDialog, QFrame, QGraphicsView, QInputDialog,
    QScrollArea, QMessageBox,
)
from PyQt6.QtCore import pyqtSignal, Qt, QRect, QPointF, QRectF, QTimer, QSize
from PyQt6.QtGui import QBrush, QColor, QFont, QPen, QPainter, QFontMetrics, QPolygonF, QWheelEvent, QPixmap, QIcon

from core.view.grafcet.grafcet_scene import GrafcetScene
from core.config.app_config import AppConfig

# Chemin du grafcet de test (modifiable manuellement, rechargeable en un clic)
_TEST_GRAFCET_PATH = os.path.normpath(os.path.join(
    os.path.dirname(__file__),           # …/view/palettes/
    "..", "..", "data", "grafcets", "test_grafcet.json"
))

# ══════════════════════════════════════════════════════════════════════════════
# Vue interactive avec zoom Ctrl+Wheel et panoramique Space
# ══════════════════════════════════════════════════════════════════════════════
class _GrafcetView(QGraphicsView):
    """QGraphicsView étendue pour la génération : Ctrl+Wheel=zoom, Space=pan."""

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self._space_down = False
        self._initial_fit_done = False
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)

    def fit_all(self):
        br = self.scene().itemsBoundingRect()
        if not br.isEmpty():
            self.fitInView(br.adjusted(-30, -30, 30, 30), Qt.AspectRatioMode.KeepAspectRatio)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._initial_fit_done:
            self._initial_fit_done = True
            QTimer.singleShot(0, self.fit_all)

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self.scale(factor, factor)
            event.accept()
        else:
            super().wheelEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F and not event.isAutoRepeat():
            self.fit_all()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._space_down = True
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._space_down = False
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            self.viewport().unsetCursor()
        super().keyReleaseEvent(event)


# ══════════════════════════════════════════════════════════════════════════════
# Constantes de mise en page
# ══════════════════════════════════════════════════════════════════════════════
_CX        = 330      # centre X de la colonne des étapes
_STEP_W    = 310      # largeur d'une étape
_HDR_H     = 46      # hauteur de l'en-tête (num + label)
_ACT_H     = 17      # hauteur par ligne d'action
_ACT_PAD   = 5       # padding vertical zone actions
_V_GAP     = 66      # espace vertical entre bas étape[n] et haut étape[n+1]
_TRANS_W   = 110     # longueur de la barre de transition
_TRANS_H   = 5       # épaisseur de la barre
_SIDE_R    = 90      # décalage latéral des flèches saut-avant (droite)
_SIDE_L    = 90      # décalage latéral des flèches retour (gauche)
_TOP_PAD   = 46      # marge en haut (laisse de la place pour le titre)
_TOTAL_W   = 750     # largeur totale du widget de dessin

# ── Couleurs ──────────────────────────────────────────────────────────────────
_C_BG       = QColor("#ffffff")
_C_STEP     = QColor("#d6eaf8")
_C_INIT     = QColor("#a9cce3")
_C_ACT_BG   = QColor("#f4f6f7")
_C_BORDER   = QColor("#1a5276")
_C_NUM      = QColor("#1a5276")
_C_LABEL    = QColor("#1c2833")
_C_ACT      = QColor("#1e8449")
_C_TRANS    = QColor("#1c2833")
_C_RECEPT   = QColor("#76448a")
_C_CMT      = QColor("#aab7b8")
_C_FW       = QColor("#2471a3")   # flèche saut avant (bleu)
_C_BK       = QColor("#c0392b")   # flèche retour (rouge)

# ── Polices ───────────────────────────────────────────────────────────────────
_F_TITLE  = QFont("Arial", 11, QFont.Weight.Bold)
_F_NUM    = QFont("Arial", 13, QFont.Weight.Bold)
_F_LABEL  = QFont("Arial", 9)
_F_ACT    = QFont("Courier New", 8)
_F_RECEPT = QFont("Arial", 9, QFont.Weight.Bold)
_F_CMT    = QFont("Arial", 7)
_F_CMT.setItalic(True)
_F_RECEPT.setItalic(True)


# ══════════════════════════════════════════════════════════════════════════════
# Widget de dessin d'un Grafcet
# ══════════════════════════════════════════════════════════════════════════════
class _GrafcetCanvas(QWidget):
    """
    Dessine le Grafcet complet via paintEvent.
    Doit être placé dans un QScrollArea.
    """

    def __init__(self, grafcet: dict, parent=None):
        super().__init__(parent)
        self._g   = grafcet
        self._pos = {}   # {num: (x, y, w, h)}
        self._compute_positions()

        max_y = (max(y + h for (_, y, _, h) in self._pos.values())
                 if self._pos else 200)
        self.setFixedSize(_TOTAL_W, max_y + 60)

    # ── Calcul des positions ──────────────────────────────────────────────────
    def _compute_positions(self):
        steps = sorted(self._g["etapes"], key=lambda e: e["num"])
        y = _TOP_PAD
        for step in steps:
            n_lines = max(1, len([a for a in step["actions"] if a.strip()]))
            h = _HDR_H + _ACT_PAD + n_lines * _ACT_H + _ACT_PAD
            x = _CX - _STEP_W // 2
            self._pos[step["num"]] = (x, y, _STEP_W, h)
            y += h + _V_GAP

    # ── paintEvent ────────────────────────────────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.fillRect(self.rect(), _C_BG)

        # Titre du grafcet en haut du canvas
        painter.setFont(_F_TITLE)
        painter.setPen(QPen(_C_NUM))
        painter.drawText(16, 28, self._g.get("titre", self._g.get("nom", "")))
        painter.setPen(QPen(_C_CMT))
        sep_fr = QFont("Arial", 7)
        sep_fr.setItalic(True)
        painter.setFont(sep_fr)
        painter.drawLine(16, 34, _TOTAL_W - 16, 34)

        # 1. Transitions (en dessous des étapes)
        for t in self._g["transitions"]:
            self._paint_trans(painter, t)

        # 2. Étapes (par-dessus)
        for step in sorted(self._g["etapes"], key=lambda e: e["num"]):
            self._paint_step(painter, step)

    # ── Étape ─────────────────────────────────────────────────────────────────
    def _paint_step(self, painter: QPainter, step: dict):
        x, y, w, h = self._pos[step["num"]]
        is_init = step.get("initiale", False)

        # Fond en-tête
        painter.fillRect(x, y, w, _HDR_H, _C_INIT if is_init else _C_STEP)
        # Fond actions
        painter.fillRect(x, y + _HDR_H, w, h - _HDR_H, _C_ACT_BG)

        # Bordure extérieure
        painter.setPen(QPen(_C_BORDER, 2))
        painter.drawRect(x, y, w, h)

        # Double bord si étape initiale
        if is_init:
            inset = 4
            painter.setPen(QPen(_C_BORDER, 1.5))
            painter.drawRect(x + inset, y + inset, w - 2 * inset, _HDR_H - 2 * inset)

        # Séparateur header/actions
        painter.setPen(QPen(_C_BORDER, 1, Qt.PenStyle.DotLine))
        painter.drawLine(x + 1, y + _HDR_H, x + w - 1, y + _HDR_H)

        # Numéro (gauche, grand, gras)
        painter.setFont(_F_NUM)
        painter.setPen(QPen(_C_NUM))
        painter.drawText(x + 8, y + _HDR_H - 8, str(step["num"]))

        # Label (à droite du numéro)
        painter.setFont(_F_LABEL)
        painter.setPen(QPen(_C_LABEL))
        lbl_rect = QRect(x + 36, y + 4, w - 44, _HDR_H - 8)
        painter.drawText(
            lbl_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            | Qt.TextFlag.TextWordWrap,
            step["label"],
        )

        # Actions
        painter.setFont(_F_ACT)
        painter.setPen(QPen(_C_ACT))
        ay = y + _HDR_H + _ACT_PAD + 11
        for action in step["actions"]:
            if action.strip():
                painter.drawText(x + 10, ay, action)
                ay += _ACT_H

    # ── Transition ────────────────────────────────────────────────────────────
    def _paint_trans(self, painter: QPainter, t: dict):
        src, dst = t["de"], t["vers"]
        if src not in self._pos or dst not in self._pos:
            return

        sx, sy, sw, sh = self._pos[src]
        dx, dy, dw, dh = self._pos[dst]

        diff = dst - src
        if diff == 1:
            self._inline_trans(painter, t, sy + sh, dy)
        elif diff > 1:
            self._side_arrow(painter, t,
                             sx + sw, sy + sh // 2,
                             dx + dw, dy + dh // 2,
                             side="right")
        else:
            self._side_arrow(painter, t,
                             sx, sy + sh // 2,
                             dx, dy + dh // 2,
                             side="left")

    def _inline_trans(self, painter: QPainter, t: dict, y_from: int, y_to: int):
        """Transition classique entre deux étapes adjacentes."""
        mid_y = (y_from + y_to) // 2

        painter.setPen(QPen(_C_TRANS, 2))
        painter.drawLine(_CX, y_from, _CX, mid_y - _TRANS_H // 2)

        bx = _CX - _TRANS_W // 2
        painter.fillRect(bx, mid_y - _TRANS_H // 2, _TRANS_W, _TRANS_H, _C_TRANS)

        painter.setPen(QPen(_C_TRANS, 2))
        painter.drawLine(_CX, mid_y + _TRANS_H // 2, _CX, y_to)

        painter.setFont(_F_RECEPT)
        painter.setPen(QPen(_C_RECEPT))
        painter.drawText(_CX + _TRANS_W // 2 + 10, mid_y + 5, t["receptivite"])

        cmt = t.get("commentaire", "")
        if cmt:
            painter.setFont(_F_CMT)
            painter.setPen(QPen(_C_CMT))
            painter.drawText(_CX + _TRANS_W // 2 + 10, mid_y + 18, cmt)

    def _side_arrow(self, painter: QPainter, t: dict,
                    sx: int, sy: int, dx: int, dy: int, side: str):
        """Flèche latérale (saut ou boucle)."""
        color = _C_BK if side == "left" else _C_FW
        off = (max(sx, dx) + _SIDE_R) if side == "right" else (min(sx, dx) - _SIDE_L)

        painter.setPen(QPen(color, 1.5, Qt.PenStyle.DashLine))
        painter.drawLine(int(sx), int(sy), int(off), int(sy))
        painter.drawLine(int(off), int(sy), int(off), int(dy))
        painter.drawLine(int(off), int(dy), int(dx), int(dy))

        # Barre de transition au milieu du segment vertical
        mid_y = (sy + dy) // 2
        blen = _TRANS_W // 3
        painter.setPen(QPen(color, 3, Qt.PenStyle.SolidLine))
        painter.drawLine(int(off - blen), int(mid_y), int(off + blen), int(mid_y))

        # Réceptivité
        painter.setFont(_F_RECEPT)
        painter.setPen(QPen(_C_RECEPT))
        recept = t["receptivite"]
        if side == "right":
            painter.drawText(int(off) + 6, int(mid_y) + 5, recept)
        else:
            fm = QFontMetrics(_F_RECEPT)
            tw = fm.horizontalAdvance(recept)
            painter.drawText(int(off) - tw - 6, int(mid_y) + 5, recept)

        # Tête de flèche à l'arrivée
        arr_dir = "left" if side == "right" else "right"
        self._arrowhead(painter, dx, dy, arr_dir, color)

    @staticmethod
    def _arrowhead(painter: QPainter, x: int, y: int, direction: str, color: QColor):
        s = 8
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))
        if direction == "down":
            pts = QPolygonF([QPointF(x-s, y-s), QPointF(x+s, y-s), QPointF(x, y)])
        elif direction == "up":
            pts = QPolygonF([QPointF(x-s, y+s), QPointF(x+s, y+s), QPointF(x, y)])
        elif direction == "left":
            pts = QPolygonF([QPointF(x+s, y-s), QPointF(x+s, y+s), QPointF(x, y)])
        else:  # right
            pts = QPolygonF([QPointF(x-s, y-s), QPointF(x-s, y+s), QPointF(x, y)])
        painter.drawPolygon(pts)
        painter.setBrush(Qt.BrushStyle.NoBrush)


# ══════════════════════════════════════════════════════════════════════════════
# Palette principale
# ══════════════════════════════════════════════════════════════════════════════
# ── Constantes d'auto-layout ─────────────────────────────────────────────────────────
_ALT_CX    = 120     # centre horizontal (aligne carré + barre de transition)
_ALT_V_GAP = 80      # espace vertical entre étapes
_I_STEP_SZ  = 50     # côté du carré (= _STEP_SZ dans grafcet_items)
_I_TRANS_W  = 50     # largeur barre de transition (= _TRANS_W, partage même col)
_I_STUB_H   = 10     # branches verticales courtes (= _STUB_H)
_I_TRANS_H  = 5


def _step_h(actions: list) -> int:
    n = max(0, len([a for a in actions if a.strip()]))
    # label en guillemets (16px) + n actions (14px chacune)
    content_h = 16 + n * 14 + 4
    return max(_I_STEP_SZ, content_h)


def _auto_layout(g: dict) -> dict:
    """
    Convertit un dict de GrafcetGenerator en dict compatible GrafcetScene.from_dict().

    Algorithme IEC 848 via analyse topologique réelle :
    ─────────────────────────────────────────────────────────────────────────────
    1. Graphe dirigé (sans doublons)
    2. DFS itératif → détection des back-edges (transitions de retour/boucle)
    3. Graphe forward (DAG) = graphe sans back-edges
    4. BFS topologique (Kahn) sur le DAG forward
    5. Assignation des colonnes :
         branche 0  → même colonne que le parent
         branche i  → colonne parent + i  (offset = i × _BS px)
    6. Calcul des positions y en ordre topologique
    7. Création des TransitionItems et OrBarItems :
         • len(fwd+bck sorties) == 1 → TransitionItem simple
         • len(fwd+bck sorties) >  1 → OrBarItem div (divergence OU)
         Les back-edges sont inclus comme branches de l'OrBar div :
         LiaisonItem._compute les route automatiquement vers le haut.
    ─────────────────────────────────────────────────────────────────────────────
    """
    from collections import deque

    _BS = 160                    # espacement branches (px)
    _BX = _I_STEP_SZ // 2       # branch_x(0) local → aligne branche 0 sur col

    steps_data = g.get("etapes", [])
    trans_data  = g.get("transitions", [])
    if not steps_data:
        return {"etapes": [], "transitions": [], "traitements": [],
                "macros": [], "or_bars": [], "parallel_bars": [],
                "connectors": [], "liaisons": []}

    step_by_num: dict[int, dict] = {e["num"]: e for e in steps_data}
    step_nums = list(step_by_num.keys())

    # ── 1. Graphe (sans doublons) ──────────────────────────────────────────
    outs: dict[int, list] = {n: [] for n in step_nums}
    ins:  dict[int, list] = {n: [] for n in step_nums}
    seen: set[tuple]      = set()
    for t in trans_data:
        src, dst = t.get("de"), t.get("vers")
        if src in step_by_num and dst in step_by_num:
            pair = (src, dst)
            if pair not in seen:
                seen.add(pair)
                outs[src].append((dst, t))
                ins[dst].append((src, t))

    # ── 2. DFS itératif → back-edges ──────────────────────────────────────
    color: dict[int, int] = {n: 0 for n in step_nums}   # 0=blanc 1=gris 2=noir
    back_edges: set[tuple] = set()

    initials = [e["num"] for e in steps_data if e.get("initiale")]
    if not initials:
        initials = [n for n in step_nums if not ins[n]] or [step_nums[0]]

    for root in initials + [n for n in step_nums if n not in initials]:
        if color[root] != 0:
            continue
        stack = [(root, iter(outs[root]))]
        color[root] = 1
        while stack:
            node, children = stack[-1]
            try:
                dst, _ = next(children)
                if color[dst] == 0:
                    color[dst] = 1
                    stack.append((dst, iter(outs[dst])))
                elif color[dst] == 1:
                    back_edges.add((node, dst))
            except StopIteration:
                color[node] = 2
                stack.pop()

    # ── 3. Graphe forward (DAG sans back-edges) ────────────────────────────
    fwd_outs: dict[int, list] = {n: [] for n in step_nums}
    fwd_ins:  dict[int, list] = {n: [] for n in step_nums}
    for src in step_nums:
        for dst, t in outs[src]:
            if (src, dst) not in back_edges:
                fwd_outs[src].append((dst, t))
                fwd_ins[dst].append((src, t))

    # back_outs[src] = [(dst, t)]
    back_outs: dict[int, list] = {n: [] for n in step_nums}
    for (src, dst) in back_edges:
        t_bk = next(
            (t2 for t2 in trans_data if t2.get("de") == src and t2.get("vers") == dst),
            {"receptivite": "1"},
        )
        back_outs[src].append((dst, t_bk))

    # ── 4. Kahn BFS → ordre topologique ───────────────────────────────────
    in_deg: dict[int, int] = {n: len(fwd_ins[n]) for n in step_nums}
    kahn_q = deque(n for n in step_nums if in_deg[n] == 0)
    topo: list[int] = []
    while kahn_q:
        n = kahn_q.popleft()
        topo.append(n)
        for dst, _ in fwd_outs[n]:
            in_deg[dst] -= 1
            if in_deg[dst] == 0:
                kahn_q.append(dst)
    for n in step_nums:   # nœuds résiduels (cycles forward)
        if n not in topo:
            topo.append(n)

    # ── 4bis. Séparer nœuds primaires (atteignables depuis initiales) et orphelins ─
    initial_set = {e["num"] for e in steps_data if e.get("initiale")}
    if not initial_set:
        initial_set = {n for n in step_nums if not fwd_ins[n]}
    primary_set: set[int] = set()
    reach_q: deque = deque(initial_set)
    while reach_q:
        n = reach_q.popleft()
        if n in primary_set:
            continue
        primary_set.add(n)
        for dst, _ in fwd_outs[n]:
            reach_q.append(dst)
    # Ordre de traitement : primaires en premier (dans topo), puis orphelins
    proc_topo = [n for n in topo if n in primary_set] + [n for n in topo if n not in primary_set]

    # ── 5. Assignation des colonnes (BFS : premier arrivé = colonne définitive) ─
    # branche 0 → même colonne que le parent
    # branche i → colonne parent + i  (offset = i × _BS px)
    col_of: dict[int, int] = {}
    assign_q: deque = deque()
    primary_sources = [n for n in proc_topo if not fwd_ins[n] and n in primary_set]
    if not primary_sources:
        primary_sources = [n for n in proc_topo if n in primary_set][:1] or [proc_topo[0]]
    for src in primary_sources:
        assign_q.append((src, 0))
    while assign_q:
        n, col = assign_q.popleft()
        if n in col_of:
            continue
        col_of[n] = col
        children = fwd_outs[n]
        if len(children) <= 1:
            for dst, _ in children:
                assign_q.append((dst, col))
        else:
            # Sources de back-edge en premier : leur distance de retour est plus courte
            sorted_children = sorted(children, key=lambda item: (0 if back_outs[item[0]] else 1))
            for i, (dst, _) in enumerate(sorted_children):
                assign_q.append((dst, col + i))
    _orphan_offset = 0
    for n in proc_topo:
        if n not in col_of:
            # Orphelin : place à droite de TOUS les nœuds primaires pour éviter
            # toute interférence visuelle avec les branches des OrBars primaires.
            _max_prim = (max(col_of[k] for k in primary_set if k in col_of)
                         if any(k in col_of for k in primary_set) else 0)
            col_of[n] = _max_prim + 1 + _orphan_offset
            _orphan_offset += 1

    # ── 6. Positions y (ordre topologique) ────────────────────────────────
    t_total_h = _I_STUB_H * 2 + _I_TRANS_H
    step_h_map: dict[int, int]   = {n: _step_h(step_by_num[n].get("actions", [])) for n in step_nums}
    step_y_map: dict[int, float] = {}

    # Pré-calcul : étapes avec plusieurs parents forward (convergence OU) → espace extra
    _conv_extra = t_total_h + 20   # hauteur de la barre de convergence + marge

    for n in proc_topo:
        parents = fwd_ins[n]
        # Compter les parents primaires (avec position déjà calculée)
        n_real_parents = sum(1 for src, _ in parents if src in step_y_map)
        needs_conv = n_real_parents > 1   # convergence OU → barre supplémentaire

        if not parents:
            # Orphelin avec cibles forward déjà calculées → placer AU-DESSUS de la cible
            fwd_placed_targets = [(dst, t) for dst, t in fwd_outs[n] if dst in step_y_map]
            if fwd_placed_targets:
                min_target_y = min(step_y_map[dst] for dst, _ in fwd_placed_targets)
                needed = step_h_map[n] + t_total_h + 20 + _ALT_V_GAP
                step_y_map[n] = max(50.0, min_target_y - needed)
            elif not step_y_map:
                step_y_map[n] = 50.0
            else:
                # Orphelin pur (aucune cible) : après tout ce qui est déjà placé
                step_y_map[n] = max(step_y_map.values()) + max(step_h_map.values()) + _ALT_V_GAP * 2
        else:
            min_y_vals = []
            for src, _ in parents:
                if src not in step_y_map:
                    continue   # parent orphelin pas encore calculé → ignorer
                src_bot = step_y_map[src] + step_h_map[src]
                # Utiliser le nombre total de branches (fwd + bck) pour cohérence avec 7b
                n_all_src = len(fwd_outs[src]) + len(back_outs[src])
                if n_all_src <= 1:
                    # Transition simple : étape arrive après un gap standard
                    y_after_t = src_bot + _ALT_V_GAP
                else:
                    # OrBar div : ob_y → t_y → étape (avec marges)
                    ob_y = src_bot + 10
                    t_y  = ob_y + t_total_h + 20
                    y_after_t = t_y + t_total_h + 20
                min_y_vals.append(y_after_t)
            if min_y_vals:
                base_y = max(min_y_vals)
                # Si convergence OU connue : ajouter l'espace pour la barre
                step_y_map[n] = base_y + (_conv_extra if needs_conv else 0)
                # Si des parents orphelins (non encore placés) doivent converger ici,
                # réserver l'espace pour leur barre de convergence future.
                unplaced_side = [src for src, _ in fwd_ins[n]
                                 if src not in step_y_map and src not in primary_set]
                if unplaced_side:
                    step_y_map[n] += _conv_extra + _ALT_V_GAP
            else:
                # Tous les parents sont orphelins non calculés → après le reste
                step_y_map[n] = (max(step_y_map.values()) + max(step_h_map.values()) + _ALT_V_GAP
                                 if step_y_map else 50.0)

    # ── 7. Construction des items ──────────────────────────────────────────
    col_main_x = _ALT_CX - _I_STEP_SZ // 2   # coin gauche de la colonne 0

    etapes_out:      list = []
    transitions_out: list = []
    or_bars_out:     list = []
    liaisons_out:    list = []
    trans_idx = 0
    ob_idx    = 0

    def _recept(t: dict) -> str:
        return t.get("receptivite") or t.get("condition") or "1"

    # 7a. Étapes ──────────────────────────────────────────────────────────
    for n in proc_topo:
        e   = step_by_num[n]
        c   = col_of.get(n, 0)
        ex  = col_main_x + c * _BS
        ey  = step_y_map[n]
        _nom = e.get("nom", "")
        _fam = ""
        for _part in reversed(_nom.split("_")):
            if _part and _part[0] in ("A", "D", "F") and len(_part) <= 3:
                _fam = _part[0]; break
        etapes_out.append({
            "num":      n,
            "label":    e.get("label") or e.get("nom", ""),
            "actions":  e.get("actions", []),
            "initiale": e.get("initiale", False),
            "famille":  _fam,
            "x": ex, "y": ey,
        })

    # 7b. Transitions et OrBars  (forward + back groupés par étape source) ─
    for n in proc_topo:
        fwd_ch = fwd_outs[n]           # [(dst, t)] en avant
        bck_ch = back_outs[n]          # [(dst, t)] retour
        all_ch = fwd_ch + bck_ch
        n_all  = len(all_ch)
        if n_all == 0:
            continue

        c_src   = col_of.get(n, 0)
        src_bot = step_y_map[n] + step_h_map[n]

        if n_all == 1:
            dst, t = all_ch[0]
            y_dst  = step_y_map[dst]
            # Transition centrée entre src et dst
            if y_dst > src_bot:
                t_y = (src_bot + y_dst - t_total_h) / 2
            else:
                # Back-edge : laisser assez d'espace pour que T soit clairement
                # séparée du bas de l'étape source (min 2×stub + marge)
                t_y = src_bot + _I_STUB_H * 2 + 10
            t_x = col_main_x + c_src * _BS
            transitions_out.append({
                "idx": trans_idx, "receptivite": _recept(t), "x": t_x, "y": t_y,
            })
            liaisons_out += [
                {"de": {"type": "etape", "num": n}, "de_port": "bottom",
                 "vers": {"type": "transition", "idx": trans_idx}, "vers_port": "top"},
                {"de": {"type": "transition", "idx": trans_idx}, "de_port": "bottom",
                 "vers": {"type": "etape", "num": dst}, "vers_port": "top"},
            ]
            trans_idx += 1

        else:
            # ── 1. DFS back-edges : un T individuel par branche retour ────────
            bck_t_y_base = src_bot + _I_STUB_H * 2 + 10
            for bck_i, (dst, t) in enumerate(bck_ch):
                t_x = col_main_x + c_src * _BS
                t_y = bck_t_y_base + bck_i * (t_total_h + 5)
                transitions_out.append({
                    "idx": trans_idx, "receptivite": _recept(t), "x": t_x, "y": t_y,
                })
                liaisons_out += [
                    {"de": {"type": "etape", "num": n}, "de_port": "bottom",
                     "vers": {"type": "transition", "idx": trans_idx}, "vers_port": "top"},
                    {"de": {"type": "transition", "idx": trans_idx}, "de_port": "bottom",
                     "vers": {"type": "etape", "num": dst}, "vers_port": "top"},
                ]
                trans_idx += 1

            # ── 2. Branches forward : OrBar (≥2) ou T simple (1) ─────────────
            fwd_sorted = sorted(fwd_ch, key=lambda dt: col_of.get(dt[0], 0))

            if len(fwd_sorted) == 0:
                pass  # seulement des back-edges, déjà traités

            elif len(fwd_sorted) == 1:
                dst, t = fwd_sorted[0]
                y_dst  = step_y_map[dst]
                t_y    = ((src_bot + y_dst - t_total_h) / 2 if y_dst > src_bot
                          else src_bot + _I_STUB_H * 2 + 10)
                t_x    = col_main_x + c_src * _BS
                transitions_out.append({
                    "idx": trans_idx, "receptivite": _recept(t), "x": t_x, "y": t_y,
                })
                liaisons_out += [
                    {"de": {"type": "etape", "num": n}, "de_port": "bottom",
                     "vers": {"type": "transition", "idx": trans_idx}, "vers_port": "top"},
                    {"de": {"type": "transition", "idx": trans_idx}, "de_port": "bottom",
                     "vers": {"type": "etape", "num": dst}, "vers_port": "top"},
                ]
                trans_idx += 1

            else:
                # OrBar div : uniquement les branches forward
                # c_min/c_max sur fwd destinations + source (garantit top_branch ≥ 0)
                dst_cols   = [col_of.get(dst, c_src) for dst, _ in fwd_sorted]
                c_min      = min(dst_cols + [c_src])
                c_max      = max(dst_cols + [c_src])
                n_br       = c_max - c_min + 1
                top_branch = c_src - c_min
                # Indices des branches réellement connectées (pas de stubs fantômes)
                active_branches = [col_of.get(dst, c_src) - c_min for dst, _ in fwd_sorted]

                ob_x = col_main_x + c_min * _BS
                ob_y = src_bot + 10
                or_bars_out.append({
                    "idx": ob_idx, "x": ob_x, "y": ob_y,
                    "branches": n_br, "branch_spacing": _BS, "role": "div",
                    "top_branch": top_branch, "active_branches": active_branches,
                })
                liaisons_out.append({
                    "de":   {"type": "etape",  "num": n},      "de_port": "bottom",
                    "vers": {"type": "or_bar", "idx": ob_idx}, "vers_port": "top",
                })
                div_idx = ob_idx;  ob_idx += 1
                t_y = ob_y + t_total_h + 20
                for dst, t in fwd_sorted:
                    col_dst = col_of.get(dst, c_src)
                    i       = col_dst - c_min
                    br_x    = col_main_x + col_dst * _BS
                    transitions_out.append({
                        "idx": trans_idx, "receptivite": _recept(t),
                        "x": br_x, "y": t_y,
                    })
                    liaisons_out += [
                        {"de":   {"type": "or_bar",    "idx": div_idx},   "de_port": f"branch_bottom_{i}",
                         "vers": {"type": "transition", "idx": trans_idx}, "vers_port": "top"},
                        {"de":   {"type": "transition", "idx": trans_idx}, "de_port": "bottom",
                         "vers": {"type": "etape",      "num": dst},      "vers_port": "top"},
                    ]
                    trans_idx += 1

    # ── 7c. Barres de convergence OU ──────────────────────────────────────
    # Pour chaque étape ayant plusieurs transitions entrantes (forward),
    # remplacer les liaisons directes T→E par T→conv_bar.branch→E.
    #
    # Structure cible :   T1 ─┐
    #                    T2 ─┤ OrBar conv ─► E_n
    #                    ...─┘
    t_map_x  = {t["idx"]: t["x"] for t in transitions_out}
    t_map_y  = {t["idx"]: t["y"] for t in transitions_out}

    for n in proc_topo:
        # Repérer les liaisons T.bottom → n.top (convergence candidates)
        conv_lias = [
            (i, l) for i, l in enumerate(liaisons_out)
            if (l["de"].get("type") == "transition"
                and l["de_port"] == "bottom"
                and l["vers"].get("type") == "etape"
                and l["vers"].get("num") == n
                and l["vers_port"] == "top")
        ]
        if len(conv_lias) < 2:
            continue   # pas de convergence OU

        # Trier les branches par x (gauche → droite)
        conv_lias.sort(key=lambda il: t_map_x.get(il[1]["de"]["idx"], 0))

        t_xs = [t_map_x[il[1]["de"]["idx"]] for il in conv_lias]
        cb_x = t_xs[0]                         # OrBar conv commence à la 1ère branche
        cb_bs = _BS

        # y de la barre : juste au-dessus de l'étape n
        e_n   = next(e for e in etapes_out if e["num"] == n)
        cb_y  = e_n["y"] - _conv_extra + 5    # t_total_h + gap laissé en step 6

        # Vérification de validité : toutes les transitions entrantes doivent être
        # AU-DESSUS de la barre de convergence (T.port_bottom.y < cb_y).
        _t_total = _I_STUB_H * 2 + _I_TRANS_H
        if any(t_map_y.get(il[1]["de"]["idx"], 0) + _t_total >= cb_y
               for il in conv_lias):
            continue  # cb_y trop haut → évite la liaison remontante incorrecte

        # Calcul des indices de branche basés sur la colonne réelle des T
        _t_cols    = [round((tx - col_main_x) / _BS) for tx in t_xs]
        if len(set(_t_cols)) < len(conv_lias):
            continue  # colonnes dupliquées → pas de barre de convergence
        _c_min_c   = min(_t_cols)
        _c_max_c   = max(_t_cols)
        _n_br_c    = _c_max_c - _c_min_c + 1
        _active_c  = [ci - _c_min_c for ci in _t_cols]
        _cb_x_c    = col_main_x + _c_min_c * _BS

        # out_branch : colonne de l'étape cible n
        _e_n_col = round((e_n["x"] - col_main_x) / _BS) if _BS > 0 else 0
        out_idx  = max(0, min(_e_n_col - _c_min_c, _n_br_c - 1))

        or_bars_out.append({
            "idx": ob_idx, "x": _cb_x_c, "y": cb_y,
            "branches": _n_br_c, "branch_spacing": _BS,
            "role": "conv", "out_branch": out_idx,
            "active_branches": _active_c,
        })
        conv_ob_idx = ob_idx
        ob_idx += 1

        # Supprimer les anciennes liaisons T→E et les remplacer
        idxs_to_remove = {i for i, _ in conv_lias}
        liaisons_out = [l for i, l in enumerate(liaisons_out) if i not in idxs_to_remove]

        for ci, (_, old_l) in zip(_t_cols, conv_lias):
            t_idx = old_l["de"]["idx"]
            br_i  = ci - _c_min_c   # indice basé sur la colonne réelle
            liaisons_out.append({
                "de":   {"type": "transition", "idx": t_idx}, "de_port": "bottom",
                "vers": {"type": "or_bar", "idx": conv_ob_idx}, "vers_port": f"branch_top_{br_i}",
            })

        liaisons_out.append({
            "de":   {"type": "or_bar", "idx": conv_ob_idx}, "de_port": f"branch_bottom_{out_idx}",
            "vers": {"type": "etape",  "num": n},           "vers_port": "top",
        })

    # ── Post-layout : détection et résolution des chevauchements par colonne ───────
    # Garantit un gap minimal _MIN_GAP entre deux éléments consécutifs.
    # Important : on ne déplace que les transitions/or_bars mal placés,
    # PAS les étapes (leurs y ont déjà été calculés avec les bonnes marges).
    _MIN_GAP = _I_STUB_H   # 10px minimum entre le bas d'un item et le haut du suivant

    # Regrouper les items par colonne (arrondi au _BS le plus proche)
    _col_items: dict[int, list] = defaultdict(list)
    for _e in etapes_out:
        _col = round((_e["x"] - col_main_x) / _BS) if _BS > 0 else 0
        _col_items[_col].append({"y": _e["y"], "h": step_h_map[_e["num"]], "ref": ("e", _e)})
    for _t in transitions_out:
        _col = round((_t["x"] - col_main_x) / _BS) if _BS > 0 else 0
        _col_items[_col].append({"y": _t["y"], "h": t_total_h, "ref": ("t", _t)})
    for _ob in or_bars_out:
        _col = round((_ob["x"] - col_main_x) / _BS) if _BS > 0 else 0
        _col_items[_col].append({"y": _ob["y"], "h": t_total_h, "ref": ("ob", _ob)})

    for _col_list in _col_items.values():
        _col_list.sort(key=lambda i: i["y"])
        for _idx in range(1, len(_col_list)):
            _prev = _col_list[_idx - 1]
            _curr = _col_list[_idx]
            _prev_bot = _prev["y"] + _prev["h"]
            _needed   = _prev_bot + _MIN_GAP
            if _curr["y"] < _needed:
                _delta = _needed - _curr["y"]
                _curr["y"] += _delta
                kind, ref = _curr["ref"]
                if kind == "t":
                    ref["y"] = _curr["y"]
                elif kind == "ob":
                    ref["y"] = _curr["y"]
                # Les étapes ne sont pas déplacées ici pour ne pas casser
                # les barres de convergence ; leurs positions sont fixées en step 6.

    return {
        "etapes":        etapes_out,
        "transitions":   transitions_out,
        "traitements":   [],
        "macros":        [],
        "or_bars":       or_bars_out,
        "parallel_bars": [],
        "connectors":    [],
        "liaisons":      liaisons_out,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Icônes dessinées pour la toolbox
# ══════════════════════════════════════════════════════════════════════════════
def _make_etape_icon(size: int = 32) -> QIcon:
    """Icône étape Grafcet : carré avec mèches haute et basse (comme une bougie)."""
    px = QPixmap(size, size)
    px.fill(QColor(0, 0, 0, 0))
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor("white"), 1.5)
    p.setPen(pen)
    cx = size // 2
    sq_t = size * 27 // 100
    sq_b = size * 73 // 100
    sq_l = size * 17 // 100
    sq_r = size * 83 // 100
    # Mèche haute
    p.drawLine(cx, 1, cx, sq_t)
    # Carré
    p.drawRect(sq_l, sq_t, sq_r - sq_l, sq_b - sq_t)
    # Mèche basse
    p.drawLine(cx, sq_b, cx, size - 2)
    p.end()
    return QIcon(px)


def _make_macro_icon(size: int = 32) -> QIcon:
    """Icône étape macro : carré avec double-barres internes et mèches haute/basse."""
    px = QPixmap(size, size)
    px.fill(QColor(0, 0, 0, 0))
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor("white"), 1.5)
    p.setPen(pen)
    cx = size // 2
    sq_t = size * 27 // 100
    sq_b = size * 73 // 100
    sq_l = size * 17 // 100
    sq_r = size * 83 // 100
    inner = max(3, size * 8 // 100)
    # Mèche haute
    p.drawLine(cx, 1, cx, sq_t)
    # Carré
    p.drawRect(sq_l, sq_t, sq_r - sq_l, sq_b - sq_t)
    # Lignes double-cadre (notation macro)
    p.drawLine(sq_l, sq_t + inner, sq_r, sq_t + inner)
    p.drawLine(sq_l, sq_b - inner, sq_r, sq_b - inner)
    # Mèche basse
    p.drawLine(cx, sq_b, cx, size - 2)
    p.end()
    return QIcon(px)


def _make_transition_icon(size: int = 32) -> QIcon:
    """Icône transition Grafcet : barre horizontale épaisse avec mèches haute/basse."""
    px = QPixmap(size, size)
    px.fill(QColor(0, 0, 0, 0))
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor("white"), 1.5)
    p.setPen(pen)
    cx = size // 2
    bar_y = size // 2
    bar_l = size * 15 // 100
    bar_r = size * 85 // 100
    # Mèche haute
    p.drawLine(cx, 1, cx, bar_y)
    # Barre épaisse (la transition)
    p.setPen(QPen(QColor("white"), 3))
    p.drawLine(bar_l, bar_y, bar_r, bar_y)
    p.setPen(pen)
    # Mèche basse
    p.drawLine(cx, bar_y, cx, size - 2)
    p.end()
    return QIcon(px)


class _EditTab(QWidget):
    """Onglet d'édition interactif : toolbox + scène + propriétés."""

    def __init__(self, g: dict, parent=None):
        super().__init__(parent)
        from core.view.grafcet.grafcet_editor import _PropertiesPanel
        self._scene    = GrafcetScene()
        self._tool_btns: dict[str, QPushButton] = {}
        self._PanelCls = _PropertiesPanel
        self._view: _GrafcetView | None = None
        self._setup_ui()
        self._scene.from_dict(_auto_layout(g))
        # Le fit initial est géré par _GrafcetView.showEvent (timing correct)

    def _setup_ui(self):
        vb = QVBoxLayout(self)
        vb.setContentsMargins(0, 0, 0, 0)
        vb.setSpacing(0)
        vb.addWidget(self._make_toolbox())   # barre d'outils horizontale en haut
        hb = QHBoxLayout()
        hb.setContentsMargins(0, 0, 0, 0)
        hb.setSpacing(0)
        hb.addWidget(self._make_view(), 1)
        props = self._PanelCls()
        props.setFixedWidth(200)
        props.setStyleSheet("background:#f8f9fa; border-left:1px solid #ddd;")
        hb.addWidget(props)
        self._scene.itemSelectionChanged.connect(props.show_item)
        vb.addLayout(hb, 1)
        self._select_tool(GrafcetScene.TOOL_SELECT)

    def _make_toolbox(self) -> QWidget:
        tb = QWidget()
        tb.setFixedHeight(52)
        tb.setStyleSheet(
            "background:#2c3e50;" + AppConfig.TOOLTIP_QSS
        )
        hb = QHBoxLayout(tb)
        hb.setContentsMargins(8, 4, 8, 4)
        hb.setSpacing(4)
                # (text_ou_None, icon_fn_ou_None, tooltip, tool_id, fsize)
        tools = [
            ("↖",  None,                  "Sélectionner / déplacer un élément",             GrafcetScene.TOOL_SELECT,        16),
            (None, _make_etape_icon,       "Étape — carré avec flèches entrée/sortie",       GrafcetScene.TOOL_ETAPE,         16),
            (None, _make_macro_icon,       "Étape macro — sous-programme Grafcet encapsulé", GrafcetScene.TOOL_MACRO,         16),
            (None, _make_transition_icon,  "Transition — barre avec flèches entrée/sortie",  GrafcetScene.TOOL_TRANSITION,    16),
            ("═",  None,                  "Divergence en OU — alternatives exclusives",      GrafcetScene.TOOL_OR_BAR,        14),
            ("≡",  None,                  "Convergence/divergence parallèle — simultanéité", GrafcetScene.TOOL_PARALLEL_BAR,  14),
            ("↕",  None,                  "Liaison / arc orienté entre étapes",              GrafcetScene.TOOL_LIAISON,       16),
            ("⊞",  None,                  "Boîte d'action — traitement associé à l'étape",  GrafcetScene.TOOL_TRAITEMENT,    16),
            ("▽",  None,                  "Renvoi sortant — suite sur autre page",            GrafcetScene.TOOL_CONNECTOR_OUT, 16),
            ("△",  None,                  "Renvoi entrant — reprise depuis autre page",       GrafcetScene.TOOL_CONNECTOR_IN,  16),
        ]
        style_tpl = (
            "QPushButton {{ color:white; font-size:{fsize}px; border:1px solid #555; "
            "background:#34495e; border-radius:3px; }}"
            "QPushButton:checked {{ background:#e67e22; border:2px solid #f39c12; }}"
            "QPushButton:hover:!checked {{ background:#5d6d7e; }}"
            "QPushButton:pressed {{ background:#2c3e50; }}"
        )
        for text, icon_fn, tooltip, tool_id, fsize in tools:
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setFixedSize(40, 40)
            btn.setStyleSheet(style_tpl.format(fsize=fsize) + AppConfig.TOOLTIP_QSS)
            btn.setToolTip(tooltip)
            if icon_fn is not None:
                btn.setIcon(icon_fn(28))
                btn.setIconSize(QSize(28, 28))
            else:
                btn.setText(text)
            btn.clicked.connect(lambda _chk, t=tool_id: self._select_tool(t))
            hb.addWidget(btn)
            self._tool_btns[tool_id] = btn
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color:#555;")
        hb.addWidget(sep)
        btn_fit = QPushButton("⌖")
        btn_fit.setFixedSize(40, 40)
        btn_fit.setStyleSheet(
            "QPushButton { color:#2ecc71; font-size:18px; border:1px solid #555; background:#34495e; border-radius:3px; }"
            "QPushButton:hover { background:#5d6d7e; }"
            "QPushButton:pressed { background:#2c3e50; }"
            + AppConfig.TOOLTIP_QSS
        )
        btn_fit.setToolTip("Tout afficher (Ctrl+Roulette = zoom, Espace = panoramique)")
        btn_fit.clicked.connect(lambda: self._view.fit_all() if self._view else None)
        hb.addWidget(btn_fit)
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet("color:#555;")
        hb.addWidget(sep2)
        btn_del = QPushButton("🗑")
        btn_del.setFixedSize(40, 40)
        btn_del.setStyleSheet(
            "QPushButton { color:#e74c3c; font-size:18px; border:1px solid #555; background:#34495e; border-radius:3px; }"
            "QPushButton:hover { background:#5d6d7e; }"
            "QPushButton:pressed { background:#2c3e50; }"
            + AppConfig.TOOLTIP_QSS
        )
        btn_del.setToolTip("Supprimer la sélection (Suppr)")
        btn_del.clicked.connect(self._scene.delete_selected)
        hb.addWidget(btn_del)
        hb.addStretch()
        return tb

    def _make_view(self) -> _GrafcetView:
        view = _GrafcetView(self._scene)
        view.setStyleSheet("background:white; border:none;")
        view.setBackgroundBrush(QBrush(QColor("#f9f9f9")))
        self._view = view
        return view

    def _select_tool(self, tool_id: str):
        self._scene.set_tool(tool_id)
        for tid, btn in self._tool_btns.items():
            btn.setChecked(tid == tool_id)

    def get_scene(self) -> GrafcetScene:
        return self._scene


# ══════════════════════════════════════════════════════════════════════════════
# Onglet de test — charge test_grafcet.json, bouton ⟳ Recharger
# ══════════════════════════════════════════════════════════════════════════════
class _TestTab(QWidget):
    """
    Onglet de test : charge test_grafcet.json, affiche le grafcet,
    et expose un bouton «⟳ Recharger» pour rafraîchir après modification
    manuelle du fichier JSON.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._json_path = _TEST_GRAFCET_PATH
        self._container_vb: QVBoxLayout | None = None
        self._status_lbl = QLabel()
        self._status_lbl.setWordWrap(True)
        self._status_lbl.setStyleSheet("font-size:9px; padding:2px 6px;")
        self._setup_ui()
        self._load()

    def _setup_ui(self):
        vb = QVBoxLayout(self)
        vb.setContentsMargins(0, 4, 0, 4)
        vb.setSpacing(4)

        # Barre du haut : chemin + bouton Recharger
        top = QHBoxLayout()
        top.setSpacing(6)
        path_lbl = QLabel(f"📄  {self._json_path}")
        path_lbl.setStyleSheet("font-size:8px; color:#555; font-style:italic;")
        path_lbl.setWordWrap(True)
        top.addWidget(path_lbl, 1)

        btn_reload = QPushButton("⟳  Recharger")
        btn_reload.setFixedHeight(28)
        btn_reload.setStyleSheet(
            "QPushButton { background:#2471a3; color:white; font-weight:bold;"
            " padding:2px 14px; border:none; border-radius:4px; }"
            "QPushButton:hover { background:#1a6fa0; }"
            "QPushButton:pressed { background:#154360; }"
        )
        btn_reload.setToolTip("Relit test_grafcet.json et rafraîchit l'affichage")
        btn_reload.clicked.connect(self._load)
        top.addWidget(btn_reload)
        vb.addLayout(top)

        vb.addWidget(self._status_lbl)

        # Zone centrale : recréée à chaque rechargement
        self._inner = QWidget()
        self._container_vb = QVBoxLayout(self._inner)
        self._container_vb.setContentsMargins(0, 0, 0, 0)
        vb.addWidget(self._inner, 1)

    def _load(self):
        """Lit le JSON et (re)crée l'_EditTab."""
        # Vider le contenu précédent
        if self._container_vb is not None:
            while self._container_vb.count():
                item = self._container_vb.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        try:
            with open(self._json_path, encoding="utf-8") as f:
                g = json.load(f)
            if "etapes" not in g or "transitions" not in g:
                raise ValueError("Clés 'etapes' et/ou 'transitions' manquantes")

            # Avertissements éventuels
            for w in g.get("avertissements", []):
                warn_lbl = QLabel(f"⚠  {w}")
                warn_lbl.setStyleSheet(
                    "background:#fff3cd; border:1px solid #ffc107;"
                    " padding:3px 8px; font-size:9px; color:#856404; border-radius:3px;"
                )
                warn_lbl.setWordWrap(True)
                self._container_vb.addWidget(warn_lbl)

            tab = _EditTab(g)
            self._container_vb.addWidget(tab, 1)

            nb_e = len(g["etapes"])
            nb_t = len(g["transitions"])
            self._status_lbl.setText(
                f"✅  {g.get('titre', g['nom'])}  —  {nb_e} étapes, {nb_t} transitions"
            )
            self._status_lbl.setStyleSheet(
                "font-size:9px; color:#1a5276; background:#e8f2fc;"
                " border-radius:3px; padding:2px 6px;"
            )

        except Exception as exc:
            err_lbl = QLabel(f"❌  Erreur : {exc}")
            err_lbl.setStyleSheet(
                "background:#fde8e8; border:1px solid #e74c3c;"
                " padding:4px 8px; color:#922b21; font-size:9px; border-radius:3px;"
            )
            err_lbl.setWordWrap(True)
            self._container_vb.addWidget(err_lbl)
            self._status_lbl.setText(f"❌  Impossible de charger {self._json_path}")
            self._status_lbl.setStyleSheet(
                "font-size:9px; color:#922b21; background:#fde8e8;"
                " border-radius:3px; padding:2px 6px;"
            )


class GenerationPalette(QWidget):
    closeRequested = pyqtSignal()
    grafcetAdded   = pyqtSignal(dict)   # émis quand un nouveau grafcet est créé inline
    generateRequested = pyqtSignal()    # bouton "Générer depuis GEMMA"

    def __init__(self, gs=None, gc=None, gpn=None, extra_grafcets=None):
        super().__init__()
        self._base_grafcets  = [g for g in [gs, gc, gpn] if g is not None]
        self._extra_grafcets = list(extra_grafcets or [])
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 8)
        layout.setSpacing(6)

        title = QLabel("⚙  GRAFCETS")
        title.setStyleSheet(
            "font-weight:bold; font-size:15px; color:#1a5276; padding-bottom:4px;"
        )
        layout.addWidget(title)

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(False)
        self._tabs.setStyleSheet("""
            QTabBar::tab {
                font-weight: bold;
                font-size: 11px;
                padding: 8px 20px;
                background: #d5d8dc;
                color: #555;
                border: 1px solid #bbb;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #2471a3;
                color: white;
                font-size: 12px;
                border-color: #1a5276;
            }
            QTabBar::tab:hover:!selected {
                background: #aed6f1;
                color: #1a5276;
            }
            QTabWidget::pane {
                border: 1px solid #bbb;
            }
        """)
        for g in self._base_grafcets + self._extra_grafcets:
            self._tabs.addTab(self._make_tab(g), g.get("titre", g["nom"]))

        # Onglet de test (toujours présent, rechargeable)
        self._test_tab = _TestTab()
        self._tabs.addTab(self._test_tab, "🧪 Test")

        layout.addWidget(self._tabs, 1)

        self._sep(layout)

        row = QHBoxLayout()
        row.setSpacing(6)

        _btn_style = """
            QPushButton {{
                background: {bg}; color: white; font-weight: bold;
                padding: 5px 12px; border: none; border-radius: 4px;
            }}
            QPushButton:hover {{ background: {hover}; }}
            QPushButton:pressed {{ background: {pressed}; }}
        """

        btn_gen = QPushButton("⚙  Générer depuis GEMMA")
        btn_gen.setStyleSheet(_btn_style.format(bg="#8e44ad", hover="#6c3483", pressed="#512e5f"))
        btn_gen.setToolTip("Génère automatiquement GS, GC et GPN depuis le GEMMA validé")
        btn_gen.clicked.connect(self.generateRequested.emit)
        btn_save = QPushButton("💾  Sauvegarder tout…")
        btn_save.setStyleSheet(_btn_style.format(bg="#27ae60", hover="#1e8449", pressed="#145a32"))
        btn_save.clicked.connect(self._save_all)
        btn_new = QPushButton("✏  Nouveau Grafcet")
        btn_new.setStyleSheet(_btn_style.format(bg="#2980b9", hover="#1a6fa0", pressed="#154360"))
        btn_new.setToolTip("Créer un nouveau Grafcet personnalisé")
        btn_new.clicked.connect(self._on_new_grafcet)
        btn_close = QPushButton("✖  Fermer")
        btn_close.setStyleSheet(_btn_style.format(bg="#c0392b", hover="#a93226", pressed="#7b241c"))
        btn_close.clicked.connect(self.closeRequested.emit)
        row.addWidget(btn_gen)
        row.addStretch()
        row.addWidget(btn_save)
        row.addWidget(btn_new)
        row.addWidget(btn_close)
        layout.addLayout(row)

    # ── Gestion des onglets ───────────────────────────────────────────────────
    def _on_new_grafcet(self):
        """Dialogue inline : saisir le nom, créer un onglet vide et l'émettre."""
        name, ok = QInputDialog.getText(self, "Nouveau Grafcet", "Nom du grafcet :")
        if not ok or not name.strip():
            return
        name = name.strip()
        g = {"nom": name, "titre": name, "description": "",
             "etapes": [], "transitions": [], "avertissements": []}
        self._add_tab(g)
        self.grafcetAdded.emit(g)

    def _add_tab(self, g: dict):
        """Ajoute un onglet pour `g` et le sélectionne."""
        self._extra_grafcets.append(g)
        self._tabs.addTab(self._make_tab(g), g.get("titre", g["nom"]))
        self._tabs.setCurrentIndex(self._tabs.count() - 1)

    def add_grafcet(self, g: dict):
        """API externe : ajouter un grafcet depuis le contrôleur."""
        self._add_tab(g)

    def focus_last(self):
        """Sélectionne le dernier onglet."""
        if self._tabs.count() > 0:
            self._tabs.setCurrentIndex(self._tabs.count() - 1)

    def _make_tab(self, g: dict) -> QWidget:
        container = QWidget()
        vb = QVBoxLayout(container)
        vb.setContentsMargins(0, 4, 0, 0)
        vb.setSpacing(4)

        for w in g.get("avertissements", []):
            lbl = QLabel(f"⚠  {w}")
            lbl.setStyleSheet(
                "background:#fff3cd; border:1px solid #ffc107; "
                "padding:3px 8px; font-size:9px; color:#856404; border-radius:3px;"
            )
            lbl.setWordWrap(True)
            vb.addWidget(lbl)

        lbl_desc = QLabel(g.get("description", "").replace("\n", "  ·  "))
        lbl_desc.setStyleSheet("font-size:9px; color:#555; font-style:italic; padding:0 4px;")
        lbl_desc.setWordWrap(True)
        vb.addWidget(lbl_desc)

        vb.addWidget(_EditTab(g), 1)

        row = QHBoxLayout()
        row.setSpacing(4)
        for label, fn in [
            ("📋 Copier texte", lambda _, gg=g: self._copy_text(gg)),
            ("📋 Copier IL/ST", lambda _, gg=g: self._copy_il(gg)),
            ("💾 Sauvegarder",  lambda _, gg=g: self._save_one(gg)),
        ]:
            btn = QPushButton(label)
            btn.clicked.connect(fn)
            row.addWidget(btn)
        vb.addLayout(row)

        return container

    def _copy_text(self, g):
        from PyQt6.QtWidgets import QApplication
        from core.utils.grafcet_generator import GrafcetGenerator
        QApplication.clipboard().setText(GrafcetGenerator.grafcet_to_text(g))

    def _copy_il(self, g):
        from PyQt6.QtWidgets import QApplication
        from core.utils.grafcet_generator import GrafcetGenerator
        QApplication.clipboard().setText(GrafcetGenerator.grafcet_to_structured_text(g))

    def _save_one(self, g):
        from core.utils.grafcet_generator import GrafcetGenerator
        path, _ = QFileDialog.getSaveFileName(
            self, f"Sauvegarder {g['nom']}",
            os.path.expanduser(f"~/{g['nom']}.txt"),
            "Texte (*.txt);;Tous (*.*)",
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(GrafcetGenerator.grafcet_to_text(g))
            f.write("\n\n" + "=" * 60 + "\nIL/ST IEC 61131-3\n" + "=" * 60 + "\n")
            f.write(GrafcetGenerator.grafcet_to_structured_text(g))

    def _save_all(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Dossier de sauvegarde", os.path.expanduser("~")
        )
        if not folder:
            return
        from core.utils.grafcet_generator import GrafcetGenerator
        for g in self._base_grafcets + self._extra_grafcets:
            if not g.get("etapes"):   # grafcet vide : skip le texte IL
                continue
            path = os.path.join(folder, f"{g['nom']}.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(GrafcetGenerator.grafcet_to_text(g))
                f.write("\n\n" + "=" * 60 + "\nIL/ST IEC 61131-3\n" + "=" * 60 + "\n")
                f.write(GrafcetGenerator.grafcet_to_structured_text(g))

    @staticmethod
    def _sep(layout):
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:#ddd;")
        layout.addWidget(sep)
