
from PyQt6.QtWidgets import (
    QGraphicsView,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsRectItem,
    QGraphicsEllipseItem,
    QGraphicsTextItem,
    QGraphicsObject,
    QGraphicsItemGroup,
    QGraphicsItem,
    QFrame,
    QSizePolicy
)
from PyQt6.QtGui import QColor, QPen, QBrush, QPixmap, QFontMetrics, QPainter, QCursor, QPainterPath, QFont
from PyQt6.QtCore import Qt, QEvent, QPropertyAnimation, pyqtProperty, QRectF, QPointF, QEasingCurve, pyqtSignal, QObject

from core.config.app_config import AppConfig

import os 

# ===============================
# Poignée de segment orthogonal (glissement perpendiculaire)
# ===============================

class SegmentHandle(QGraphicsObject):
    """Poignée draggable positionnée au milieu d'un segment.
    Un segment H ne peut bouger qu'en Y ; un segment V ne peut bouger qu'en X."""

    def __init__(self, arrow, seg_index, is_horizontal):
        super().__init__()
        self._arrow = arrow
        self._seg_index = seg_index
        self._is_h = is_horizontal
        self.setFlags(
            QGraphicsObject.GraphicsItemFlag.ItemIsMovable |
            QGraphicsObject.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setZValue(10)
        self.setCursor(
            Qt.CursorShape.SizeVerCursor if is_horizontal else Qt.CursorShape.SizeHorCursor
        )

    @property
    def seg_index(self):
        return self._seg_index

    def boundingRect(self):
        # Segment H → poignée large/plate  ;  segment V → poignée étroite/haute
        if self._is_h:
            return QRectF(-12, -5, 24, 10)
        else:
            return QRectF(-5, -12, 10, 24)

    def paint(self, painter, option, widget=None):
        painter.setBrush(QBrush(QColor("#e67e22")))
        painter.setPen(QPen(QColor("#a04000"), 1))
        painter.drawRect(self.boundingRect())

    def itemChange(self, change, value):
        if getattr(self, '_dead', False):
            return super().itemChange(change, value)
        if change == QGraphicsObject.GraphicsItemChange.ItemPositionChange:
            # Contraindre le déplacement à la direction perpendiculaire
            try:
                if not self._arrow._updating_handles:
                    pts = self._arrow._waypoints
                    i   = self._seg_index
                    if pts and i + 1 < len(pts):
                        p0, p1 = pts[i], pts[i + 1]
                        is_h = abs(p0.y() - p1.y()) < 1.0
                        if is_h:
                            mid_x = (p0.x() + p1.x()) / 2
                            return QPointF(mid_x, value.y())
                        else:
                            mid_y = (p0.y() + p1.y()) / 2
                            return QPointF(value.x(), mid_y)
            except RuntimeError:
                pass
        elif change == QGraphicsObject.GraphicsItemChange.ItemPositionHasChanged:
            try:
                if not self._arrow._updating_handles:
                    self._arrow.move_segment(self._seg_index, self.scenePos())
            except RuntimeError:
                pass
        return super().itemChange(change, value)


def _project_to_border(rect, pos):
    """Projette pos (coords scène) sur le bord le plus proche de rect."""
    x, y = pos.x(), pos.y()
    cx = max(rect.left(), min(rect.right(),  x))
    cy = max(rect.top(),  min(rect.bottom(), y))
    candidates = [
        (abs(x - rect.left()),   QPointF(rect.left(),   cy)),
        (abs(x - rect.right()),  QPointF(rect.right(),  cy)),
        (abs(y - rect.top()),    QPointF(cx, rect.top())),
        (abs(y - rect.bottom()), QPointF(cx, rect.bottom())),
    ]
    return min(candidates, key=lambda d: d[0])[1]


class AttachHandle(QGraphicsObject):
    """Cercle draggable sur le bord d'un état — choisit le côté de raccordement.
    Vert = point de départ (p1) ; Bleu = point d'arrivée (p2)."""

    def __init__(self, arrow, is_start):
        super().__init__()
        self._arrow    = arrow
        self._is_start = is_start
        self.setFlags(
            QGraphicsObject.GraphicsItemFlag.ItemIsMovable |
            QGraphicsObject.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setZValue(12)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def boundingRect(self):
        return QRectF(-8, -8, 16, 16)

    def paint(self, painter, option, widget=None):
        color = QColor("#27ae60") if self._is_start else QColor("#2980b9")
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(QColor("#1a252f"), 1.5))
        painter.drawEllipse(self.boundingRect())

    def itemChange(self, change, value):
        if getattr(self, '_dead', False):
            return super().itemChange(change, value)
        if change == QGraphicsObject.GraphicsItemChange.ItemPositionChange:
            try:
                if not self._arrow._updating_handles:
                    state = self._arrow.start_item if self._is_start else self._arrow.end_item
                    return _project_to_border(state.sceneBoundingRect(), value)
            except RuntimeError:
                pass
        elif change == QGraphicsObject.GraphicsItemChange.ItemPositionHasChanged:
            try:
                if not self._arrow._updating_handles:
                    self._arrow.move_attach(self._is_start, self.scenePos())
            except RuntimeError:
                pass
        return super().itemChange(change, value)


# ────────────────────────────────
# Flèche de transition orthogonale
# ────────────────────────────────

def _remove_handles_from_scene(handles):
    """Fonction HORS CLASSE : supprime les poignées de la scène.
    Ne dépend PAS de l'objet flèche (évite le crash si la flèche est
    déjà supprimée quand le QTimer se déclenche)."""
    for h in handles:
        try:
            if h.scene():
                h.scene().removeItem(h)
        except RuntimeError:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# RenvoiItem — symbole de renvoi (pentagone ▽ départ / △ arrivée)
# ══════════════════════════════════════════════════════════════════════════════

class RenvoiItem(QGraphicsObject):
    """
    Symbole de renvoi attaché à une TransitionArrow.
      direction='out' : ▽ côté départ  (montre la destination)
      direction='in'  : △ côté arrivée (montre l'origine via Y(…))
    Clic droit → reconvertir la flèche associée.
    """
    W, H = 66, 30

    def __init__(self, arrow, direction: str, label: str):
        super().__init__()
        self._arrow    = arrow
        self.direction = direction   # 'out' ou 'in'
        self.label     = label
        self.setFlags(
            QGraphicsObject.GraphicsItemFlag.ItemIsMovable    |
            QGraphicsObject.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsObject.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setZValue(3)

    def boundingRect(self):
        return QRectF(-3, -3, self.W + 6, self.H + 6)

    def paint(self, painter, option, widget=None):
        w, h = self.W, self.H
        cx   = w / 2
        is_sel = self.isSelected()

        path = QPainterPath()
        if self.direction == 'out':
            # ▽ pentagone pointant vers le bas
            path.moveTo(0, 0);      path.lineTo(w, 0)
            path.lineTo(w, h - 11); path.lineTo(cx, h)
            path.lineTo(0, h - 11); path.closeSubpath()
            bg = QColor("#eaf2ff")
        else:
            # △ pentagone pointant vers le haut
            path.moveTo(cx, 0);     path.lineTo(w, 11)
            path.lineTo(w, h);      path.lineTo(0, h)
            path.lineTo(0, 11);     path.closeSubpath()
            bg = QColor("#fff3e0")

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg))
        painter.drawPath(path)

        border = QColor("#f39c12") if is_sel else QColor("#c0392b")
        painter.setPen(QPen(border, 1.8))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

        font = QFont("Arial", 9, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QPen(border))
        painter.drawText(QRectF(0, 0, w, h),
                         Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                         self.label)

    def contextMenuEvent(self, event):
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QCursor
        menu = QMenu()
        act  = menu.addAction("Reconvertir en flèche")
        chosen = menu.exec(QCursor.pos())
        if chosen == act:
            self._arrow.restore_from_renvoi()
        event.accept()


# ────────────────────────────────
# Flèche de transition orthogonale
# ────────────────────────────────

