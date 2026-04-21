"""
grafcet_items.py — Éléments graphiques de l'éditeur de Grafcet.

  EtapeItem       : étape (rectangle numéroté + zone actions, double bord si initiale)
  TransitionItem  : barre horizontale + branche verticale + réceptivité
  LiaisonItem     : liaison orientée orthogonale (étape ↔ transition)
  TraitementItem  : boîte d'équations de sortie (ex: Monter = X1 + X2)
"""
from PyQt6.QtWidgets import QGraphicsObject
from PyQt6.QtCore import Qt, QRectF, QPointF, QRect
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath, QFontMetrics, QPolygonF as _QPolygonF,
)

# ── Dimensions ────────────────────────────────────────────────────────────────
_STEP_SZ    = 50     # côté du carré d'étape (norme IEC 848)
_TEXT_GAP   = 12     # espace entre le carré et la zone commentaire
_TEXT_W     = 230    # largeur de la zone commentaire / actions
_TEXT_LBL_H = 16     # hauteur de la ligne de label (guillemets)
_TEXT_ACT_H = 14     # hauteur d'une ligne d'action externe
_TRANS_W    = 50     # largeur barre de transition (= _STEP_SZ pour aligner les ports)
_TRANS_H    = 5      # épaisseur barre
_STUB_H     = 10     # longueur branche verticale haute/basse (courte)
_PORT_R   = 6        # rayon cercle de port (survol)
_SNAP_R   = 20       # distance de snap pour les liaisons
_GRID     = 20       # pas de la grille magnétique (pixels)
_LOOP_OFF = 60       # décalage latéral pour les boucles de retour
_TRAIT_W  = 180      # largeur boîte Traitement
_TRAIT_HDR = 26      # hauteur en-tête Traitement
_TRAIT_LH  = 17      # hauteur par ligne de code
_TRAIT_PAD = 5       # padding corps Traitement

# ── Dimensions éléments supplémentaires ───────────────────────────────────────────
_MACRO_H         = _STEP_SZ + 10    # hauteur d'une macro-étape
_OR_BAR_W        = 160              # largeur barre OU simple (1 branche, compat)
_PAR_BAR_W       = 160              # largeur double barre ET simple (1 branche, compat)
_PAR_GAP         = 6                # écart entre les deux barres parallèles
_CONN_W          = 80               # largeur d'un connecteur renvoi
_CONN_H          = 36               # hauteur d'un connecteur renvoi
_BRANCH_SPACING  = 160              # espacement centre-à-centre entre branches

# ── Couleurs ──────────────────────────────────────────────────────────────────
_C_STEP_HDR  = QColor("#d6eaf8")
_C_STEP_INIT = QColor("#7fb3d3")
_C_STEP_BODY = QColor("#f4f6f7")
_C_TRAIT_HDR = QColor("#d2b4de")
_C_TRAIT_BODY= QColor("#faf5ff")
_C_TRAIT_BRD = QColor("#7d3c98")
_C_BORDER    = QColor("#1a5276")
_C_SEL       = QColor("#e67e22")
_C_TRANS     = QColor("#1c2833")
_C_RECEPT    = QColor("#76448a")
_C_ACT       = QColor("#1e8449")
_C_PORT      = QColor("#e74c3c")
_C_LINK      = QColor("#2c3e50")

# ── Polices ───────────────────────────────────────────────────────────────────
_F_NUM    = QFont("Arial", 15, QFont.Weight.Bold)
_F_LABEL  = QFont("Arial", 8)
_F_ACT    = QFont("Courier New", 7)
_F_RECEPT = QFont("Arial", 8)
_F_RECEPT.setItalic(True)
_F_TRAIT_HDR = QFont("Arial", 8, QFont.Weight.Bold)
_F_TRAIT_CODE= QFont("Courier New", 8)

# ── Type tags ─────────────────────────────────────────────────────────────────
ITEM_ETAPE        = 0
ITEM_TRANSITION   = 1
ITEM_LIAISON      = 2
ITEM_TRAITEMENT   = 3
ITEM_MACRO        = 4   # macro-étape
ITEM_OR_BAR       = 5   # barre simple OU (divergence/convergence sélection)
ITEM_PARALLEL_BAR = 6   # double barre ET (parallèle simultané)
ITEM_CONNECTOR    = 7   # renvoi de liaison (▽ sortie / △ entrée)


# ══════════════════════════════════════════════════════════════════════════════
# Utilitaires
# ══════════════════════════════════════════════════════════════════════════════

def _arrowhead(tip: QPointF, direction: str = "down", size: int = 7) -> QPainterPath:
    s = size
    p = QPainterPath()
    if direction == "down":
        pts = [QPointF(tip.x() - s, tip.y() - s * 1.4),
               QPointF(tip.x() + s, tip.y() - s * 1.4), tip]
    elif direction == "up":
        pts = [QPointF(tip.x() - s, tip.y() + s * 1.4),
               QPointF(tip.x() + s, tip.y() + s * 1.4), tip]
    elif direction == "right":
        pts = [QPointF(tip.x() - s * 1.4, tip.y() - s),
               QPointF(tip.x() - s * 1.4, tip.y() + s), tip]
    else:  # left
        pts = [QPointF(tip.x() + s * 1.4, tip.y() - s),
               QPointF(tip.x() + s * 1.4, tip.y() + s), tip]
    p.moveTo(pts[0])
    p.lineTo(pts[1])
    p.lineTo(pts[2])
    p.closeSubpath()
    return p


# ══════════════════════════════════════════════════════════════════════════════
# EtapeItem
# ══════════════════════════════════════════════════════════════════════════════

