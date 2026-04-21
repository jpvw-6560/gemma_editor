"""
Contrôleur de simulation GEMMA.

Reçoit la liste des transitions (issue du canvas ou du JSON), gère l'état
actif courant, met en surbrillance les états sur le canvas et pilote la
SimulationPalette.
"""
from PyQt6.QtCore import QObject


class SimulationController(QObject):
    """
    Moteur de simulation pour la machine d'états GEMMA.

    Paramètres
    ----------
    canvas      : CanvasView
    palette     : SimulationPalette
    transitions : list[dict]  — chaque dict contient au moins
                               {"de": str, "vers": str, "condition": str}
    """

    def __init__(self, canvas, palette, transitions):
        super().__init__()
        self._canvas      = canvas
        self._palette     = palette
        self._transitions = transitions          # [{de, vers, condition}]
        self._current     = None                 # code de l'état actif

        # Index des items graphiques et labels depuis le canvas
        from core.view.canvas_view import EtatGraphicsObject
        self._items  = {}   # {code: EtatGraphicsObject}
        self._labels = {}   # {code: label}
        for item in canvas.scene.items():
            if isinstance(item, EtatGraphicsObject):
                self._items[item.code]  = item
                self._labels[item.code] = item.label

        # Signaux palette → contrôleur
        palette.initRequested.connect(self.init)
        palette.resetRequested.connect(self.init)
        palette.bpFired.connect(self._on_bp_fired)

    # ─── API publique ────────────────────────────────────────────────────────────

    def init(self):
        """Initialise la simulation : met A1 actif (fond rouge)."""
        self._activate("A1")

    def reset(self):
        """Désactive l'état courant sans en activer un nouveau."""
        if self._current and self._current in self._items:
            self._items[self._current].set_sim_active(False)
        self._current = None
        self._palette.update_state("", "", [])

    # ─── Logique interne ─────────────────────────────────────────────────────────

    def _activate(self, code: str):
        """Active l'état `code` sur le canvas et met à jour la palette."""
        # Désactiver l'ancien état
        if self._current and self._current in self._items:
            self._items[self._current].set_sim_active(False)

        self._current = code

        # Activer le nouvel état (fond rouge)
        if code in self._items:
            self._items[code].set_sim_active(True)
        else:
            # L'état n'est pas présent sur le canvas ─ on met quand même à jour la palette
            pass

        outgoing = self._get_outgoing(code)
        desc = self._labels.get(code, "")
        self._palette.update_state(code, desc, outgoing)

    def _get_outgoing(self, code: str) -> list:
        """Retourne [(dest_code, dest_label, condition)] depuis l'état `code`."""
        result = []
        for t in self._transitions:
            if t.get("de") == code:
                dest  = t.get("vers", "")
                cond  = t.get("condition", "") or ""
                label = self._labels.get(dest, "")
                result.append((dest, label, cond))
        return result

    def _on_bp_fired(self, dest_code: str, condition: str):
        """Réception d'un appui sur un bouton BP → activation immédiate de la transition."""
        self._activate(dest_code)