class TransitionArrow(QGraphicsPathItem):
    def _connect_item_movement(self):
        # Connecte la mise à jour de la flèche sur le déplacement des items
        def handler():
            self.update_arrow()
        self.start_item.installSceneEventFilter(self)
        self.end_item.installSceneEventFilter(self)
        self._movement_handler = handler

    def sceneEventFilter(self, watched, event):
        from PyQt6.QtCore import QEvent
        # Met à jour la flèche sur déplacement ou changement de géométrie
        if event.type() in [QEvent.Type.GraphicsSceneMove, QEvent.Type.GraphicsSceneResize, QEvent.Type.GraphicsSceneChange]:
            try:
                # Vérifie que les deux extrémités sont encore valides (objet C++ vivant)
                self.start_item.sceneBoundingRect()
                self.end_item.sceneBoundingRect()
            except RuntimeError:
                return False
            self.update_arrow()
        return False
    def compute_orthogonal_path(self, start_point, end_point, obstacles):
        """
        Algorithme A* sur grille pour chemin orthogonal multi-segments entre start_point et end_point,
        évitant les obstacles. Retourne une liste de QPointF.
        """
        import heapq
        grid_size = 20
        def point_to_grid(p):
            return (int(p.x() // grid_size), int(p.y() // grid_size))
        def grid_to_point(g):
            return QPointF(g[0]*grid_size, g[1]*grid_size)
        def is_blocked(g):
            p = grid_to_point(g)
            for rect in obstacles:
                if rect.contains(p):
                    return True
            return False
        start_g = point_to_grid(start_point)
        end_g = point_to_grid(end_point)
        open_set = []
        heapq.heappush(open_set, (0, start_g, [start_g]))
        visited = set()
        directions = [(1,0),(-1,0),(0,1),(0,-1)]
        while open_set:
            cost, curr, path = heapq.heappop(open_set)
            if curr == end_g:
                return [grid_to_point(g) for g in path]
            if curr in visited:
                continue
            visited.add(curr)
            for d in directions:
                next_g = (curr[0]+d[0], curr[1]+d[1])
                if next_g in visited or is_blocked(next_g):
                    continue
                # Heuristique manhattan
                h = abs(next_g[0]-end_g[0]) + abs(next_g[1]-end_g[1])
                heapq.heappush(open_set, (cost+1+h, next_g, path+[next_g]))
        # Fallback: ligne droite
        return [start_point, end_point]

    def __init__(self, start_item, end_item):
        QGraphicsPathItem.__init__(self)
        self.start_item = start_item
        self.end_item = end_item
        self.setZValue(1)  # Au-dessus des blocs

        # Crayon noir (lisibilité sur fond pastel)
        pen = QPen(QColor(30, 30, 30), 2)
        pen.setStyle(Qt.PenStyle.DashLine)
        self.pen = pen
        self.setPen(self.pen)

        # ── Routage personnalisé ──
        self._waypoints = None        # None = auto ; list[QPointF] = personnalisé
        self._handles = []            # SegmentHandle actifs
        self._locked = False
        self._updating_handles = False
        self._last_auto_pts = []      # Derniers points calculés automatiquement
        self.condition = ""          # Condition de franchissement
        self._show_condition = False   # Affichée uniquement lors du survol dans la liste
        self._is_renvoi   = False    # True = affiché sous forme de deux repères
        self._renvoi_items = []      # [RenvoiItem départ, RenvoiItem arrivée]
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.start_item.add_arrow(self)
        self.end_item.add_arrow(self)

        # ── Route statique GEMMA : chemin fixe depuis le fichier de référence ──
        self._apply_static_route()
        if self._waypoints is None:
            # Fallback : routage automatique si la paire n'est pas référencée
            self.update_arrow()

    def _apply_static_route(self):
        """Applique le chemin prédéfini pour cette transition (src→dst).

        Si la paire (start_item.code, end_item.code) est présente dans
        STATIC_ROUTES, on fixe immédiatement les waypoints et on verrouille
        la flèche (pas de recalcul dynamique, pas de poignées).
        """
        from core.utils.gemma_static_routes import STATIC_ROUTES
        key = (self.start_item.code, self.end_item.code)
        pts = STATIC_ROUTES.get(key)
        if pts is None:
            return
        self._waypoints = [QPointF(x, y) for x, y in pts]
        self._locked = True
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setPath(self._build_path_from_points(self._waypoints))

    def update_arrow(self):
        if self._waypoints is not None:
            self._reattach_endpoints()
            self._redraw_custom()
            self._update_handles()
            return
        try:
            sr = self.start_item.sceneBoundingRect()
            er = self.end_item.sceneBoundingRect()
        except RuntimeError:
            return
        scene = self.start_item.scene()
        if scene is None:
            return

        # ── Calcul de l'offset pour distribuer les flèches sur les bords ──
        # Règle : on ne groupe ensemble que les flèches qui partagent
        # EXACTEMENT le même côté de sortie (ou d'entrée) d'un état.
        # Cela évite de mélanger les flèches qui partent à gauche avec
        # celles qui partent à droite (elles n'occupent pas le même bord).

        def dominant_exit_side(from_rect, to_rect):
            """Côté de from_rect que la flèche quitte (L/R/T/B)."""
            fc, tc = from_rect.center(), to_rect.center()
            dx, dy = tc.x() - fc.x(), tc.y() - fc.y()
            if abs(dx) >= abs(dy):
                return 'R' if dx >= 0 else 'L'
            return 'B' if dy >= 0 else 'T'

        def arrow_is_alive(it):
            """Retourne (sr, er) si les deux extrémités de it sont encore valides,
            None sinon. Protège contre les crashs 'pure virtual method called'."""
            try:
                return it.start_item.sceneBoundingRect(), it.end_item.sceneBoundingRect()
            except RuntimeError:
                return None

        # Côté de sortie de CETTE flèche sur start_item
        my_exit_side  = dominant_exit_side(sr, er)
        # Côté d'entrée de CETTE flèche sur end_item
        my_entry_side = dominant_exit_side(er, sr)

        STEP = 20   # espacement entre deux flèches parallèles (px)

        # Frères sur le même côté de sortie
        siblings_start = []
        for it in self.start_item.arrows:
            if not isinstance(it, TransitionArrow): continue
            if it.start_item is not self.start_item: continue
            if it._waypoints is not None: continue
            rects = arrow_is_alive(it)
            if rects is None: continue
            if dominant_exit_side(rects[0], rects[1]) == my_exit_side:
                siblings_start.append(it)
        siblings_start.sort(key=lambda it: it.end_item.code)

        # Frères sur le même côté d'entrée
        siblings_end = []
        for it in self.end_item.arrows:
            if not isinstance(it, TransitionArrow): continue
            if it.end_item is not self.end_item: continue
            if it._waypoints is not None: continue
            rects = arrow_is_alive(it)
            if rects is None: continue
            if dominant_exit_side(rects[1], rects[0]) == my_entry_side:
                siblings_end.append(it)
        siblings_end.sort(key=lambda it: it.start_item.code)

        def spread_offset(siblings, self_arrow, bias=0):
            n = len(siblings)
            if n <= 1:
                return bias
            idx = next((i for i, it in enumerate(siblings) if it is self_arrow), 0)
            return (idx - (n - 1) / 2) * STEP + bias

        # Décalage léger pour séparer départs et arrivées sur le même bord
        offset_start = spread_offset(siblings_start, self, bias= STEP / 4)
        offset_end   = spread_offset(siblings_end,   self, bias=-STEP / 4)

        pts = self._auto_route(sr, er, scene, offset_start, offset_end)
        self._last_auto_pts = pts
        self.setPath(self._build_path_from_points(pts))
        self._update_handles()

    def _draw_arrow_head(self, path, end, mid_x, mid_y):
        # Dessine une petite tête de flèche à la fin
        import math
        arrow_size = 12
        angle = math.atan2(end.y() - mid_y, end.x() - mid_x)
        p1 = QPointF(
            end.x() - arrow_size * math.cos(angle - math.pi / 6),
            end.y() - arrow_size * math.sin(angle - math.pi / 6)
        )
        p2 = QPointF(
            end.x() - arrow_size * math.cos(angle + math.pi / 6),
            end.y() - arrow_size * math.sin(angle + math.pi / 6)
        )
        path.moveTo(end)
        path.lineTo(p1)
        path.moveTo(end)
        path.lineTo(p2)

    # ─────────────────────────────────────────────────────────────────
    # Routage automatique : L-shape puis U-shape ciblé
    # ─────────────────────────────────────────────────────────────────

    def _auto_route(self, sr, er, scene, offset_start=0, offset_end=0):
        """Routage orthogonal.
        offset_start : décalage perpendiculaire du point d'attache sur sr
        offset_end   : décalage perpendiculaire du point d'attache sur er
        Ces offsets sont calculés dans update_arrow() pour distribuer les
        flèches et éviter les superpositions.
        Phase 1 : L-shape (1 coin) — 5 paires de bords ordonnées.
        Phase 2 : U-shape ciblé sur les lisières d'obstacles.
        """
        sc, ec = sr.center(), er.center()
        dx, dy = ec.x() - sc.x(), ec.y() - sc.y()
        abs_dx, abs_dy = abs(dx), abs(dy)

        def attach(rect, cx_off, cy_off):
            cx = max(rect.left()+4, min(rect.right()-4,  rect.center().x() + cx_off))
            cy = max(rect.top()+4,  min(rect.bottom()-4, rect.center().y() + cy_off))
            return {
                'T': QPointF(cx, rect.top()), 'B': QPointF(cx, rect.bottom()),
                'L': QPointF(rect.left(), cy), 'R': QPointF(rect.right(), cy),
            }

        # L'offset décale perpendiculairement à la direction principale
        if abs_dx >= abs_dy:   # direction H → offset perpendiculaire = vertical
            sp = attach(sr, 0, offset_start)
            ep = attach(er, 0, offset_end)
        else:                   # direction V → offset perpendiculaire = horizontal
            sp = attach(sr, offset_start, 0)
            ep = attach(er, offset_end, 0)

        # Obstacles tiers — bords exacts (pas d'inflation) pour éviter les faux positifs
        obs = [item.sceneBoundingRect()
               for item in scene.items()
               if isinstance(item, EtatGraphicsObject)
               and item is not self.start_item and item is not self.end_item]

        MARGIN = 10   # marge pour rejeter les segments qui longent un bord

        def seg_ok(pa, pb):
            """Vrai si le segment orthogonal pa→pb ne traverse (ni ne longe) aucun état tiers."""
            x1, y1, x2, y2 = pa.x(), pa.y(), pb.x(), pb.y()
            if abs(x1 - x2) < 0.5:   # vertical
                for r in obs:
                    if r.left() - MARGIN < x1 < r.right() + MARGIN:
                        ylo, yhi = min(y1, y2), max(y1, y2)
                        if r.top() - MARGIN < yhi and r.bottom() + MARGIN > ylo:
                            return False
            else:                     # horizontal
                for r in obs:
                    if r.top() - MARGIN < y1 < r.bottom() + MARGIN:
                        xlo, xhi = min(x1, x2), max(x1, x2)
                        if r.left() - MARGIN < xhi and r.right() + MARGIN > xlo:
                            return False
            return True

        def path_ok(pts):
            return all(seg_ok(pts[i], pts[i + 1]) for i in range(len(pts) - 1))

        # ── Phase 0 : segment droit ──────────────────────────────────
        # Si les deux états se chevauchent dans la direction perpendiculaire,
        # un segment orthogonal direct suffit — pas de coin nécessaire.
        if abs_dy >= abs_dx:   # connexion verticale possible ?
            x_lo = max(sr.left() + 4, er.left() + 4)
            x_hi = min(sr.right() - 4, er.right() - 4)
            if x_lo <= x_hi:
                # cx = centre du recouvrement + offset de répartition (clamped)
                cx = max(x_lo, min(x_hi, (x_lo + x_hi) / 2 + offset_start))
                if dy >= 0:
                    p1, p2 = QPointF(cx, sr.bottom()), QPointF(cx, er.top())
                else:
                    p1, p2 = QPointF(cx, sr.top()), QPointF(cx, er.bottom())
                if seg_ok(p1, p2):
                    return [p1, p2]
        else:                   # connexion horizontale possible ?
            y_lo = max(sr.top() + 4, er.top() + 4)
            y_hi = min(sr.bottom() - 4, er.bottom() - 4)
            if y_lo <= y_hi:
                cy = max(y_lo, min(y_hi, (y_lo + y_hi) / 2 + offset_start))
                if dx >= 0:
                    p1, p2 = QPointF(sr.right(), cy), QPointF(er.left(), cy)
                else:
                    p1, p2 = QPointF(sr.left(), cy), QPointF(er.right(), cy)
                if seg_ok(p1, p2):
                    return [p1, p2]

        # ── Paires de bords selon direction principale ─────────────────
        if abs_dx >= abs_dy:
            if dx >= 0:
                order = [('R','L'), ('R','T'), ('R','B'), ('B','L'), ('T','L')]
            else:
                order = [('L','R'), ('L','T'), ('L','B'), ('B','R'), ('T','R')]
        else:
            if dy >= 0:
                order = [('B','T'), ('B','L'), ('B','R'), ('L','T'), ('R','T')]
            else:
                order = [('T','B'), ('T','L'), ('T','R'), ('L','B'), ('R','B')]

        # ── Phase 1 : L-shape ─────────────────────────────────────────
        for s_side, e_side in order:
            p1, p2 = sp[s_side], ep[e_side]
            for corner in (QPointF(p2.x(), p1.y()), QPointF(p1.x(), p2.y())):
                # coin dégénéré (confondu avec p1 ou p2) → ignorer
                if abs(corner.x()-p1.x()) < 0.5 and abs(corner.y()-p1.y()) < 0.5: continue
                if abs(corner.x()-p2.x()) < 0.5 and abs(corner.y()-p2.y()) < 0.5: continue
                if path_ok([p1, corner, p2]):
                    return [p1, corner, p2]

        # ── Phase 2 : U-shape ciblé ──────────────────────────────────
        # Utilise les lisières des obstacles comme candidats de dérivation ;
        # trie par proximité au milieu du trajet pour favoriser les courts détours.
        GAP  = 20
        mid_y = (sc.y() + ec.y()) / 2
        mid_x = (sc.x() + ec.x()) / 2

        if abs_dx >= abs_dy:
            p1 = sp['R'] if dx >= 0 else sp['L']
            p2 = ep['L'] if dx >= 0 else ep['R']
            y_cands = sorted(
                {r.top() - GAP for r in obs} | {r.bottom() + GAP for r in obs} |
                {sc.y(), ec.y()},
                key=lambda y: abs(y - mid_y)
            )
            for by in y_cands:
                pts = [p1, QPointF(p1.x(), by), QPointF(p2.x(), by), p2]
                if path_ok(pts):
                    return pts
        else:
            p1 = sp['B'] if dy >= 0 else sp['T']
            p2 = ep['T'] if dy >= 0 else ep['B']
            x_cands = sorted(
                {r.left() - GAP for r in obs} | {r.right() + GAP for r in obs} |
                {sc.x(), ec.x()},
                key=lambda x: abs(x - mid_x)
            )
            for bx in x_cands:
                pts = [p1, QPointF(bx, p1.y()), QPointF(bx, p2.y()), p2]
                if path_ok(pts):
                    return pts

        # ── Dernier recours : L-shape naturel sans vérification ───────
        if abs_dx >= abs_dy:
            p1 = sp['R'] if dx >= 0 else sp['L']
            p2 = ep['L'] if dx >= 0 else ep['R']
        else:
            p1 = sp['B'] if dy >= 0 else sp['T']
            p2 = ep['T'] if dy >= 0 else ep['B']
        return [p1, QPointF(p2.x(), p1.y()), p2]

    def _build_path_from_points(self, pts):
        """Construit le QPainterPath (polyline + tête de flèche) depuis
        une liste de QPointF. Utilisé par le tracé auto et le tracé custom."""
        import math
        if not pts or len(pts) < 2:
            return QPainterPath()
        # Supprimer les points consécutifs en double (évite direction nulle sur la tête)
        deduped = [pts[0]]
        for pt in pts[1:]:
            if abs(pt.x() - deduped[-1].x()) > 0.5 or abs(pt.y() - deduped[-1].y()) > 0.5:
                deduped.append(pt)
        if len(deduped) < 2:
            return QPainterPath()
        pts = deduped
        path = QPainterPath(pts[0])
        for pt in pts[1:]:
            path.lineTo(pt)
        end, prev = pts[-1], pts[-2]
        sz  = 12
        ang = math.atan2(end.y() - prev.y(), end.x() - prev.x())
        a1  = QPointF(end.x() - sz * math.cos(ang - math.pi / 6),
                      end.y() - sz * math.sin(ang - math.pi / 6))
        a2  = QPointF(end.x() - sz * math.cos(ang + math.pi / 6),
                      end.y() - sz * math.sin(ang + math.pi / 6))
        path.moveTo(end); path.lineTo(a1)
        path.moveTo(end); path.lineTo(a2)
        return path

    # ─────────────────────────────────────────────────────────────────
    # Routage personnalisé (waypoints draggables)
    # ─────────────────────────────────────────────────────────────────

    def _border_attach(self, rect, target):
        """Retourne le point sur le bord de `rect` face à `target`."""
        c = rect.center()
        dx, dy = target.x() - c.x(), target.y() - c.y()
        if abs(dx) < 0.5 and abs(dy) < 0.5:
            return QPointF(c.x(), rect.top())
        hw, hh = rect.width() / 2, rect.height() / 2
        if abs(dx) / hw > abs(dy) / hh:
            return QPointF(rect.right() if dx > 0 else rect.left(), c.y())
        else:
            return QPointF(c.x(), rect.bottom() if dy > 0 else rect.top())

    def _reattach_endpoints(self):
        """Recolle p1/_waypoints[0] sur le bord de start_item et
        p2/_waypoints[-1] sur le bord de end_item en conservant l'orthogonalité.
        IMPORTANT : on garde exactement nxt.y (ou nxt.x) pour que le premier/dernier
        segment reste strictement H ou V — jamais diagonal.
        Si la coordonnée secondaire sort des bornes de l'état, elle est recadrée
        et le coin adjacent (waypoints[1] ou waypoints[-2]) est aussi ajusté pour
        maintenir l'orthogonalité de l'ensemble du tracé."""
        if not self._waypoints or len(self._waypoints) < 2:
            return
        try:
            sr = self.start_item.sceneBoundingRect()
            er = self.end_item.sceneBoundingRect()
        except RuntimeError:
            return

        # --- p1 : _waypoints[0] sur start_item ---
        nxt = self._waypoints[1]
        p0  = self._waypoints[0]
        if abs(p0.y() - nxt.y()) < 1.0:           # segment H sortant
            # Garder y = nxt.y() → segment reste horizontal
            x = sr.right() if nxt.x() >= sr.center().x() else sr.left()
            y_new = max(sr.top(), min(sr.bottom(), nxt.y()))
            self._waypoints[0] = QPointF(x, y_new)
            # Si y a été recadré, ajuster le coin adjacent pour maintenir l'orthogonalité
            if len(self._waypoints) >= 3 and abs(y_new - nxt.y()) > 0.5:
                self._waypoints[1] = QPointF(self._waypoints[1].x(), y_new)
        else:                                       # segment V sortant
            # Garder x = nxt.x() → segment reste vertical
            y = sr.bottom() if nxt.y() >= sr.center().y() else sr.top()
            x_new = max(sr.left(), min(sr.right(), nxt.x()))
            self._waypoints[0] = QPointF(x_new, y)
            # Si x a été recadré, ajuster le coin adjacent pour maintenir l'orthogonalité
            if len(self._waypoints) >= 3 and abs(x_new - nxt.x()) > 0.5:
                self._waypoints[1] = QPointF(x_new, self._waypoints[1].y())

        # --- p2 : _waypoints[-1] sur end_item ---
        prv = self._waypoints[-2]
        pN  = self._waypoints[-1]
        if abs(pN.y() - prv.y()) < 1.0:           # segment H entrant
            # Garder y = prv.y() → segment reste horizontal
            x = er.left() if prv.x() <= er.center().x() else er.right()
            y_new = max(er.top(), min(er.bottom(), prv.y()))
            self._waypoints[-1] = QPointF(x, y_new)
            # Si y a été recadré, ajuster le coin adjacent pour maintenir l'orthogonalité
            if len(self._waypoints) >= 3 and abs(y_new - prv.y()) > 0.5:
                self._waypoints[-2] = QPointF(self._waypoints[-2].x(), y_new)
        else:                                       # segment V entrant
            # Garder x = prv.x() → segment reste vertical
            y = er.top() if prv.y() <= er.center().y() else er.bottom()
            x_new = max(er.left(), min(er.right(), prv.x()))
            self._waypoints[-1] = QPointF(x_new, y)
            # Si x a été recadré, ajuster le coin adjacent pour maintenir l'orthogonalité
            if len(self._waypoints) >= 3 and abs(x_new - prv.x()) > 0.5:
                self._waypoints[-2] = QPointF(x_new, self._waypoints[-2].y())

    def _redraw_custom(self):
        """Retrace le chemin depuis _waypoints (liste complète incluant p1 et p2)."""
        pts = self._waypoints
        if not pts or len(pts) < 2:
            return
        self.setPath(self._build_path_from_points(pts))

    def move_segment(self, seg_index, scene_pos):
        """Appelé par SegmentHandle : déplace un segment parallèlement à lui-même.
        N'appelle PAS _reattach_endpoints : les points d'attache restent sur leur
        bord courant, seul ce segment bouge."""
        if not self._waypoints or seg_index + 1 >= len(self._waypoints):
            return
        pts  = self._waypoints
        is_h = abs(pts[seg_index].y() - pts[seg_index + 1].y()) < 1.0
        if is_h:
            ny = scene_pos.y()
            pts[seg_index]     = QPointF(pts[seg_index].x(),     ny)
            pts[seg_index + 1] = QPointF(pts[seg_index + 1].x(), ny)
        else:
            nx = scene_pos.x()
            pts[seg_index]     = QPointF(nx, pts[seg_index].y())
            pts[seg_index + 1] = QPointF(nx, pts[seg_index + 1].y())
        self._redraw_custom()

    def move_attach(self, is_start, scene_pos):
        """Appelé par AttachHandle : déplace p1 ou p2 sur le bord de l'état.
        Recalcule le coin ADJACENT en utilisant le point fixe suivant/précédent
        (pts[2] ou pts[-3]) pour garantir que les deux segments adjacents restent
        strictement orthogonaux — jamais diagonaux."""
        pts = self._waypoints
        if not pts or len(pts) < 2:
            return
        tol = 4
        try:
            _sr = self.start_item.sceneBoundingRect()
            _er = self.end_item.sceneBoundingRect()
        except RuntimeError:
            return
        if is_start:
            pts[0] = scene_pos
            sr = _sr
            on_h_border = (abs(scene_pos.y() - sr.top())    < tol or
                           abs(scene_pos.y() - sr.bottom()) < tol)
            if len(pts) >= 3:
                # Le coin pts[1] est recalculé pour relier pts[0] à pts[2]
                # orthogonalement, sans toucher à pts[2] ni au reste du chemin.
                if on_h_border:
                    # Sortie V : pts[1].x = pts[0].x, pts[1].y = pts[2].y
                    pts[1] = QPointF(scene_pos.x(), pts[2].y())
                else:
                    # Sortie H : pts[1].y = pts[0].y, pts[1].x = pts[2].x
                    pts[1] = QPointF(pts[2].x(), scene_pos.y())
            else:
                # Chemin à 2 points : ajustement minimal
                if on_h_border:
                    pts[1] = QPointF(scene_pos.x(), pts[1].y())
                else:
                    pts[1] = QPointF(pts[1].x(), scene_pos.y())
        else:
            pts[-1] = scene_pos
            er = _er
            on_h_border = (abs(scene_pos.y() - er.top())    < tol or
                           abs(scene_pos.y() - er.bottom()) < tol)
            if len(pts) >= 3:
                # Le coin pts[-2] est recalculé pour relier pts[-3] à pts[-1]
                # orthogonalement, sans toucher à pts[-3] ni au reste du chemin.
                if on_h_border:
                    # Arrivée V : pts[-2].x = pts[-1].x, pts[-2].y = pts[-3].y
                    pts[-2] = QPointF(scene_pos.x(), pts[-3].y())
                else:
                    # Arrivée H : pts[-2].y = pts[-1].y, pts[-2].x = pts[-3].x
                    pts[-2] = QPointF(pts[-3].x(), scene_pos.y())
            else:
                if on_h_border:
                    pts[-2] = QPointF(scene_pos.x(), pts[-2].y())
                else:
                    pts[-2] = QPointF(pts[-2].x(), scene_pos.y())
        self._redraw_custom()
        self._update_handles()

    def _show_handles(self):
        """Crée les poignées : AttachHandle sur p1/p2 + SegmentHandle sur chaque segment."""
        if self._locked:
            return
        if self._waypoints is None:
            pts = self._last_auto_pts
            if len(pts) < 2:
                return
            self._waypoints = [QPointF(p) for p in pts]
        self._clear_handles()
        if not self.scene() or len(self._waypoints) < 2:
            return
        # Cercle vert sur p1 (départ)
        h_start = AttachHandle(self, True)
        h_start.setPos(self._waypoints[0])
        self.scene().addItem(h_start)
        self._handles.append(h_start)
        # Poignées rectangulaires sur chaque segment
        for i in range(len(self._waypoints) - 1):
            p0, p1 = self._waypoints[i], self._waypoints[i + 1]
            is_h = abs(p0.y() - p1.y()) < 1.0
            mid  = QPointF((p0.x() + p1.x()) / 2, (p0.y() + p1.y()) / 2)
            h = SegmentHandle(self, i, is_h)
            h.setPos(mid)
            self.scene().addItem(h)
            self._handles.append(h)
        # Cercle bleu sur p2 (arrivée)
        h_end = AttachHandle(self, False)
        h_end.setPos(self._waypoints[-1])
        self.scene().addItem(h_end)
        self._handles.append(h_end)

    def _hide_handles(self):
        """Cache les poignées : marque _dead immédiatement, diffère la suppression.
        Utilise une fonction module-level (sans référence à self) pour le timer
        — évite le crash si la flèche est supprimée avant que le timer ne tire."""
        to_remove = list(self._handles)
        self._handles = []
        for h in to_remove:
            h._dead = True
        if to_remove:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: _remove_handles_from_scene(to_remove))

    def _clear_handles(self):
        """Vide la liste des poignées et diffère leur suppression physique."""
        to_remove = list(self._handles)
        self._handles = []
        for h in to_remove:
            h._dead = True
        if to_remove:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: _remove_handles_from_scene(to_remove))

    def _update_handles(self):
        """Repositionne chaque poignée (AttachHandle et SegmentHandle) — flag guard."""
        if not self._handles or not self._waypoints:
            return
        self._updating_handles = True
        for h in self._handles:
            if isinstance(h, AttachHandle):
                h.setPos(self._waypoints[0] if h._is_start else self._waypoints[-1])
            elif isinstance(h, SegmentHandle):
                i = h.seg_index
                if i + 1 < len(self._waypoints):
                    p0, p1 = self._waypoints[i], self._waypoints[i + 1]
                    h._is_h = abs(p0.y() - p1.y()) < 1.0
                    h.setPos(QPointF((p0.x() + p1.x()) / 2, (p0.y() + p1.y()) / 2))
        self._updating_handles = False

    def reset_routing(self):
        """Revenir au tracé automatique (supprime les waypoints personnalisés)."""
        self._clear_handles()
        self._waypoints = None
        self.update_arrow()

    def set_locked(self, locked: bool):
        self._locked = locked
        if locked:
            self._clear_handles()
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        else:
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)

    def shape(self):
        """Zone cliquable élargie (±8 px autour du chemin) pour faciliter le clic
        sur la flèche fine."""
        from PyQt6.QtGui import QPainterPathStroker
        stroker = QPainterPathStroker()
        stroker.setWidth(16)
        return stroker.createStroke(self.path())

    def paint(self, painter, option, widget=None):
        """Dessine le chemin puis la condition de franchissement si elle est définie."""
        QGraphicsPathItem.paint(self, painter, option, widget)
        if self.condition and self._show_condition:
            mid = self.path().pointAtPercent(0.5)
            font = QFont()
            font.setPointSize(8)
            font.setBold(True)
            painter.setFont(font)
            # QFontMetrics(font) évite les valeurs stale du painter au premier rendu
            fm = QFontMetrics(font)
            text_w = fm.horizontalAdvance(self.condition)
            text_h = fm.height()
            pad_x, pad_y = 5, 3
            bg = QRectF(mid.x() - text_w / 2 - pad_x,
                        mid.y() - text_h / 2 - pad_y,
                        text_w + pad_x * 2,
                        text_h + pad_y * 2)
            # Fond jaune
            painter.fillRect(bg, QColor("#fffb6e"))
            # Bordure noire fine
            painter.setPen(QPen(QColor("#000000"), 1))
            painter.drawRect(bg)
            # Texte noir
            painter.drawText(bg, Qt.AlignmentFlag.AlignCenter, self.condition)

    def set_condition(self, condition: str):
        self.condition = condition
        self.update()

    def set_highlighted(self, highlighted: bool):
        """Met en surbrillance la flèche (jaune/épais) ou revient à la normale."""
        if highlighted:
            self.setPen(QPen(QColor("#f39c12"), 4))
        else:
            self.setPen(self.pen)   # restaure le QPen d'origine (rouge, épaisseur 2)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            if value:
                self._show_handles()
            else:
                self._hide_handles()
        return QGraphicsPathItem.itemChange(self, change, value)

    # ─────────────────────────────────────────────────────────────────
    # Renvoi (transformation flèche ↔ deux repères pentagones)
    # ─────────────────────────────────────────────────────────────────

    def _renvoi_positions(self):
        """Calcule les positions scène (x, y) des deux repères en fonction
        de la direction de la flèche par rapport aux deux états."""
        W, H = RenvoiItem.W, RenvoiItem.H
        try:
            sr = self.start_item.sceneBoundingRect()
            er = self.end_item.sceneBoundingRect()
        except RuntimeError:
            return (0, 0), (0, 0)
        sc = sr.center()
        ec = er.center()
        dx = ec.x() - sc.x()
        dy = ec.y() - sc.y()
        off = 10
        if abs(dx) >= abs(dy):          # direction principale = horizontale
            if dx >= 0:                 # end est à droite
                x_out = sr.right() + off;         y_out = sc.y() - H / 2
                x_in  = er.left()  - W - off;     y_in  = ec.y() - H / 2
            else:                       # end est à gauche
                x_out = sr.left()  - W - off;     y_out = sc.y() - H / 2
                x_in  = er.right() + off;         y_in  = ec.y() - H / 2
        else:                           # direction principale = verticale
            if dy >= 0:                 # end est en bas
                x_out = sc.x() - W / 2;           y_out = sr.bottom() + off
                x_in  = ec.x() - W / 2;           y_in  = er.top() - H - off
            else:                       # end est en haut
                x_out = sc.x() - W / 2;           y_out = sr.top() - H - off
                x_in  = ec.x() - W / 2;           y_in  = er.bottom() + off
        return (x_out, y_out), (x_in, y_in)

    def convert_to_renvoi(self):
        """Masque la flèche et place deux symboles pentagones (▽ et △) sur la scène."""
        if self._is_renvoi:
            return
        self._is_renvoi = True
        self._clear_handles()
        # Labels :
        #   côté départ  (▽) : indique la destination  → code de end_item
        #   côté arrivée (△) : indique l'origine        → Y(code de start_item)
        label_out = self.end_item.code
        label_in  = f"Y({self.start_item.code})"
        (x_out, y_out), (x_in, y_in) = self._renvoi_positions()
        r_out = RenvoiItem(self, 'out', label_out)
        r_in  = RenvoiItem(self, 'in',  label_in)
        r_out.setPos(x_out, y_out)
        r_in.setPos(x_in,  y_in)
        sc = self.scene()
        sc.addItem(r_out)
        sc.addItem(r_in)
        self._renvoi_items = [r_out, r_in]
        self.setVisible(False)

    def restore_from_renvoi(self):
        """Supprime les symboles de renvoi et réaffiche la flèche."""
        if not self._is_renvoi:
            return
        scene = (self._renvoi_items[0].scene()
                 if self._renvoi_items else self.scene())
        for item in self._renvoi_items:
            try:
                if scene:
                    scene.removeItem(item)
            except RuntimeError:
                pass
        self._renvoi_items = []
        self._is_renvoi = False
        self.setVisible(True)
        self.update_arrow()

    def contextMenuEvent(self, event):
        event.accept()   # inhibé — pas de menu contextuel sur les flèches

    def mouseDoubleClickEvent(self, event):
        event.accept()   # inhibé — plus de réinitialisation du tracé par double-clic
        