class EtapeItem(QGraphicsObject):
    item_type = ITEM_ETAPE

    def __init__(self, numero: int = 1, label: str = "Étape",
                 actions=None, initiale: bool = False, famille: str = ""):
        super().__init__()
        self.numero   = numero
        self.label    = label
        self.actions  = list(actions or [])
        self.initiale = initiale
        self.famille  = famille   # 'A', 'D', 'F' ou '' pour défaut
        self._hover_port = None

        self.setFlags(
            QGraphicsObject.GraphicsItemFlag.ItemIsMovable    |
            QGraphicsObject.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsObject.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

    # ── Géométrie ─────────────────────────────────────────────────────────────
    def width(self) -> float:
        return float(_STEP_SZ + _TEXT_GAP + _TEXT_W)

    def height(self) -> float:
        n = max(0, len([a for a in self.actions if a.strip()]))
        lbl_h = _TEXT_LBL_H if self.label else 0
        text_h = lbl_h + n * _TEXT_ACT_H + 4
        return max(float(_STEP_SZ), float(text_h))

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.width(), self.height())

    # ── Ports : centre haut / bas du CARRÉ (pas du bounding rect) ─────────────
    def port_top(self) -> QPointF:
        return self.mapToScene(QPointF(_STEP_SZ / 2, 0.0))

    def port_bottom(self) -> QPointF:
        return self.mapToScene(QPointF(_STEP_SZ / 2, float(_STEP_SZ)))

    def nearest_port(self, scene_pos: QPointF):
        """Retourne (port_name, distance)."""
        top = self.port_top()
        bot = self.port_bottom()
        dt = (scene_pos - top).manhattanLength()
        db = (scene_pos - bot).manhattanLength()
        return ("top", dt) if dt < db else ("bottom", db)

    # ── Dessin ────────────────────────────────────────────────────────────────
    def paint(self, painter: QPainter, option, widget=None):
        is_sel = self.isSelected()

        # Couleurs par famille
        _FAM = {
            "D": ("#fce4e4", "#922b21"),
            "A": ("#e8f8ed", "#1a5928"),
            "F": ("#e8f2fc", "#1a5276"),
        }
        fill_s, brd_s = _FAM.get(self.famille, ("#f5f5f5", "#1a5276"))
        brd_col  = _C_SEL if is_sel else QColor(brd_s)
        fill_col = QColor(fill_s)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # ── Carré de l'étape (IEC 848) ────────────────────────────────────────
        painter.setPen(QPen(brd_col, 2.0 if is_sel else 1.8))
        painter.setBrush(QBrush(fill_col))
        painter.drawRect(QRectF(0, 0, _STEP_SZ, _STEP_SZ))

        # Double bord si étape initiale
        if self.initiale:
            ins = 5
            painter.setPen(QPen(brd_col, 1.4))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(QRectF(ins, ins, _STEP_SZ - 2*ins, _STEP_SZ - 2*ins))

        # ── Numéro centré dans le carré ───────────────────────────────────────
        painter.setFont(_F_NUM)
        painter.setPen(QPen(brd_col))
        fm = QFontMetrics(_F_NUM)
        num_s = str(self.numero)
        tw = fm.horizontalAdvance(num_s)
        painter.drawText(
            int(_STEP_SZ / 2 - tw / 2),
            int(_STEP_SZ / 2 + fm.ascent() / 2 - 1),
            num_s,
        )

        # ── Zone texte à droite : label (commentaire) puis actions ────────────
        tx = int(_STEP_SZ + _TEXT_GAP)
        ty = 6
        if self.label:
            f_lbl = QFont("Arial", 8)
            f_lbl.setItalic(True)
            painter.setFont(f_lbl)
            painter.setPen(QPen(QColor("#444444")))
            painter.drawText(tx, ty + 12, f'«\u202f{self.label}\u202f»')
            ty += _TEXT_LBL_H

        painter.setFont(_F_ACT)
        painter.setPen(QPen(_C_ACT))
        for action in self.actions:
            if action.strip():
                painter.drawText(tx, ty + 11, action)
                ty += _TEXT_ACT_H

        # ── Port de survol ────────────────────────────────────────────────────
        if self._hover_port:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(_C_PORT))
            py = 0.0 if self._hover_port == "top" else float(_STEP_SZ)
            painter.drawEllipse(QPointF(_STEP_SZ / 2, py), _PORT_R, _PORT_R)

    # ── Survol ────────────────────────────────────────────────────────────────
    def hoverMoveEvent(self, event):
        pos = event.pos()
        cx = _STEP_SZ / 2
        if abs(pos.x() - cx) < 15 and abs(pos.y()) < 12:
            self._hover_port = "top"
        elif abs(pos.x() - cx) < 15 and abs(pos.y() - _STEP_SZ) < 12:
            self._hover_port = "bottom"
        else:
            self._hover_port = None
        self.update()

    def hoverLeaveEvent(self, event):
        self._hover_port = None
        self.update()

    # ── Notification déplacement ──────────────────────────────────────────────
    def itemChange(self, change, value):
        if change == QGraphicsObject.GraphicsItemChange.ItemPositionChange:
            # Snap à la grille
            x = round(value.x() / _GRID) * _GRID
            y = round(value.y() / _GRID) * _GRID
            return QPointF(x, y)
        if change == QGraphicsObject.GraphicsItemChange.ItemPositionHasChanged:
            sc = self.scene()
            if sc and hasattr(sc, "update_liaisons_for"):
                sc.update_liaisons_for(self)
        return super().itemChange(change, value)


# ══════════════════════════════════════════════════════════════════════════════
# TransitionItem
# ══════════════════════════════════════════════════════════════════════════════

