"""
Graphe admissible GEMMA — liste exhaustive des transitions autorisées par état.

Source : norme GEMMA + usage industriel cohérent (sécurité, logique de conduite,
réversibilité contrôlée).

Deux règles fondamentales :
  - L'arrêt d'urgence D1 est accessible depuis TOUS les états (câblé en dur).
  - On ne redémarre jamais directement après un défaut : passage obligatoire A5→A6.

Transitions explicitement interdites (exemples) :
  F1→A1, D1→F1, A7→F1, F2→A1, D2→F1

Ce fichier fait autorité pour la validation R5 dans TransitionsController.
"""

# ---------------------------------------------------------------------------
# Transitions admissibles sortantes par état (hors règle D1 globale).
# ---------------------------------------------------------------------------
_ADJACENCE_BASE: dict[str, frozenset[str]] = {
    # Zone A — procédures d'arrêt et de remise en route
    "A1": frozenset({"A7", "F1", "F2", "F4", "F5", "F6"}),
    "A2": frozenset({"A1", "F1", "F3"}),
    "A3": frozenset({"A4", "F4", "F5"}),
    "A4": frozenset({"A5", "A6", "A7", "F1", "F4", "F5", "F6"}),
    "A5": frozenset({"A6", "A7"}),
    "A6": frozenset({"A1", "F2"}),
    "A7": frozenset({"A1", "A4", "A6"}),
    # Zone F — procédures de fonctionnement
    "F1": frozenset({"A2", "A3", "D1", "D2", "D3", "F3", "F4", "F5", "F6"}),
    "F2": frozenset({"A3", "D1", "F1"}),
    "F3": frozenset({"A1", "A2", "D1"}),
    "F4": frozenset({"A3", "A4", "A6", "D2"}),
    "F5": frozenset({"A3", "A4", "F1", "F4"}),
    "F6": frozenset({"A3", "A4", "D1", "F1"}),
    # Zone D — procédures de défaillance
    "D1": frozenset({"A5", "D2"}),
    "D2": frozenset({"A5", "D3"}),
    "D3": frozenset({"A2", "A3", "D1", "D2", "F1"}),
}

# Règle de sécurité globale : tout état (sauf D1 lui-même) peut déclencher D1
# via le bouton AU câblé en dur.
ADJACENCE_ADMISSIBLE: dict[str, frozenset[str]] = {
    state: (targets | {"D1"}) if state != "D1" else targets
    for state, targets in _ADJACENCE_BASE.items()
}