# ===============================
# Bloc état redimensionnable sans cadre blanc
# ===============================
class EtatGraphicsObject(QGraphicsObject):
            
        
    # Signal pour demander la suppression du bloc
    deleteRequested = pyqtSignal(str)

    
    def __init__(self, code, label, width=250, height=150):
        super().__init__()
        self.arrows = []
        self.code = code
        self.label = label
        self.width_ref = width
        self.height_ref = height
        self.width = width
        self.height = height
        self.handle_size = AppConfig.HANDLE_SIZE
        self.setFlags(
            QGraphicsObject.GraphicsItemFlag.ItemIsMovable |
            QGraphicsObject.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsObject.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.handle_pos = QPointF(width - self.handle_size, height - self.handle_size)
        self._dragging_handle = False
        self._handle_pressed = False  # Pour la couleur du handle
        self.handle_visible = True  # Par défaut, visible
        self._border_color = Qt.GlobalColor.black  # Bordure noire par défaut
        self._states_interactive = True  # Par défaut, le clic droit est actif
        self._sim_active = False  # Simulation : état actif (fond rouge)
        self.update_handle_position()
        
    def setPos(self, *args, **kwargs):
        super().setPos(*args, **kwargs)
        self.update_handle_position()

    def boundingRect(self):
        return QRectF(0, 0, self.width, self.height)

    def update_handle_position(self):
            self.handle_pos = QPointF(self.width - self.handle_size, self.height - self.handle_size)
            self.update()
            
    def set_sim_active(self, active: bool):
        """Simulation : état actif = fond rouge vif, inactif = fond bleu normal."""
        self._sim_active = active
        self.update()

    def paint(self, painter, option, widget=None):
        # Couleurs par famille (premier caractère du code)
        _FAMILY_COLORS = {
            "A": ("#d6f5d6", "#2e7d32"),   # fond vert très pastel, bord vert foncé
            "F": ("#dce9fb", "#1565c0"),   # fond bleu pastel, bord bleu
            "D": ("#fde0e0", "#c62828"),   # fond rouge pastel, bord rouge
        }
        family = self.code[0] if self.code else ""
        bg_default, border_default = _FAMILY_COLORS.get(family, ("#ffffff", "#000000"))

        # Rectangle principal
        border_color = self._border_color if self._border_color != Qt.GlobalColor.black \
                       else QColor(border_default)
        painter.setPen(QPen(border_color, 2))
        bg_color = QColor("#e74c3c") if self._sim_active else QColor(bg_default)
        painter.setBrush(QBrush(bg_color))
        painter.drawRect(0, 0, int(self.width), int(self.height))

        # En simulation active : texte/cercle en jaune vif ; sinon couleur famille
        text_color = QColor("#ffe600") if self._sim_active else border_color

        # Double bord pour l'étape initiale (A1)
        if self.code == "A1":
            inset = 4
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(text_color, 2))
            painter.drawRect(inset, inset, int(self.width) - 2 * inset, int(self.height) - 2 * inset)

        # Cercle
        circle_diameter = 24
        painter.setBrush(QBrush(Qt.GlobalColor.transparent))
        painter.setPen(QPen(text_color, 1))
        painter.drawEllipse(4, 5, circle_diameter, circle_diameter)

        # Texte code (dans le cercle)
        painter.setPen(QPen(text_color))
        painter.drawText(8, 22, self.code)

        # -------- LABEL AVEC WORD WRAP --------
        text_x = circle_diameter + 12
        text_y = 6
        text_width = self.width - text_x - 6
        text_height = self.height - text_y - 6

        text_rect = QRectF(text_x, text_y, text_width, text_height)

        painter.setPen(QPen(text_color))
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
            self.label
        )

        # Handle (affiché seulement si handle_visible)
        if self.handle_visible:
            if self._handle_pressed:
                painter.setBrush(QBrush(Qt.GlobalColor.red))
            else:
                painter.setBrush(QBrush(Qt.GlobalColor.darkGray))
            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            painter.drawRect(
                int(self.handle_pos.x()),
                int(self.handle_pos.y()),
                self.handle_size,
                self.handle_size
            )
            

    def add_arrow(self, arrow):
        self.arrows.append(arrow)

    def itemChange(self, change, value):
        # ItemPositionHasChanged : position déjà mise à jour → sceneBoundingRect() correct
        if change == QGraphicsObject.GraphicsItemChange.ItemPositionHasChanged:
            for arrow in list(self.arrows):
                try:
                    arrow.update_arrow()
                except RuntimeError:
                    pass
        return super().itemChange(change, value)

    def set_handle_visible(self, visible: bool):
        self.handle_visible = visible
        self.update()
            
    def mousePressEvent(self, event):
        # Accès à la vue principale (CanvasView) via la scène
        canvas_view = None
        if self.scene() and self.scene().views():
            canvas_view = self.scene().views()[0]
        if canvas_view:
            print(f"Mouse press on state : {canvas_view.action_for_states}")
            action_for_states = canvas_view.action_for_states

        else:
            print("Mouse press on state : (vue non trouvée)")
            action_for_states = None
        self.animate_state_block_highlight()
        if event.button() == Qt.MouseButton.RightButton:
            if not action_for_states:
                print("Clic droit désactivé sur les blocs état")
                # Si le clic droit est désactivé, on laisse le comportement par défaut
                super().mousePressEvent(event)
                return
            # Mettre en évidence la bordure spécifique état
            self.animate_state_block_highlight()
            # Menu contextuel
            from PyQt6.QtWidgets import QMenu
            menu = QMenu()
            action_delete = menu.addAction('Supprimer')
            action = menu.exec(event.screenPos())
            if action == action_delete:
                # Émettre le signal pour suppression
                self.deleteRequested.emit(self.code)
            # Désélectionner la bordure après
            self.animate_state_block_unhighlight()
            
        else:
            if self._on_handle(event.pos()):
                self._dragging_handle = True
                self._handle_pressed = True
                self.update()
            else:
                super().mousePressEvent(event)
        
    def animate_state_block_highlight(self):
        self._border_color = Qt.GlobalColor.red
        self.update()

    def animate_state_block_unhighlight(self):
        self._border_color = Qt.GlobalColor.black
        self.update()

    def mouseMoveEvent(self, event):
        if self._dragging_handle:
            new_width = max(event.pos().x(), 50)
            new_height = max(event.pos().y(), 30)
            self.prepareGeometryChange()
            self.width = new_width
            self.height = new_height
            self.update_handle_position()
            for arrow in list(self.arrows):
                try:
                    arrow.update_arrow()
                except RuntimeError:
                    pass
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        print(f"Mouse release on state : dragging_handle={self._dragging_handle}")
        self._dragging_handle = False
        self._handle_pressed = False
        self.update()
        super().mouseReleaseEvent(event)
        # Si l'état n'est plus sélectionné, remettre la bordure à la couleur normale
        print(f"State selected: {self.isSelected()}")
        if not self.isSelected():
            print("State released, unhighlighting")
            self.animate_state_block_unhighlight()

    def _on_handle(self, pos):
        return QRectF(self.handle_pos.x(), self.handle_pos.y(), self.handle_size, self.handle_size).contains(pos)