class TransitionItem(QGraphicsObject):
    item_type = ITEM_TRANSITION

    def __init__(self, receptivite: str = "1"):
        super().__init__()
        self.receptivite  = receptivite
        self._hover_port  = None

        self.setFlags(
            QGraphicsObject.GraphicsItemFlag.ItemIsMovable    |
            QGraphicsObject.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsObject.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

    # ── Géométrie ─────────────────────────────────────────────────────────────
    def cx(self) -> float:
        return _TRANS_W / 2

    def total_height(self) -> float:
        return _STUB_H * 2 + _TRANS_H

    def boundingRect(self) -> QRectF:
        # La barre fait _TRANS_W, la réceptivité s'étend 220px à droite
        return QRectF(-4, -4, _TRANS_W + 220, self.total_height() + 8)

    # ── Ports ─────────────────────────────────────────────────────────────────
    def port_top(self) -> QPointF:
        return self.mapToScene(QPointF(self.cx(), 0))

    def port_bottom(self) -> QPointF:
        return self.mapToScene(QPointF(self.cx(), self.total_height()))

    def nearest_port(self, scene_pos: QPointF):
        top = self.port_top()
        bot = self.port_bottom()
        dt = (scene_pos - top).manhattanLength()
        db = (scene_pos - bot).manhattanLength()
        return ("top", dt) if dt < db else ("bottom", db)

    # ── Dessin ────────────────────────────────────────────────────────────────
    def paint(self, painter: QPainter, option, widget=None):
        is_sel = self.isSelected()
        cx = self.cx()
        bar_y = _STUB_H

        pen = QPen(_C_SEL if is_sel else _C_TRANS, 2 if is_sel else 1.5)
        painter.setPen(pen)

        # Branche verticale haute
        painter.drawLine(int(cx), 0, int(cx), int(bar_y))
        # Branche verticale basse
        painter.drawLine(int(cx), int(bar_y + _TRANS_H), int(cx), int(self.total_height()))
        # Barre horizontale
        painter.fillRect(0, int(bar_y), _TRANS_W, _TRANS_H,
                         _C_SEL if is_sel else _C_TRANS)

        # Réceptivité dans une bulle arrondie
        if self.receptivite:
            painter.setFont(_F_RECEPT)
            fm_r = painter.fontMetrics()
            tw_r = fm_r.horizontalAdvance(self.receptivite)
            th_r = fm_r.height()
            rx = int(cx) + _TRANS_W // 2 + 8
            ry = int(bar_y + _TRANS_H // 2) - th_r // 2 - 3
            rw = tw_r + 10
            rh = th_r + 6
            painter.setPen(QPen(QColor("#76448a"), 1))
            painter.setBrush(QBrush(QColor("#f5eef8")))
            painter.drawRoundedRect(rx, ry, rw, rh, 5, 5)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(_C_RECEPT))
            painter.drawText(rx + 5, ry + fm_r.ascent() + 3, self.receptivite)

        # Port visuel (survol)
        if self._hover_port:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(_C_PORT))
            py = 0.0 if self._hover_port == "top" else self.total_height()
            painter.drawEllipse(QPointF(cx, py), _PORT_R, _PORT_R)

    def hoverMoveEvent(self, event):
        pos = event.pos()
        cx = self.cx()
        h = self.total_height()
        if abs(pos.x() - cx) < 15 and abs(pos.y()) < 10:
            self._hover_port = "top"
        elif abs(pos.x() - cx) < 15 and abs(pos.y() - h) < 10:
            self._hover_port = "bottom"
        else:
            self._hover_port = None
        self.update()

    def hoverLeaveEvent(self, event):
        self._hover_port = None
        self.update()

    def itemChange(self, change, value):
        if change == QGraphicsObject.GraphicsItemChange.ItemPositionChange:
            # Snap à la grille
            x = round(value.x() / _GRID) * _GRID
            y = round(value.y() / _GRID) * _GRID
            return QPointF(x, y)
        if change == QGraphicsObject.GraphicsItemChange.ItemPositionHasChanged:
            sc = self.scene()
            if sc and hasattr(sc, "update_liaisons_for"):
                sc.update_liaisons_for(self)
        return super().itemChange(change, value)


# ══════════════════════════════════════════════════════════════════════════════
# LiaisonItem
# ══════════════════════════════════════════════════════════════════════════════

