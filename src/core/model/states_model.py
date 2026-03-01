from typing import List, Optional
from core.model.state_block import StateBlock


# =========================
# Données internes (pas d'import) Coordonnées valables pour fullSize Window 1920x1080
# =========================
STATE_BLOCKS = [
    {"code": "D3", "label": "Production tout de même", "x": 390, "y": 546, "w": 290, "h": 149},
    {"code": "D2", "label": "Diagnostic et/ou traitement de défaillance", "x": 99, "y": 541, "w": 219, "h": 149},
    {"code": "D1", "label": "Arrêt d'urgence", "x": 89, "y": 770, "w": 631, "h": 88},
    {"code": "F6", "label": "Marches de test", "x": 1326, "y": 623, "w": 162, "h": 255},
    {"code": "F5", "label": "Marches de vérification dans l'ordre", "x": 1326, "y": 244, "w": 161, "h": 338},
    {"code": "F4", "label": "Marches de vérification dans le désordre", "x": 1322, "y": 41, "w": 163, "h": 161},
    {"code": "F3", "label": "Marches de clôture", "x": 1099, "y": 227, "w": 120, "h": 142},
    {"code": "F2", "label": "Marches de préparation", "x": 943, "y": 225, "w": 121, "h": 144},
    {"code": "F1", "label": "Production normale", "x": 851, "y": 422, "w": 379, "h": 301},
    {"code": "A7", "label": "Mise P.O. dans état déterminé", "x": 134, "y": 194, "w": 209, "h": 84},
    {"code": "A6", "label": "Mise P.O. dans l'état initial", "x": 78, "y": 53, "w": 270, "h": 100},
    {"code": "A5", "label": "Préparation pour remise en route après défaillance", "x": 76, "y": 299, "w": 271, "h": 147},
    {"code": "A4", "label": "Arrêt obtenu", "x": 484, "y": 197, "w": 212, "h": 82},
    {"code": "A3", "label": "Arrêt demandé dans un état déterminé", "x": 569, "y": 325, "w": 129, "h": 112},
    {"code": "A2", "label": "Arrêt demandé en fin de cycle", "x": 409, "y": 301, "w": 129, "h": 148},
    {"code": "A1", "label": "Arrêt dans état initial", "x": 413, "y": 57, "w": 281, "h": 109},
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