class EtatGroupWithResize(QGraphicsItemGroup):

    def __init__(self, code, label, scene, width=250, height=150):
        super().__init__()
        class CustomRect(QGraphicsRectItem):
            def paint(self, painter, option, widget=None):
                painter.setBrush(QBrush(QColor(100, 200, 255)))
                painter.setPen(QPen(Qt.GlobalColor.black, 1))
                painter.drawRect(self.rect())
                # Ne jamais dessiner le cadre de sélection
                # if option.state & QStyle.State_Selected:
                #     pass
        self.rect = CustomRect(0, 0, width, height)
        self.addToGroup(self.rect)
        circle_diameter = 24
        self.circle = QGraphicsEllipseItem(4, 5, circle_diameter, circle_diameter)
        self.circle.setPen(QPen(Qt.GlobalColor.black, 1))
        self.addToGroup(self.circle)
        self.text_item = QGraphicsTextItem(code)
        self.text_item.setPos(3, 3)
        self.text_item.setDefaultTextColor(Qt.GlobalColor.black)
        self.addToGroup(self.text_item)
        self.text_definition = QGraphicsTextItem(label)
        self.text_definition.setPos(circle_diameter + 8, 3)
        self.text_definition.setDefaultTextColor(Qt.GlobalColor.black)
        self.addToGroup(self.text_definition)
        # Handle de resize (ajouté au groupe)
        self.handle = QGraphicsRectItem(width - self.handle_size, height - self.handle_size, self.handle_size, self.handle_size)
        self.handle.setBrush(QBrush(Qt.GlobalColor.darkGray))
        self.handle.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.handle.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.addToGroup(self.handle)
        self.setFlags(
            QGraphicsItemGroup.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItemGroup.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItemGroup.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        # L'event filter sera installé après ajout à la scène


    def sceneEventFilter(self, watched, event):
    
        if watched == self.handle and event.type() == QEvent.Type.GraphicsSceneMouseMove:
            new_width = max(event.scenePos().x() - self.scenePos().x(), 50)
            new_height = max(event.scenePos().y() - self.scenePos().y(), 30)
            # Mise à jour du rectangle unique
            self.rect.prepareGeometryChange()
            self.rect.setRect(0, 0, new_width, new_height)
            self.handle.setRect(new_width - self.handle_size, new_height - self.handle_size, self.handle_size, self.handle_size)
            return True
        return False

    def setPos(self, *args, **kwargs):
        super().setPos(*args, **kwargs)
        # Toujours repositionner le handle dans le coin du rectangle
        rect = self.rect.rect()
        self.handle.setRect(rect.width() - self.handle_size, rect.height() - self.handle_size, self.handle_size, self.handle_size)

class AnimatedRectItem(QGraphicsObject):
    def __init__(self, x, y, w, h):
        super().__init__()

        self.rect = QRectF(x, y, w, h)
        self.setPos(x, y)

        self._border_color = QColor(0, 0, 0)
        self._base_border_color = QColor(0, 0, 0)   # couleur au repos (restaurée après unhighlight)
        self._background = QColor(240, 240, 240)

        self.animation = QPropertyAnimation(self, b"borderColor")
        self.animation.setDuration(250)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

    # =========================
    # Obligatoire avec QGraphicsObject
    # =========================
    def boundingRect(self):
        return self.rect
    # =========================
    # Ajout de setRect pour mise à jour
    # =========================
    def setRect(self, x, y, w, h):
        # ⚠️ Prévenir Qt que la géométrie change
        self.prepareGeometryChange()
        self.rect = QRectF(x, y, w, h)
        self.update()

    def paint(self, painter, option, widget):
        painter.setRenderHint(painter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(self._background))
        painter.setPen(QPen(self._border_color, 2))
        painter.drawRoundedRect(self.rect, 14, 14)

    # =========================
    # Propriété animable
    # =========================
    def getBorderColor(self):
        return self._border_color

    def setBorderColor(self, color):
        self._border_color = color
        self.update()

    borderColor = pyqtProperty(QColor, getBorderColor, setBorderColor)

    # =========================
    # Animations
    # =========================
    def animate_highlight(self):
        self.animation.stop()
        self.animation.setStartValue(self._border_color)
        self.animation.setEndValue(QColor(255, 0, 0))
        self.animation.start()

    def animate_unhighlight(self):
        self.animation.stop()
        self._border_color = QColor(self._base_border_color)
        self.update()


class LayoutBlockGraphicsObject(QGraphicsObject):

    def __init__(self, key, block):
        super().__init__()

        self.key = key
        self.block = block
        self.circle_diameter = 20

        # IMPORTANT : définir width/height AVANT toute chose
        self.width = block.w
        self.height = block.h

        self.setPos(block.x, block.y)

        self.rect_item = AnimatedRectItem(0, 0, block.w, block.h)
        self.rect_item.setParentItem(self)

        # Couleurs modernes par famille
        _FAMILY_LAYOUT = {
            "A": ("#e8f8e8", "#2e7d32"),
            "F": ("#e3eeff", "#1565c0"),
            "D": ("#fce8e8", "#c62828"),
        }
        bg, border = _FAMILY_LAYOUT.get(key, ("#f0f0f0", "#555555"))
        self.rect_item._background = QColor(bg)
        self.rect_item._border_color = QColor(border)
        self.rect_item._base_border_color = QColor(border)

        self.content_items = []
        self._create_content()
        self._update_geometry()
    # -------------------------
    # Obligatoire
    # -------------------------
    def boundingRect(self):
        return QRectF(0, 0, self.block.w, self.block.h)

    def paint(self, painter, option, widget=None):
        pass  # tout est géré par les sous-items

    # -------------------------
    # Création contenu
    # -------------------------
    def _create_content(self):
        self.content_items = []
        # Couleurs de la famille
        _FAMILY_LAYOUT = {
            "A": ("#2e7d32", "#e8f8e8"),
            "F": ("#1565c0", "#e3eeff"),
            "D": ("#c62828", "#fce8e8"),
        }
        border_color, _ = _FAMILY_LAYOUT.get(self.key, ("#555555", "#f0f0f0"))

        # Pour chaque zone, on place le contenu en haut ou en bas
        if self.key == "A":
            positions = ["top"]
        elif self.key == "D":
            positions = ["bottom"]
        elif self.key == "F":
            positions = ["top", "bottom"]
        else:
            positions = ["top"]

        for pos in positions:
            circle = QGraphicsEllipseItem(self)
            circle.setPen(QPen(QColor(border_color), 2))
            circle.setBrush(QColor("white"))

            letter_item = QGraphicsTextItem(self.key, self)
            font = letter_item.font()
            font.setPointSize(10)
            font.setBold(True)
            letter_item.setFont(font)
            letter_item.setDefaultTextColor(QColor(border_color))

            text_item = QGraphicsTextItem(self.block.text, self)
            font2 = text_item.font()
            font2.setPointSize(9)
            font2.setBold(True)
            font2.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
            text_item.setFont(font2)
            text_item.setDefaultTextColor(QColor(border_color))

            self.content_items.append((circle, letter_item, text_item, pos))

    # -------------------------
    # Mise à jour géométrie
    # -------------------------
    def _update_geometry(self):
        # ⚠️ prévenir Qt AVANT tout changement de taille
        self.prepareGeometryChange()

        # Mettre à jour les dimensions utilisées par boundingRect
        self.width = self.block.w
        self.height = self.block.h

        # Position globale
        self.setPos(self.block.x, self.block.y)

        # Rectangle visuel (⚠️ voir remarque plus bas)
        self.rect_item.setRect(0, 0, self.block.w, self.block.h)

        padding = 8

        for circle, letter_item, text_item, pos in self.content_items:
            circle_x = 10

            if pos == "top":
                circle_y = padding
            else:
                circle_y = self.block.h - self.circle_diameter - padding

            circle.setRect(
                circle_x,
                circle_y,
                self.circle_diameter,
                self.circle_diameter
            )

            letter_rect = letter_item.boundingRect()
            letter_item.setPos(
                circle_x + (self.circle_diameter - letter_rect.width()) / 2,
                circle_y + (self.circle_diameter - letter_rect.height()) / 2
            )

            text_rect = text_item.boundingRect()
            text_item.setPos(
                circle_x + self.circle_diameter + 8,
                circle_y + (self.circle_diameter - text_rect.height()) / 2
            )
    # -------------------------
    # Resize public
    # -------------------------
    def resize_block(self, block):
        self.prepareGeometryChange()
        self.block = block
        self._update_geometry()

    # -------------------------
    # Expose animation
    # -------------------------
    def animate_highlight(self):
        self.rect_item.animate_highlight()

    def animate_unhighlight(self):
        self.rect_item.animate_unhighlight()



class CanvasView(QGraphicsView):

    # Signal unique pour resize centralisé
    resizeSceneRequested = pyqtSignal(int, int)
    
    def __init__(self):
        super().__init__()
        self.setContentsMargins(0, 0, 0, 0)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setViewportMargins(0, 0, 0, 0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Initialisation de la scene
        self.scene = QGraphicsScene(0, 0, AppConfig.REFERENCE_CANVAS_WIDTH, AppConfig.REFERENCE_CANVAS_HEIGHT)
        self.setScene(self.scene)
        # Fond gris 128 (identique au GIF de référence le_gemma_plus_fleches.gif)
        self.setBackgroundBrush(QBrush(QColor(128, 128, 128)))

        # Désactiver les scrollbars
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Activer l'antialiasing (plus pro visuellement)
        self.setRenderHints(self.renderHints() | 
                            QPainter.RenderHint.Antialiasing)

        # Items du layout
        self._layout_items = {}
        self.zones = {}
        self.controller = None
        self.current_highlight = None

        # Debug : ajouter un cadre orange pour visualiser les dimensions de la scène
        cadre = QGraphicsRectItem(0, 0, AppConfig.REFERENCE_CANVAS_WIDTH, AppConfig.REFERENCE_CANVAS_HEIGHT)
        cadre.setPen(QPen(QColor("orange")))
        self.scene.addItem(cadre)

        # Initialiser la scene avec la taille actuelle
        self.resize(AppConfig.REFERENCE_CANVAS_WIDTH, AppConfig.REFERENCE_CANVAS_HEIGHT)
        


    # =========================
    # 1️⃣ SIGNAUX PUBLICS
    # =========================

    stateDropped = pyqtSignal(str, str, QPointF)
    canvasClicked = pyqtSignal(QPointF)
    itemClicked = pyqtSignal(object)
    mouseMoved = pyqtSignal(QPointF)


    def accept_drop_from_palette(self):
        return True
    # =========================
    # 2️⃣ INITIALISATION
    # =========================


    def set_states_interactive(self, enabled: bool):
        """Active ou désactive le déplacement/redimensionnement des Etats et l'affichage du handle."""
        self._states_interactive = enabled
        for item in self.scene.items():
            if isinstance(item, EtatGraphicsObject):
                item.setFlag(QGraphicsObject.GraphicsItemFlag.ItemIsMovable, enabled)
                item.setFlag(QGraphicsObject.GraphicsItemFlag.ItemIsSelectable, enabled)
                item.set_handle_visible(enabled)

    def set_canvas_locked(self, locked: bool):
        """Verrouille ou déverrouille tous les états ET les flèches du canvas."""
        self.set_states_interactive(not locked)
        for item in self.scene.items():
            if isinstance(item, TransitionArrow):
                item.set_locked(locked)
        


    def apply_states_interactive(self):
        """Réapplique l'état interactif courant à tous les Etats (utile après un redraw)."""
        enabled = getattr(self, '_states_interactive', False)
        for item in self.scene.items():
            if isinstance(item, EtatGraphicsObject):
                item.setFlag(QGraphicsObject.GraphicsItemFlag.ItemIsMovable, enabled)
                item.setFlag(QGraphicsObject.GraphicsItemFlag.ItemIsSelectable, enabled)
                item.set_handle_visible(enabled)

    def _init_scene(self):
        
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        # Fixer la taille initiale de la scène à celle du viewport
        self._sync_scene_size()

    def _sync_scene_size(self):
        w = self.viewport().width()
        h = self.viewport().height()
        self.scene.setSceneRect(0, 0, w, h)

    def _init_view_config(self):
        pass

    def handle_state_drop(self, code, label, global_pos):
        scene_pos = self.mapToScene(self.mapFromGlobal(global_pos))
        print(f"Handling state drop in CanvasView: code={code}, label={label}, global_pos={global_pos}, scene_pos={scene_pos}")
        # Bloc ajouté uniquement par StatesController.on_state_dropped (taille adaptée)
        
    # =========================
    # Resize handler
    # =========================
    def resizeEvent(self, event):
        super().resizeEvent(event)

        view_width = self.viewport().width()
        view_height = self.viewport().height()

        scale_x = view_width / AppConfig.REFERENCE_CANVAS_WIDTH
        scale_y = view_height / AppConfig.REFERENCE_CANVAS_HEIGHT

        # garder les proportions
        scale = min(scale_x, scale_y)

        # Reset transformation
        self.resetTransform()

        # Appliquer le zoom global
        self.scale(scale, scale)

        # Centrer la scène
        self.centerOn(AppConfig.REFERENCE_CANVAS_WIDTH / 2, AppConfig.REFERENCE_CANVAS_HEIGHT / 2)
            
    # =========================
    # 3️⃣ ÉVÉNEMENTS QT (ÉMISSION)
    # =========================

    def mousePressEvent(self, event):
        pos = self.mapToScene(event.pos())
        self.canvasClicked.emit(pos)
        super().mousePressEvent(event)

    # =========================
    # 4️⃣ MÉTHODES DE RENDU
    # =========================

    def add_zone(self, zone_id, rect):
        pass

    def add_state_graphic(self, state_id, pos):
        pass

    def add_transition_graphic(self, start_id, end_id):
        pass

    def highlight_zone(self, letter: str):
        # Désactiver l’ancien highlight
        # print(f"Highlight zone {letter} self.zones {self.zones}")
        if self.current_highlight in self.zones:
            self.zones[self.current_highlight].animate_unhighlight()

        self.current_highlight = letter

        # Activer le nouveau highlight
        if letter in self.zones:
            self.zones[letter].animate_highlight()

    def clear(self):
        self.scene.clear()

    # =========================
    # Dessin ou mise à jour des blocs
    # =========================
    def draw_layout_blocks(self, layout_data):
        # Création initiale (une seule fois)
        if not self._layout_items:
            for key, block in layout_data.items():
                item = LayoutBlockGraphicsObject(key, block)
                self.scene.addItem(item)
                self._layout_items[key] = item
                self.zones[key] = item  
            return
        # Mise à jour simple (toujours 3 blocs)
        for key, block in layout_data.items():
            if key in self._layout_items:
                self._layout_items[key].resize_block(block)
                
    # =====================================================
    # Construction des Etats
    # =====================================================
    def draw_state_blocks(self, states):
        return
        for state in states:
            graphics_item = StateGraphicsItem(state)
            self.scene.addItem(graphics_item)

    def remove_all_state_blocks(self):
        for item in list(self.scene.items()):
            if isinstance(item, EtatGraphicsObject):
                self.scene.removeItem(item)