class LiaisonItem(QGraphicsObject):
    """
    Liaison orientée orthogoale entre un port d’une étape et un port d’une
    transition. Dessinée manuellement (QGraphicsObject) pour garantir :
      - segments strictement H ou V (jamais obliques)
      - routage en boucle de retour via côté gauche
    """
    item_type = ITEM_LIAISON

    def __init__(self, src_item, src_port: str, dst_item, dst_port: str):
        super().__init__()
        self.src_item = src_item
        self.src_port = src_port
        self.dst_item = dst_item
        self.dst_port = dst_port

        self._segs: list[tuple[QPointF, QPointF]] = []
        self._arrow: list[QPointF] = []
        self._brect  = QRectF()

        # Offset ajustable par l'utilisateur (drag du segment mobile)
        self._mid_y_offset: float = 0.0   # décalage V du segment H (liaison normale)
        self._loop_x_offset: float = 0.0  # décalage H de la branche gauche (boucle)
        self._is_back_loop   = False
        self._h_seg_y: float | None = None  # Y scène du segment H draggable

        # Drag interne (segment mobile)
        self._drag_seg  = False
        self._drag_prev: QPointF | None = None

        self.setFlags(
            QGraphicsObject.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsObject.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setZValue(-1)
        self.update_path()

    # ── Résolution des ports ──────────────────────────────────────────────────
    @staticmethod
    def _resolve_port(item, port_name: str) -> "QPointF":
        """
        Résout un nom de port en position scène.
        Ports standard : "top" / "bottom"
        Ports de branche : "branch_top_N" / "branch_bottom_N"
        """
        if port_name.startswith("branch_"):
            # "branch_top_2" → side="top", idx=2
            parts = port_name.split("_")   # ["branch", "top"/"bottom", "N"]
            side = parts[1]
            idx  = int(parts[2])
            bx   = item.branch_x(idx)
            by   = 0.0 if side == "top" else item.total_height()
            return item.mapToScene(QPointF(bx, by))
        return getattr(item, f"port_{port_name}")()

    # ── Mise à jour ──────────────────────────────────────────────────────────────────────
    def update_path(self):
        try:
            src_pt = self._resolve_port(self.src_item, self.src_port)
            dst_pt = self._resolve_port(self.dst_item, self.dst_port)
        except (RuntimeError, AttributeError, IndexError, ValueError):
            return
        self.prepareGeometryChange()
        self._compute(src_pt, dst_pt)
        self.update()

    def _compute(self, src: QPointF, dst: QPointF):
        """Calcule les segments (strictement H/V) et la flèche."""
        A  = 9
        DW = 20
        pre = QPointF(dst.x(), dst.y() - A)

        back_loop = src.y() >= dst.y() - 5
        self._is_back_loop = back_loop

        if not back_loop:
            # Pas de flèche → le trait doit atteindre dst directement
            if abs(src.x() - dst.x()) < 10:   # tolérance snap grille
                pts = [QPointF(src.x(), src.y()), QPointF(src.x(), dst.y())]
                self._h_seg_y = None
            else:
                mid_y = (src.y() + dst.y()) / 2 + self._mid_y_offset
                self._h_seg_y = mid_y
                pts = [
                    src,
                    QPointF(src.x(), mid_y),
                    QPointF(dst.x(), mid_y),
                    dst,
                ]
        else:
            # Flèche présente → on s'arrête à pre, la pointe complète jusqu'à dst
            lx = min(src.x(), dst.x()) - _LOOP_OFF + self._loop_x_offset
            self._h_seg_y = None
            pts = [
                src,
                QPointF(src.x(), src.y() + DW),
                QPointF(lx,      src.y() + DW),
                QPointF(lx,      dst.y() - A),
                pre,
            ]

        self._segs = list(zip(pts, pts[1:]))

        # Flèche uniquement sur les liaisons remontantes (retour/boucle)
        s = 7
        if back_loop:
            self._arrow = [
                QPointF(dst.x() - s, dst.y() - s * 1.5),
                QPointF(dst.x() + s, dst.y() - s * 1.5),
                dst,
            ]
        else:
            self._arrow = []   # pas de pointe sur les liaisons descendantes

        # Bounding rect (marge agrandie pour inclure le handle de drag)
        all_pts = pts + self._arrow
        xs = [p.x() for p in all_pts]
        ys = [p.y() for p in all_pts]
        m = 12
        self._brect = QRectF(min(xs) - m, min(ys) - m,
                             max(xs) - min(xs) + 2 * m,
                             max(ys) - min(ys) + 2 * m)

    # ── Qt interface ─────────────────────────────────────────────────────────
    def boundingRect(self) -> QRectF:
        return self._brect

    def paint(self, painter: QPainter, option, widget=None):
        is_sel = self.isSelected()
        color  = _C_SEL if is_sel else _C_LINK

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(color, 2.0 if is_sel else 1.4, Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.FlatCap, Qt.PenJoinStyle.MiterJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for p1, p2 in self._segs:
            painter.drawLine(p1, p2)

        # Flèche uniquement sur les boucles de retour (liaisons remontantes)
        if self._arrow:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawPolygon(_QPolygonF(self._arrow))

        # Handle de drag : petit losange orange sur le segment mobile (si sélectionné)
        if is_sel:
            handle_pt = self._drag_handle_scene_pos()
            if handle_pt is not None:
                r = 6
                painter.setBrush(QBrush(QColor("#e67e22")))
                painter.setPen(QPen(QColor("#a04000"), 1))
                diamond = _QPolygonF([
                    QPointF(handle_pt.x(),     handle_pt.y() - r),
                    QPointF(handle_pt.x() + r, handle_pt.y()),
                    QPointF(handle_pt.x(),     handle_pt.y() + r),
                    QPointF(handle_pt.x() - r, handle_pt.y()),
                ])
                painter.drawPolygon(diamond)

    def _drag_handle_scene_pos(self) -> "QPointF | None":
        """Position scène du handle de drag, ou None si pas de segment mobile."""
        if not self._segs:
            return None
        if self._is_back_loop:
            # Milieu de la branche gauche verticale (segment [2] : H vers V gauche)
            if len(self._segs) >= 3:
                p1, p2 = self._segs[2]  # V-gauche haut→bas
                return QPointF((p1.x() + p2.x()) / 2, (p1.y() + p2.y()) / 2)
        elif self._h_seg_y is not None:
            # Milieu du segment H (segment [1])
            if len(self._segs) >= 2:
                p1, p2 = self._segs[1]
                return QPointF((p1.x() + p2.x()) / 2, (p1.y() + p2.y()) / 2)
        return None

    # ── Drag du segment mobile ─────────────────────────────────────────────────
    def mousePressEvent(self, event):
        # Un clic n'importe où sur la liaison active le drag si un segment est mobile
        if self._drag_handle_scene_pos() is not None:
            self._drag_seg  = True
            self._drag_prev = event.scenePos()
        # On passe aussi au super pour gérer la sélection
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_seg and self._drag_prev is not None:
            delta = event.scenePos() - self._drag_prev
            if self._is_back_loop:
                self._loop_x_offset += delta.x()
            elif self._h_seg_y is not None:
                self._mid_y_offset += delta.y()
            self._drag_prev = event.scenePos()
            self.update_path()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_seg  = False
        self._drag_prev = None
        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsObject.GraphicsItemChange.ItemSelectedChange:
            self.update()
        return super().itemChange(change, value)


# ══════════════════════════════════════════════════════════════════════════════
# TraitementItem  — boîte d'équations de sortie
# ══════════════════════════════════════════════════════════════════════════════

class TraitementItem(QGraphicsObject):
    """
    Boîte rectangulaire représentant des équations de sortie.
    Exemple : Monter = X1 + X2   (X1 = étape n°1)
    """
    item_type = ITEM_TRAITEMENT

    def __init__(self, titre: str = "Traitement", lignes: list | None = None):
        super().__init__()
        self.titre  = titre
        self.lignes: list[str] = lignes or []
        self.setFlags(
            QGraphicsObject.GraphicsItemFlag.ItemIsMovable |
            QGraphicsObject.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsObject.GraphicsItemFlag.ItemSendsGeometryChanges
        )

    # ── Géométrie ─────────────────────────────────────────────────────────────
    def width(self) -> float:
        return _TRAIT_W

    def height(self) -> float:
        n = max(1, len(self.lignes))
        return _TRAIT_HDR + _TRAIT_PAD + n * _TRAIT_LH + _TRAIT_PAD

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.width(), self.height())

    # ── Dessin ────────────────────────────────────────────────────────────────
    def paint(self, painter: QPainter, option, widget=None):
        w, h = self.width(), self.height()
        is_sel = self.isSelected()
        border = _C_SEL if is_sel else _C_TRAIT_BRD
        lw     = 2.0 if is_sel else 1.5

        # Corps
        painter.setPen(QPen(border, lw))
        painter.setBrush(QBrush(_C_TRAIT_BODY))
        painter.drawRect(QRectF(0, 0, w, h))

        # En-tête
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(_C_TRAIT_HDR))
        painter.drawRect(QRectF(0, 0, w, _TRAIT_HDR))

        # Ligne de séparation en-tête/corps
        painter.setPen(QPen(border, lw))
        painter.drawLine(QPointF(0, _TRAIT_HDR), QPointF(w, _TRAIT_HDR))

        # Titre
        painter.setFont(_F_TRAIT_HDR)
        painter.setPen(QPen(QColor("#4a235a")))
        painter.drawText(
            QRectF(4, 0, w - 8, _TRAIT_HDR),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self.titre,
        )

        # Lignes de code
        painter.setFont(_F_TRAIT_CODE)
        painter.setPen(QPen(QColor("#1a1a1a")))
        for i, line in enumerate(self.lignes):
            y = _TRAIT_HDR + _TRAIT_PAD + i * _TRAIT_LH
            painter.drawText(
                QRectF(6, y, w - 12, _TRAIT_LH),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                line,
            )

    # ── Snap grille + notification liaisons ───────────────────────────────────
    def itemChange(self, change, value):
        if change == QGraphicsObject.GraphicsItemChange.ItemPositionChange:
            value = QPointF(
                round(value.x() / _GRID) * _GRID,
                round(value.y() / _GRID) * _GRID,
            )
        elif change == QGraphicsObject.GraphicsItemChange.ItemPositionHasChanged:
            sc = self.scene()
            if sc and hasattr(sc, "update_liaisons_for"):
                sc.update_liaisons_for(self)
        return super().itemChange(change, value)

