"""
Modèle statique des 35 flèches GEMMA (33 originales + F1→A2 et A4→A6 ajoutées).

Coordonnées pixel absolues validées visuellement sur un canvas 1620×1020.
Ce fichier fait autorité — ne pas modifier sans recalibration sur le canvas
de référence (bouton « Save → fleches.json » puis copie ici).

Chaque entrée :
    "de"        : code de l'état origine
    "vers"      : code de l'état destination
    "condition" : condition GEMMA par défaut (utilisée si le questionnaire
                  ne fournit pas de condition pour cette transition)
    "points"    : liste de waypoints {x, y} définissant le tracé de la flèche.
                  Liste vide = routage automatique droit.
"""

FLECHES_MODEL: dict[str, dict] = {
    "A1_F1": {
        "de": "A1", "vers": "F1", "condition": "Depart_cycle",
        "points": [{"x": 776.0, "y": 173.9}, 
                   {"x": 981.7, "y": 173.9},
                   {"x": 981.7, "y": 466.0}],
    },
    "A1_F2": {
        "de": "A1", "vers": "F2", "condition": "Mode_preparation",
        "points": [{"x": 776.0, "y": 160.5}, {"x": 1085.0, "y": 160.5},
                   {"x": 1085.0, "y": 266.0}],
    },
    "A1_F4": {
        "de": "A1", "vers": "F4", "condition": "Mode_verif_libre",
        "points": [{"x": 776.0, "y": 117.9}, {"x": 1428.0, "y": 117.9}],
    },
    "A1_F5": {
        "de": "A1", "vers": "F5", "condition": "Mode_verif_seq",
        "points": [{"x": 776.0, "y": 130.1}, {"x": 1373.0, "y": 130.1},
                   {"x": 1373.0, "y": 335.3}, {"x": 1428.0, "y": 335.3}],
    },
    "A2_A1": {
        "de": "A2", "vers": "A1", "condition": "Fin_cycle",
        "points": [{"x": 560.5, "y": 425.0}, {"x": 560.5, "y": 185.0}],
    },
    "A3_A4": {
        "de": "A3", "vers": "A4", "condition": "Arret_obtenu",
        "points": [],
    },
    "A4_A6": {
        "de": "A4", "vers": "A6", "condition": "Init_position",
        "points": [{"x": 589.0, "y": 302.0}, {"x": 442.0, "y": 302.0},
                   {"x": 442.0, "y": 168.0}, {"x": 417.0, "y": 168.0}],
    },
    "A4_F1": {
        "de": "A4", "vers": "F1", "condition": "Remise_en_marche",
        "points": [{"x": 781.0, "y": 317.0}, {"x": 964.3, "y": 317.0},
                   {"x": 964.3, "y": 466.0}],
    },
    "A5_A6": {
        "de": "A5", "vers": "A6", "condition": "Reset_machine",
        "points": [{"x": 173.0, "y": 425},{"x": 173.0, "y": 190.0}],
    },
    "A5_A7": {
        "de": "A5", "vers": "A7", "condition": "Mode_reglage",
        "points": [{"x": 309.5, "y": 425.0}, {"x": 309.5, "y": 360.0}],
    },
    "A6_A1": {
        "de": "A6", "vers": "A1", "condition": "Init_OK",
        "points": [{"x": 417.0, "y": 147.5}, {"x": 510.0, "y": 147.5}],
    },
    "A7_A4": {
        "de": "A7", "vers": "A4", "condition": "Arret_obtenu",
        "points": [{"x": 418.0, "y": 317.0}, {"x": 589.0, "y": 317.0}],
    },
    "A7_A6": {
        "de": "A7", "vers": "A6", "condition": "Quitter_reglage",
        "points": [{"x": 309.5, "y": 264.0}, {"x": 309.5, "y": 190.0}],
    },
    "D1_A5": {
        "de": "D1", "vers": "A5", "condition": "Reset_direct",
        "points": [{"x": 169.0, "y": 837.0}, {"x": 167.0, "y": 837.0},
                   {"x": 167.0, "y": 638.0}],
    },
    "D1_D2": {
        "de": "D1", "vers": "D2", "condition": "EU_relachee",
        "points": [{"x": 305.0, "y": 837.0}, {"x": 305.0, "y": 771.0}],
    },
    "D2_A5": {
        "de": "D2", "vers": "A5", "condition": "Acquit_defaut",
        "points": [{"x": 309.5, "y": 684.0}, {"x": 309.5, "y": 638.0}],
    },
    "D3_A2": {
        "de": "D3", "vers": "A2", "condition": "Stop",
        "points": [{"x": 560.5, "y": 684.0}, {"x": 560.5, "y": 638.0}],
    },
    "D3_A3": {
        "de": "D3", "vers": "A3", "condition": "Stop_immediat",
        "points": [{"x": 734.6, "y": 684.0}, {"x": 734.6, "y": 586.0}],
    },
    "D3_D2": {
        "de": "D3", "vers": "D2", "condition": "Defaut_majeur",
        "points": [{"x": 506.0, "y": 732.5}, {"x": 418.0, "y": 732.5}],
    },
    "F1_A2": {
        "de": "F1", "vers": "A2", "condition": "Stop",
        "points": [{"x": 946.0, "y": 620.0}, {"x": 615.0, "y": 620.0}],
    },
    "F1_A3": {
        "de": "F1", "vers": "A3", "condition": "Stop_immediat",
        "points": [{"x": 946.0, "y": 530.0}, {"x": 780.0, "y": 530.0}],
    },
    "F1_D1": {
        "de": "F1", "vers": "D1", "condition": "Defaut",
        "points": [{"x": 1147.7, "y": 771.0}, {"x": 1147.7, "y": 854.6},
                   {"x": 780.0, "y": 854.6}],
    },
    "F1_D2": {
        "de": "F1", "vers": "D2", "condition": "Defaut_direct",
        "points": [{"x": 990.8, "y": 771.0}, {"x": 990.8, "y": 815.0},
                   {"x": 375.2, "y": 815.0}, {"x": 375.2, "y": 771.0}],
    },
    "F1_D3": {
        "de": "F1", "vers": "D3", "condition": "Defaut_mineur",
        "points": [{"x": 946.0, "y": 700.9}, {"x": 780.0, "y": 700.9}],
    },
    "F1_F3": {
        "de": "F1", "vers": "F3", "condition": "Mode_cloture",
        "points": [{"x": 1255.5, "y": 466.0}, {"x": 1255.5, "y": 419.0}],
    },
    "F1_F4": {
        "de": "F1", "vers": "F4", "condition": "Mode_verif_libre",
        "points": [{"x": 1305.0, "y": 517.0}, {"x": 1335.0, "y": 517.0},
                   {"x": 1335.0, "y": 201.5}, {"x": 1428.0, "y": 201.5}],
    },
    "F1_F5": {
        "de": "F1", "vers": "F5", "condition": "Mode_verif_seq",
        "points": [{"x": 1305.0, "y": 603.0}, {"x": 1428.0, "y": 603.0}],
    },
    "F1_F6": {
        "de": "F1", "vers": "F6", "condition": "Mode_test",
        "points": [{"x": 1305.0, "y": 740.7}, {"x": 1428.0, "y": 740.7}],
    },
    "F2_F1": {
        "de": "F2", "vers": "F1", "condition": "Preparation_ok",
        "points": [{"x": 1092.5, "y": 419.0}, {"x": 1092.5, "y": 466.0}],
    },
    "F3_A1": {
        "de": "F3", "vers": "A1", "condition": "Cloture_ok",
        "points": [{"x": 1246.9, "y": 266.0}, {"x": 1246.9, "y": 142.5},
                   {"x": 776.0, "y": 142.5}],
    },
    "F4_A6": {
        "de": "F4", "vers": "A6", "condition": "CI",
        "points": [{"x": 1501.5, "y": 82.0}, {"x": 1501.5, "y": 50.4},
                   {"x": 367.1, "y": 50.4}, {"x": 367.1, "y": 106.0}],
    },
    "F5_F1": {
        "de": "F5", "vers": "F1", "condition": "Fin_verif",
        "points": [{"x": 1428.0, "y": 577.5}, {"x": 1305.0, "y": 577.5}],
    },
    "F5_F4": {
        "de": "F5", "vers": "F4", "condition": "Passage_verif_libre",
        "points": [{"x": 1509.6, "y": 293.0}, {"x": 1509.6, "y": 228.0}],
    },
    "F6_D1": {
        "de": "F6", "vers": "D1", "condition": "AU",
        "points": [{"x": 1428.0, "y": 885.0}, {"x": 780.0, "y": 885.0}],
    },
    "F6_F1": {
        "de": "F6", "vers": "F1", "condition": "Fin_test",
        "points": [{"x": 1428.0, "y": 755.0}, {"x": 1305.0, "y": 755.0}],
    },
}
