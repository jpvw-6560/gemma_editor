"""
grafcet_scene.py — Scène QGraphics de l'éditeur de Grafcet.

Outils disponibles :
  TOOL_SELECT     — sélection / déplacement
  TOOL_ETAPE      — clic pour poser une étape
  TOOL_TRANSITION — clic pour poser une transition
  TOOL_LIAISON    — clic-clic pour relier deux éléments
  TOOL_TRAITEMENT — clic pour poser une boîte d'équations
"""
import json
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsLineItem
from PyQt6.QtCore import Qt, QPointF, pyqtSignal
from PyQt6.QtGui import QPen, QColor

from core.view.grafcet.grafcet_items import (
    EtapeItem, TransitionItem, LiaisonItem, TraitementItem,
    MacroItem, OrBarItem, ParallelBarItem, ConnectorItem,
    ITEM_ETAPE, ITEM_TRANSITION, ITEM_LIAISON, ITEM_TRAITEMENT,
    ITEM_MACRO, ITEM_OR_BAR, ITEM_PARALLEL_BAR, ITEM_CONNECTOR,
    _SNAP_R,
)


class GrafcetScene(QGraphicsScene):
    # Émis chaque fois que la sélection change (None si rien n'est sélectionné)
    itemSelectionChanged = pyqtSignal(object)

    TOOL_SELECT             = "select"
    TOOL_ETAPE              = "etape"
    TOOL_TRANSITION         = "transition"
    TOOL_LIAISON            = "liaison"
    TOOL_TRAITEMENT         = "traitement"
    TOOL_MACRO              = "macro"
    TOOL_OR_BAR             = "or_bar"          # divergence OU (barre simple)
    TOOL_OR_BAR_CONV        = "or_bar_conv"    # convergence OU
    TOOL_PARALLEL_BAR       = "parallel_bar"    # divergence ET (double barre)
    TOOL_PARALLEL_BAR_CONV  = "parallel_bar_conv"  # convergence ET
    TOOL_CONNECTOR_OUT      = "connector_out"
    TOOL_CONNECTOR_IN       = "connector_in"

    def __init__(self):
        super().__init__()
        self.current_tool  = self.TOOL_SELECT
        self._next_num     = 1          # prochain numéro d'étape
        self._liaison_src  = None       # (EtapeItem|TransitionItem, port_name) en cours
        self._temp_line    = None       # QGraphicsLineItem guide de liaison
        self._liaisons: list[LiaisonItem] = []

        self.setSceneRect(-400, -300, 1600, 1200)
        self.selectionChanged.connect(self._on_sel_changed)

    # ── Changement d'outil ────────────────────────────────────────────────────
    def set_tool(self, tool: str):
        self.current_tool = tool
        if tool != self.TOOL_LIAISON:
            self._cancel_liaison()

    # ── Événements souris ─────────────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        pos = event.scenePos()

        if self.current_tool == self.TOOL_ETAPE:
            self._place_etape(pos)
            event.accept()
            return

        if self.current_tool == self.TOOL_TRANSITION:
            self._place_transition(pos)
            event.accept()
            return

        if self.current_tool == self.TOOL_TRAITEMENT:
            self._place_traitement(pos)
            event.accept()
            return

        if self.current_tool == self.TOOL_MACRO:
            self._place_macro(pos)
            event.accept()
            return

        if self.current_tool == self.TOOL_OR_BAR:
            self._place_or_bar(pos, role="div")
            event.accept()
            return

        if self.current_tool == self.TOOL_OR_BAR_CONV:
            self._place_or_bar(pos, role="conv")
            event.accept()
            return

        if self.current_tool == self.TOOL_PARALLEL_BAR:
            self._place_parallel_bar(pos, role="div")
            event.accept()
            return

        if self.current_tool == self.TOOL_PARALLEL_BAR_CONV:
            self._place_parallel_bar(pos, role="conv")
            event.accept()
            return

        if self.current_tool == self.TOOL_CONNECTOR_OUT:
            self._place_connector(pos, "out")
            event.accept()
            return

        if self.current_tool == self.TOOL_CONNECTOR_IN:
            self._place_connector(pos, "in")
            event.accept()
            return

        if self.current_tool == self.TOOL_LIAISON:
            self._handle_liaison_click(pos)
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.current_tool == self.TOOL_LIAISON and self._liaison_src is not None:
            pos = event.scenePos()
            src_pt = getattr(self._liaison_src[0], f"port_{self._liaison_src[1]}")()
            if self._temp_line is None:
                pen = QPen(QColor("#e67e22"), 1.5, Qt.PenStyle.DashLine)
                self._temp_line = self.addLine(
                    src_pt.x(), src_pt.y(), pos.x(), pos.y(), pen
                )
                self._temp_line.setZValue(100)
            else:
                self._temp_line.setLine(src_pt.x(), src_pt.y(), pos.x(), pos.y())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)

    # ── Placement ─────────────────────────────────────────────────────────────
    def _place_etape(self, pos: QPointF):
        item = EtapeItem(numero=self._next_num, label="Étape")
        self._next_num += 1
        item.setPos(pos.x() - item.width() / 2, pos.y() - item.height() / 2)
        self.addItem(item)
        self.clearSelection()
        item.setSelected(True)

    def _place_transition(self, pos: QPointF):
        item = TransitionItem(receptivite="1")
        item.setPos(pos.x() - item.cx(), pos.y() - item.total_height() / 2)
        self.addItem(item)
        self.clearSelection()
        item.setSelected(True)

    def _place_traitement(self, pos: QPointF):
        item = TraitementItem(titre="Traitement", lignes=[])
        item.setPos(pos.x() - item.width() / 2, pos.y() - item.height() / 2)
        self.addItem(item)
        self.clearSelection()
        item.setSelected(True)

    def _place_macro(self, pos: QPointF):
        item = MacroItem(numero=self._next_num, label="Macro")
        self._next_num += 1
        item.setPos(pos.x() - item.width() / 2, pos.y() - item.height() / 2)
        self.addItem(item)
        self.clearSelection()
        item.setSelected(True)

    def _place_or_bar(self, pos: QPointF, role: str = "div"):
        item = OrBarItem(branches=2, role=role)
        item.setPos(pos.x() - item.cx(), pos.y() - item.total_height() / 2)
        self.addItem(item)
        self.clearSelection()
        item.setSelected(True)

    def _place_parallel_bar(self, pos: QPointF, role: str = "div"):
        item = ParallelBarItem(branches=2, role=role)
        item.setPos(pos.x() - item.cx(), pos.y() - item.total_height() / 2)
        self.addItem(item)
        self.clearSelection()
        item.setSelected(True)

    def _place_connector(self, pos: QPointF, direction: str):
        item = ConnectorItem(label="X1", direction=direction)
        item.setPos(pos.x() - item.width() / 2, pos.y() - item.height() / 2)
        self.addItem(item)
        self.clearSelection()
        item.setSelected(True)

    # ── Liaison ───────────────────────────────────────────────────────────────
    def _handle_liaison_click(self, pos: QPointF):
        item, port, dist = self._find_nearest_port(pos)

        if self._liaison_src is None:
            # Début : chercher un port source
            if item and dist <= _SNAP_R:
                self._liaison_src = (item, port)
        else:
            src_item, src_port = self._liaison_src
            # Fin : créer la liaison si port différent et item différent
            if item and item is not src_item and dist <= _SNAP_R:
                liaison = LiaisonItem(src_item, src_port, item, port)
                self.addItem(liaison)
                self._liaisons.append(liaison)
            self._cancel_liaison()

    def _cancel_liaison(self):
        if self._temp_line is not None:
            self.removeItem(self._temp_line)
            self._temp_line = None
        self._liaison_src = None

    def _find_nearest_port(self, pos: QPointF):
        _connectable = (EtapeItem, TransitionItem, MacroItem,
                        OrBarItem, ParallelBarItem, ConnectorItem)
        best_item, best_port, best_dist = None, None, float("inf")
        for it in self.items():
            if isinstance(it, _connectable):
                port, dist = it.nearest_port(pos)
                if dist < best_dist:
                    best_item, best_port, best_dist = it, port, dist
        return best_item, best_port, best_dist

    # ── Mise à jour liaisons après déplacement ────────────────────────────────
    def update_liaisons_for(self, item):
        for lia in self._liaisons:
            if lia.src_item is item or lia.dst_item is item:
                lia.update_path()

    # ── Suppression ──────────────────────────────────────────────────────────
    def delete_selected(self):
        for item in list(self.selectedItems()):
            if isinstance(item, LiaisonItem) and item in self._liaisons:
                self._liaisons.remove(item)
            self.removeItem(item)

    # ── Sélection ────────────────────────────────────────────────────────────
    def _on_sel_changed(self):
        sel = self.selectedItems()
        self.itemSelectionChanged.emit(sel[0] if sel else None)

    # ── Sérialisation ─────────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        etapes, transitions = [], []
        step_by_id, trans_by_id = {}, {}
        macros, or_bars, parallel_bars, connectors = [], [], [], []
        macro_by_id, or_bar_by_id, par_bar_by_id, conn_by_id = {}, {}, {}, {}

        for it in self.items():
            if isinstance(it, EtapeItem):
                step_by_id[id(it)] = it.numero
                etapes.append({
                    "num":      it.numero,
                    "label":    it.label,
                    "actions":  it.actions,
                    "initiale": it.initiale,
                    "famille":  it.famille,
                    "x":        it.x(),
                    "y":        it.y(),
                })
            elif isinstance(it, TransitionItem):
                idx = len(trans_by_id)
                trans_by_id[id(it)] = idx
                transitions.append({
                    "idx":         idx,
                    "receptivite": it.receptivite,
                    "x":           it.x(),
                    "y":           it.y(),
                })
            elif isinstance(it, MacroItem):
                idx = len(macro_by_id)
                macro_by_id[id(it)] = idx
                macros.append({
                    "idx":    idx,
                    "numero": it.numero,
                    "label":  it.label,
                    "x":      it.x(),
                    "y":      it.y(),
                })
            elif isinstance(it, OrBarItem):
                idx = len(or_bar_by_id)
                or_bar_by_id[id(it)] = idx
                or_bars.append({
                    "idx": idx, "x": it.x(), "y": it.y(),
                    "branches": it.branches,
                    "branch_spacing": it.branch_spacing,
                    "role": it.role,
                })
            elif isinstance(it, ParallelBarItem):
                idx = len(par_bar_by_id)
                par_bar_by_id[id(it)] = idx
                parallel_bars.append({
                    "idx": idx, "x": it.x(), "y": it.y(),
                    "branches": it.branches,
                    "branch_spacing": it.branch_spacing,
                    "role": it.role,
                })
            elif isinstance(it, ConnectorItem):
                idx = len(conn_by_id)
                conn_by_id[id(it)] = idx
                connectors.append({
                    "idx":       idx,
                    "label":     it.label,
                    "direction": it.direction,
                    "x":         it.x(),
                    "y":         it.y(),
                })

        traitements = []
        for it in self.items():
            if isinstance(it, TraitementItem):
                traitements.append({
                    "titre":  it.titre,
                    "lignes": it.lignes,
                    "x":      it.x(),
                    "y":      it.y(),
                })

        def _ref(item):
            if isinstance(item, EtapeItem):
                return {"type": "etape",        "num": step_by_id.get(id(item))}
            if isinstance(item, TransitionItem):
                return {"type": "transition",   "idx": trans_by_id.get(id(item))}
            if isinstance(item, MacroItem):
                return {"type": "macro",        "idx": macro_by_id.get(id(item))}
            if isinstance(item, OrBarItem):
                return {"type": "or_bar",       "idx": or_bar_by_id.get(id(item))}
            if isinstance(item, ParallelBarItem):
                return {"type": "parallel_bar", "idx": par_bar_by_id.get(id(item))}
            if isinstance(item, ConnectorItem):
                return {"type": "connector",    "idx": conn_by_id.get(id(item))}
            return None

        liaisons = []
        for lia in self._liaisons:
            liaisons.append({
                "de":        _ref(lia.src_item),
                "de_port":   lia.src_port,
                "vers":      _ref(lia.dst_item),
                "vers_port": lia.dst_port,
            })

        return {
            "nom":           "Nouveau Grafcet",
            "etapes":        etapes,
            "transitions":   transitions,
            "traitements":   traitements,
            "macros":        macros,
            "or_bars":       or_bars,
            "parallel_bars": parallel_bars,
            "connectors":    connectors,
            "liaisons":      liaisons,
        }

    # ── Désérialisation ───────────────────────────────────────────────────────
    def from_dict(self, data: dict):
        """Charge un Grafcet depuis un dictionnaire (efface la scène préalablement)."""
        self.clear()
        self._liaisons.clear()
        self._cancel_liaison()

        step_by_num: dict[int, EtapeItem]          = {}
        trans_by_idx: dict[int, TransitionItem]    = {}
        macro_by_idx: dict[int, MacroItem]         = {}
        or_bar_by_idx: dict[int, OrBarItem]        = {}
        par_bar_by_idx: dict[int, ParallelBarItem] = {}
        conn_by_idx: dict[int, ConnectorItem]      = {}

        for e in data.get("etapes", []):
            item = EtapeItem(e["num"], e.get("label", ""), e.get("actions", []),
                             e.get("initiale", False), e.get("famille", ""))
            item.setPos(e.get("x", 0), e.get("y", 0))
            self.addItem(item)
            step_by_num[e["num"]] = item
            self._next_num = max(self._next_num, e["num"] + 1)

        for t in data.get("transitions", []):
            item = TransitionItem(t.get("receptivite", "1"))
            item.setPos(t.get("x", 0), t.get("y", 0))
            self.addItem(item)
            trans_by_idx[t["idx"]] = item

        for tr in data.get("traitements", []):
            item = TraitementItem(tr.get("titre", "Traitement"), tr.get("lignes", []))
            item.setPos(tr.get("x", 0), tr.get("y", 0))
            self.addItem(item)

        for m in data.get("macros", []):
            item = MacroItem(m.get("numero", 1), m.get("label", "Macro"))
            item.setPos(m.get("x", 0), m.get("y", 0))
            self.addItem(item)
            macro_by_idx[m["idx"]] = item
            self._next_num = max(self._next_num, m.get("numero", 1) + 1)

        for o in data.get("or_bars", []):
            item = OrBarItem(
                branches=o.get("branches", 1),
                branch_spacing=o.get("branch_spacing", 160),
                role=o.get("role", "both"),
                out_branch=o.get("out_branch", 0),
                top_branch=o.get("top_branch", 0),
                active_branches=o.get("active_branches", None),
            )
            item.setPos(o.get("x", 0), o.get("y", 0))
            self.addItem(item)
            or_bar_by_idx[o["idx"]] = item

        for p in data.get("parallel_bars", []):
            item = ParallelBarItem(
                branches=p.get("branches", 1),
                branch_spacing=p.get("branch_spacing", 160),
                role=p.get("role", "both"),
                out_branch=p.get("out_branch", 0),
            )
            item.setPos(p.get("x", 0), p.get("y", 0))
            self.addItem(item)
            par_bar_by_idx[p["idx"]] = item

        for c in data.get("connectors", []):
            item = ConnectorItem(c.get("label", "X1"), c.get("direction", "out"))
            item.setPos(c.get("x", 0), c.get("y", 0))
            self.addItem(item)
            conn_by_idx[c["idx"]] = item

        def _resolve(ref):
            if ref is None:
                return None
            t = ref.get("type")
            if t == "etape":        return step_by_num.get(ref.get("num"))
            if t == "transition":   return trans_by_idx.get(ref.get("idx"))
            if t == "macro":        return macro_by_idx.get(ref.get("idx"))
            if t == "or_bar":       return or_bar_by_idx.get(ref.get("idx"))
            if t == "parallel_bar": return par_bar_by_idx.get(ref.get("idx"))
            if t == "connector":    return conn_by_idx.get(ref.get("idx"))
            return None

        for lia in data.get("liaisons", []):
            src = _resolve(lia.get("de"))
            dst = _resolve(lia.get("vers"))
            if src and dst:
                liaison = LiaisonItem(src, lia["de_port"], dst, lia["vers_port"])
                self.addItem(liaison)
                self._liaisons.append(liaison)