# ════════════════════════════════════════════════════════════════════════════════
# MacroItem  — macro-étape
# ════════════════════════════════════════════════════════════════════════════════

class MacroItem(QGraphicsObject):
    """
    Macro-étape numérotée encapsulant un sous-grafcet.
    Rendue par un rectangle à double bordure avec indicateur « M ».
    """
    item_type = ITEM_MACRO

    def __init__(self, numero: int = 1, label: str = "Macro"):
        super().__init__()
        self.numero  = numero
        self.label   = label
        self._hover_port = None
        self.setFlags(
            QGraphicsObject.GraphicsItemFlag.ItemIsMovable    |
            QGraphicsObject.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsObject.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

    def width(self)  -> float: return _STEP_W
    def height(self) -> float: return _MACRO_H

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.width(), self.height())

    def port_top(self)    -> QPointF:
        return self.mapToScene(QPointF(self.width() / 2, 0))
    def port_bottom(self) -> QPointF:
        return self.mapToScene(QPointF(self.width() / 2, self.height()))

    def nearest_port(self, scene_pos: QPointF):
        top = self.port_top();  dt = (scene_pos - top).manhattanLength()
        bot = self.port_bottom(); db = (scene_pos - bot).manhattanLength()
        return ("top", dt) if dt < db else ("bottom", db)

    def paint(self, painter: QPainter, option, widget=None):
        w, h = self.width(), self.height()
        is_sel = self.isSelected()
        painter.fillRect(0, 0, w, h, QColor("#fdfefe"))
        painter.setPen(QPen(_C_SEL if is_sel else _C_BORDER, 2 if is_sel else 1.5))
        painter.drawRect(0, 0, w, h)
        ins = 4
        painter.setPen(QPen(_C_BORDER, 1.2))
        painter.drawRect(ins, ins, w - 2 * ins, h - 2 * ins)
        f_m = QFont("Arial", 9, QFont.Weight.Bold)
        painter.setFont(f_m)
        painter.setPen(QPen(QColor("#884ea0")))
        painter.drawText(w - 18, 14, "M")
        painter.setFont(_F_NUM)
        painter.setPen(QPen(_C_BORDER))
        painter.drawText(6, h - 6, str(self.numero))
        painter.setFont(_F_LABEL)
        painter.setPen(QPen(QColor("#1c2833")))
        from PyQt6.QtCore import QRect
        painter.drawText(
            QRect(28, 4, w - 36, h - 8),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            | Qt.TextFlag.TextWordWrap,
            self.label,
        )
        if self._hover_port:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(_C_PORT))
            py = 0 if self._hover_port == "top" else h
            painter.drawEllipse(QPointF(w / 2, py), _PORT_R, _PORT_R)

    def hoverMoveEvent(self, event):
        pos = event.pos(); w, h = self.width(), self.height()
        if abs(pos.x() - w / 2) < 15 and abs(pos.y()) < 10:
            self._hover_port = "top"
        elif abs(pos.x() - w / 2) < 15 and abs(pos.y() - h) < 10:
            self._hover_port = "bottom"
        else:
            self._hover_port = None
        self.update()

    def hoverLeaveEvent(self, event):
        self._hover_port = None; self.update()

    def itemChange(self, change, value):
        if change == QGraphicsObject.GraphicsItemChange.ItemPositionChange:
            x = round(value.x() / _GRID) * _GRID
            y = round(value.y() / _GRID) * _GRID
            return QPointF(x, y)
        if change == QGraphicsObject.GraphicsItemChange.ItemPositionHasChanged:
            sc = self.scene()
            if sc and hasattr(sc, "update_liaisons_for"):
                sc.update_liaisons_for(self)
        return super().itemChange(change, value)


