from typing import List, Optional
from core.model.state_block import StateBlock


# =========================
# Positions dérivées du fichier de référence :
#   /doc/le_gemma_plus_fleches.gif  (803×595)
# et du PDF GEMMA-vide.pdf (page 792×612 après rotation).
# Scalée sur le canvas de référence : 1620×1020.
# =========================
STATE_BLOCKS = [
    # Positions extraites par analyse BFS du GIF de référence
    # le_gemma_plus_fleches.gif (803×595) → canvas 1620×1020
    {
        "code": "A1",
        "label": "Arrêt dans état initial",
        "x": 510, "y": 110, "w": 266, "h": 75
    },
    {
        "code": "A2",
        "label": "Arrêt demandé en fin de cycle",
        "x": 506, "y": 425, "w": 109, "h": 213
    },
    {
        "code": "A3",
        "label": "Arrêt demandé dans un état déterminé",
        "x": 673, "y": 425, "w": 107, "h": 161
    },
    {
        "code": "A4",
        "label": "Arrêt obtenu",
        "x": 589, "y": 264, "w": 192, "h": 96
    },
    {
        "code": "A5",
        "label": "Préparation pour remise en route après défaillance",
        "x": 147, "y": 425, "w": 270, "h": 213
    },
    {
        "code": "A6",
        "label": "Mise P.O. dans l'état initial",
        "x": 147, "y": 106, "w": 270, "h": 84
    },
    {
        "code": "A7",
        "label": "Mise P.O. dans état déterminé",
        "x": 192, "y": 264, "w": 226, "h": 96
    },
    {
        "code": "D1",
        "label": "Arrêt d'urgence",
        "x": 147, "y": 837, "w": 633, "h": 84
    },
    {
        "code": "D2",
        "label": "Diagnostic et/ou traitement de défaillance",
        "x": 192, "y": 684, "w": 226, "h": 87
    },
    {
        "code": "D3",
        "label": "Production tout de même",
        "x": 506, "y": 684, "w": 274, "h": 87
    },
    {
        "code": "F1",
        "label": "Production normale",
        "x": 946, "y": 466, "w": 359, "h": 305
    },
    {
        "code": "F2",
        "label": "Marches de préparation",
        "x": 1031, "y": 266, "w": 109, "h": 153
    },
    {
        "code": "F3",
        "label": "Marches de clôture",
        "x": 1196, "y": 266, "w": 109, "h": 153
    },
    {
        "code": "F4",
        "label": "Marches de vérification dans le désordre",
        "x": 1428, "y": 84, "w": 147, "h": 144
    },
    {
        "code": "F5",
        "label": "Marches de vérification dans l'ordre",
        "x": 1428, "y": 293, "w": 147, "h": 386
    },
    {
        "code": "F6",
        "label": "Marches de test",
        "x": 1428, "y": 729, "w": 147, "h": 192
    },
]


# =========================
# MODEL
# =========================
class StatesModel:
    """
    Modèle métier des états GEMMA.
    Totalement indépendant du GUI.
    """

    def __init__(self):
        self._states: List[StateBlock] = []
        self._populate_states()

    # -------------------------
    # Initialisation interne
    # -------------------------
    def _populate_states(self):
        self._states = [
            StateBlock(
                code=e["code"],
                label=e["label"],
                x=e["x"],
                y=e["y"],
                w=e["w"],
                h=e["h"],
            )
            for e in STATE_BLOCKS
        ]

    # -------------------------
    # Accès
    # -------------------------
    def all(self) -> List[StateBlock]:
        return list(self._states)

    def get_by_code(self, code: str) -> Optional[StateBlock]:
        return next((s for s in self._states if s.code == code), None)

    # -------------------------
    # Gestion dynamique
    # -------------------------
    def remove(self, code: str):
        self._states = [s for s in self._states if s.code != code]

    def add(self, state: StateBlock):
        if not self.get_by_code(state.code):
            self._states.append(state)

    def reset(self):
        self._populate_states()

    # -------------------------
    # Export / Import
    # -------------------------
    def to_dict_list(self) -> List[dict]:
        return [
            {
                "code": s.code,
                "label": s.label,
                "x": s.x,
                "y": s.y,
                "w": s.w,
                "h": s.h,
            }
            for s in self._states
        ]

    def load_from_dict_list(self, data: List[dict]):
        self._states = [
            StateBlock(
                code=d["code"],
                label=d["label"],
                x=d["x"],
                y=d["y"],
                w=d["w"],
                h=d["h"],
            )
            for d in data
        ]