# ════════════════════════════════════════════════════════════════════════════════
# ════════════════════════════════════════════════════════════════════════════════
# OrBarItem  — barre simple OU (divergence/convergence en sélection)
# ════════════════════════════════════════════════════════════════════════════════

class OrBarItem(QGraphicsObject):
    """
    Barre horizontale simple — divergence/convergence en OU (sélection).

    Parameters
    ----------
    branches       : nombre de branches parallèles (1 = barre simple compat, 2+ = div/conv)
    branch_spacing : espacement centre-à-centre entre branches (px)
    role           : "div"  → stub central en haut + stubs branches en bas  (divergence)
                     "conv" → stubs branches en haut + stub central en bas   (convergence)
                     "both" → tous les stubs (compat ancien comportement)
    """
    item_type = ITEM_OR_BAR

    def __init__(self, branches: int = 2, branch_spacing: int = _BRANCH_SPACING, role: str = "div",
                 out_branch: int = 0, top_branch: int = 0, active_branches: list = None):
        super().__init__()
        self.branches        = branches
        self.branch_spacing  = branch_spacing
        self.role            = role
        self.out_branch      = out_branch
        self.top_branch      = top_branch
        # Indices des branches avec stubs de sortie réels (évite les stubs fantômes).
        # None = toutes les branches sont actives.
        self.active_branches = active_branches
        self._hover_port     = None
        self.setFlags(
            QGraphicsObject.GraphicsItemFlag.ItemIsMovable    |
            QGraphicsObject.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsObject.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

    # ── Géométrie ─────────────────────────────────────────────────────────────
    @property
    def bar_width(self) -> float:
        if self.branches <= 1:
            return float(_OR_BAR_W)
        return (self.branches - 1) * self.branch_spacing + _STEP_SZ

    def cx(self)           -> float: return self.bar_width / 2
    def total_height(self) -> float: return _STUB_H * 2 + _TRANS_H

    def branch_x(self, i: int) -> float:
        """Coordonnée X locale du centre de la branche i."""
        if self.branches <= 1:
            return self.cx()
        return _STEP_SZ / 2 + i * self.branch_spacing

    def boundingRect(self) -> QRectF:
        return QRectF(-4, -4, self.bar_width + 8, self.total_height() + 8)

    # ── Ports ─────────────────────────────────────────────────────────────────
    def port_top(self)    -> QPointF:
        # Pour div : l'entrée est alignée sur top_branch (même col que l'étape source)
        if self.role == "div":
            return self.mapToScene(QPointF(self.branch_x(self.top_branch), 0.0))
        return self.mapToScene(QPointF(self.cx(), 0.0))
    def port_bottom(self) -> QPointF:
        # Pour conv : la sortie est alignée sur out_branch (même col que l'étape destination)
        if self.role == "conv":
            return self.mapToScene(QPointF(self.branch_x(self.out_branch), self.total_height()))
        return self.mapToScene(QPointF(self.cx(), self.total_height()))

    def nearest_port(self, scene_pos: QPointF):
        candidates = [("top", self.port_top()), ("bottom", self.port_bottom())]
        for i in range(self.branches):
            bx = self.branch_x(i)
            candidates.append((f"branch_top_{i}",    self.mapToScene(QPointF(bx, 0))))
            candidates.append((f"branch_bottom_{i}", self.mapToScene(QPointF(bx, self.total_height()))))
        best_name, best_pt = min(candidates, key=lambda c: (scene_pos - c[1]).manhattanLength())
        return best_name, (scene_pos - best_pt).manhattanLength()

    # ── Dessin ────────────────────────────────────────────────────────────────
    def paint(self, painter: QPainter, option, widget=None):
        is_sel = self.isSelected()
        cx    = self.cx()
        bw    = int(self.bar_width)
        bar_y = _STUB_H
        c     = _C_SEL if is_sel else _C_TRANS
        painter.setPen(QPen(c, 2 if is_sel else 1.5))

        # Barre horizontale fine (trait unique, pas un rectangle rempli)
        painter.drawLine(0, bar_y, bw, bar_y)

        # Stub entrant (en haut pour div : aligné sur top_branch ; both : au centre)
        if self.role == "div":
            painter.drawLine(int(self.branch_x(self.top_branch)), 0, int(self.branch_x(self.top_branch)), bar_y)
        elif self.role == "both":
            painter.drawLine(int(cx), 0, int(cx), bar_y)
        # Stub sortant (en bas pour conv : aligné sur branch_x(out_branch) ; both : au centre)
        if self.role == "conv":
            painter.drawLine(int(self.branch_x(self.out_branch)), bar_y,
                             int(self.branch_x(self.out_branch)), int(self.total_height()))
        elif self.role == "both":
            painter.drawLine(int(cx), bar_y, int(cx), int(self.total_height()))

        # Stubs de branches : seulement aux indices connectés (évite les stubs fantômes)
        active = self.active_branches if self.active_branches is not None else range(self.branches)
        for i in active:
            bx = int(self.branch_x(i))
            if self.role in ("conv", "both"):
                painter.drawLine(bx, 0, bx, bar_y)
            if self.role in ("div", "both"):
                painter.drawLine(bx, bar_y, bx, int(self.total_height()))

        # Port survolé
        if self._hover_port:
            pt = self._local_port_pos(self._hover_port)
            if pt is not None:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(_C_PORT))
                painter.drawEllipse(pt, _PORT_R, _PORT_R)

    def _local_port_pos(self, port_name: str):
        """Retourne la position locale (item coords) d'un port par son nom."""
        if port_name == "top":
            return QPointF(self.cx(), 0)
        if port_name == "bottom":
            return QPointF(self.cx(), self.total_height())
        if port_name.startswith("branch_"):
            parts = port_name.split("_")
            if len(parts) == 3:
                try:
                    idx = int(parts[2])
                    by  = 0.0 if parts[1] == "top" else self.total_height()
                    return QPointF(self.branch_x(idx), by)
                except (ValueError, IndexError):
                    pass
        return None

    # ── Survol ────────────────────────────────────────────────────────────────
    def hoverMoveEvent(self, event):
        best_name, _ = self.nearest_port(self.mapToScene(event.pos()))
        self._hover_port = best_name
        self.update()

    def hoverLeaveEvent(self, event):
        self._hover_port = None
        self.update()

    # ── Snap sur grille ───────────────────────────────────────────────────────
    def itemChange(self, change, value):
        if change == QGraphicsObject.GraphicsItemChange.ItemPositionChange:
            x = round(value.x() / _GRID) * _GRID
            y = round(value.y() / _GRID) * _GRID
            return QPointF(x, y)
        if change == QGraphicsObject.GraphicsItemChange.ItemPositionHasChanged:
            sc = self.scene()
            if sc and hasattr(sc, "update_liaisons_for"):
                sc.update_liaisons_for(self)
        return super().itemChange(change, value)


# ════════════════════════════════════════════════════════════════════════════════
# ParallelBarItem  — double barre ET (parallèle simultané)
# ════════════════════════════════════════════════════════════════════════════════

class ParallelBarItem(QGraphicsObject):
    """
    Double barre horizontale — divergence/convergence en ET (parallèle simultané).

    Parameters
    ----------
    branches       : nombre de branches parallèles (1 = compat ancien, 2+ = div/conv)
    branch_spacing : espacement centre-à-centre entre branches (px)
    role           : "div"  → stub central en haut + stubs branches en bas  (divergence)
                     "conv" → stubs branches en haut + stub central en bas   (convergence)
                     "both" → tous les stubs
    """
    item_type = ITEM_PARALLEL_BAR

    def __init__(self, branches: int = 2, branch_spacing: int = _BRANCH_SPACING, role: str = "div", out_branch: int = 0):
        super().__init__()
        self.branches       = branches
        self.branch_spacing = branch_spacing
        self.role           = role
        self.out_branch     = out_branch
        self._hover_port    = None
        self.setFlags(
            QGraphicsObject.GraphicsItemFlag.ItemIsMovable    |
            QGraphicsObject.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsObject.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

    # ── Géométrie ─────────────────────────────────────────────────────────────
    @property
    def bar_width(self) -> float:
        if self.branches <= 1:
            return float(_PAR_BAR_W)
        return (self.branches - 1) * self.branch_spacing + _STEP_SZ

    def cx(self)           -> float: return self.bar_width / 2
    def total_height(self) -> float: return _STUB_H * 2 + _TRANS_H * 2 + _PAR_GAP

    def branch_x(self, i: int) -> float:
        if self.branches <= 1:
            return self.cx()
        return _STEP_SZ / 2 + i * self.branch_spacing

    def boundingRect(self) -> QRectF:
        return QRectF(-4, -4, self.bar_width + 8, self.total_height() + 8)

    # ── Ports ─────────────────────────────────────────────────────────────────
    def port_top(self) -> QPointF:
        if self.role == "div":
            return self.mapToScene(QPointF(self.branch_x(0), 0.0))
        return self.mapToScene(QPointF(self.cx(), 0.0))
    def port_bottom(self) -> QPointF:
        if self.role == "conv":
            return self.mapToScene(QPointF(self.branch_x(self.out_branch), self.total_height()))
        return self.mapToScene(QPointF(self.cx(), self.total_height()))

    def nearest_port(self, scene_pos: QPointF):
        candidates = [("top", self.port_top()), ("bottom", self.port_bottom())]
        for i in range(self.branches):
            bx = self.branch_x(i)
            candidates.append((f"branch_top_{i}",    self.mapToScene(QPointF(bx, 0))))
            candidates.append((f"branch_bottom_{i}", self.mapToScene(QPointF(bx, self.total_height()))))
        best_name, best_pt = min(candidates, key=lambda c: (scene_pos - c[1]).manhattanLength())
        return best_name, (scene_pos - best_pt).manhattanLength()

    # ── Dessin ────────────────────────────────────────────────────────────────
    def paint(self, painter: QPainter, option, widget=None):
        is_sel = self.isSelected()
        cx    = self.cx()
        bw    = int(self.bar_width)
        bar1_y = _STUB_H
        bar2_y = bar1_y + _TRANS_H + _PAR_GAP
        th    = int(self.total_height())
        c     = _C_SEL if is_sel else _C_TRANS
        pen   = QPen(c, 2 if is_sel else 1.5)
        painter.setPen(pen)

        # Double barre pleine largeur
        painter.fillRect(QRect(0, bar1_y, bw, _TRANS_H), c)
        painter.fillRect(QRect(0, bar2_y, bw, _TRANS_H), c)

        # Stub entrant (div : aligné sur branch_x(0) ; both : au centre)
        if self.role == "div":
            painter.drawLine(int(self.branch_x(0)), 0, int(self.branch_x(0)), bar1_y)
        elif self.role == "both":
            painter.drawLine(int(cx), 0, int(cx), bar1_y)
        # Stub sortant (conv : aligné sur branch_x(out_branch) ; both : au centre)
        if self.role == "conv":
            painter.drawLine(int(self.branch_x(self.out_branch)), bar2_y + _TRANS_H,
                             int(self.branch_x(self.out_branch)), th)
        elif self.role == "both":
            painter.drawLine(int(cx), bar2_y + _TRANS_H, int(cx), th)

        # Stubs de branches
        for i in range(self.branches):
            bx = int(self.branch_x(i))
            if self.role in ("conv", "both"):
                painter.drawLine(bx, 0, bx, bar1_y)
            if self.role in ("div", "both"):
                painter.drawLine(bx, bar2_y + _TRANS_H, bx, th)

        # Port survolé
        if self._hover_port:
            pt = self._local_port_pos(self._hover_port)
            if pt is not None:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(_C_PORT))
                painter.drawEllipse(pt, _PORT_R, _PORT_R)

    def _local_port_pos(self, port_name: str):
        if port_name == "top":
            return QPointF(self.cx(), 0)
        if port_name == "bottom":
            return QPointF(self.cx(), self.total_height())
        if port_name.startswith("branch_"):
            parts = port_name.split("_")
            if len(parts) == 3:
                try:
                    idx = int(parts[2])
                    by  = 0.0 if parts[1] == "top" else self.total_height()
                    return QPointF(self.branch_x(idx), by)
                except (ValueError, IndexError):
                    pass
        return None

    def hoverMoveEvent(self, event):
        best_name, _ = self.nearest_port(self.mapToScene(event.pos()))
        self._hover_port = best_name
        self.update()

    def hoverLeaveEvent(self, event):
        self._hover_port = None
        self.update()

    def itemChange(self, change, value):
        if change == QGraphicsObject.GraphicsItemChange.ItemPositionChange:
            x = round(value.x() / _GRID) * _GRID
            y = round(value.y() / _GRID) * _GRID
            return QPointF(x, y)
        if change == QGraphicsObject.GraphicsItemChange.ItemPositionHasChanged:
            sc = self.scene()
            if sc and hasattr(sc, "update_liaisons_for"):
                sc.update_liaisons_for(self)
        return super().itemChange(change, value)


# ════════════════════════════════════════════════════════════════════════════════
# ConnectorItem  — renvoi de liaison (▽ sortie / △ entrée)
# ════════════════════════════════════════════════════════════════════════════════

class ConnectorItem(QGraphicsObject):
    """
    Renvoi de liaison — permet de « couper » une liaison et d'indiquer
    l'origine ou la destination via un label symbolique.

      direction="out" : source du renvoi, affiche ▽ suivi du label (ex: « ▽ X3 »)
      direction="in"  : destination du renvoi, affiche △ suivi du label (ex: « △ Y2 »)
    """
    item_type = ITEM_CONNECTOR

    def __init__(self, label: str = "X1", direction: str = "out"):
        super().__init__()
        self.label     = label
        self.direction = direction
        self._hover_port = None
        self.setFlags(
            QGraphicsObject.GraphicsItemFlag.ItemIsMovable    |
            QGraphicsObject.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsObject.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

    def width(self)  -> float: return _CONN_W
    def height(self) -> float: return _CONN_H

    def boundingRect(self) -> QRectF:
        return QRectF(-4, -4, _CONN_W + 8, _CONN_H + 8)

    def port_top(self)    -> QPointF:
        return self.mapToScene(QPointF(_CONN_W / 2, 0))
    def port_bottom(self) -> QPointF:
        return self.mapToScene(QPointF(_CONN_W / 2, _CONN_H))

    def nearest_port(self, scene_pos: QPointF):
        top = self.port_top();  dt = (scene_pos - top).manhattanLength()
        bot = self.port_bottom(); db = (scene_pos - bot).manhattanLength()
        return ("top", dt) if dt < db else ("bottom", db)

    def paint(self, painter: QPainter, option, widget=None):
        w, h = self.width(), self.height()
        is_sel = self.isSelected()
        cx = w / 2
        path = QPainterPath()
        if self.direction == "out":
            rect_h = h - 14
            path.moveTo(0, 0)
            path.lineTo(w, 0)
            path.lineTo(w, rect_h)
            path.lineTo(cx, h)
            path.lineTo(0, rect_h)
            path.closeSubpath()
            bg = QColor("#eaf2ff")
        else:
            rect_y = 14
            path.moveTo(cx, 0)
            path.lineTo(w, rect_y)
            path.lineTo(w, h)
            path.lineTo(0, h)
            path.lineTo(0, rect_y)
            path.closeSubpath()
            bg = QColor("#fff3e0")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg))
        painter.drawPath(path)
        painter.setPen(QPen(_C_SEL if is_sel else _C_LINK, 1.8))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
        sym = "▽" if self.direction == "out" else "△"
        f = QFont("Arial", 9, QFont.Weight.Bold)
        painter.setFont(f)
        painter.setPen(QPen(_C_SEL if is_sel else _C_LINK))
        from PyQt6.QtCore import QRectF as _RF
        painter.drawText(
            _RF(0, 0, w, h),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            f"{sym} {self.label}",
        )
        if self._hover_port:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(_C_PORT))
            py = 0.0 if self._hover_port == "top" else float(h)
            painter.drawEllipse(QPointF(cx, py), _PORT_R, _PORT_R)

    def hoverMoveEvent(self, event):
        pos = event.pos(); w, h = self.width(), self.height()
        if abs(pos.x() - w / 2) < 15 and abs(pos.y()) < 10:
            self._hover_port = "top"
        elif abs(pos.x() - w / 2) < 15 and abs(pos.y() - h) < 10:
            self._hover_port = "bottom"
        else:
            self._hover_port = None
        self.update()

    def hoverLeaveEvent(self, event):
        self._hover_port = None; self.update()

    def itemChange(self, change, value):
        if change == QGraphicsObject.GraphicsItemChange.ItemPositionChange:
            x = round(value.x() / _GRID) * _GRID
            y = round(value.y() / _GRID) * _GRID
            return QPointF(x, y)
        if change == QGraphicsObject.GraphicsItemChange.ItemPositionHasChanged:
            sc = self.scene()
            if sc and hasattr(sc, "update_liaisons_for"):
                sc.update_liaisons_for(self)
        return super().itemChange(change, value)