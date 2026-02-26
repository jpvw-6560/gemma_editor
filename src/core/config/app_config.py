
from dataclasses import dataclass
from typing import Dict
from PyQt6.QtWidgets import QApplication

# Lecture résolution écran
_app = QApplication([])
screen = _app.primaryScreen()
screen_size = screen.size()
SCREEN_WIDTH = min(screen_size.width(), 1920)
SCREEN_HEIGHT = screen_size.height()
del _app


class AppConfig:
    # Dimensions du PDF GEMMA-vide.pdf (points)
    PDF_WIDTH = 792.0
    PDF_HEIGHT = 612.0
    SHOW_PDF = False  # Afficher le PDF en fond du canvas (pour debug)
# Largeurs des menus latéraux
    LEFT_MENU_WIDTH = 200
    RIGHT_MENU_WIDTH = 150
    TOP_BANDEAU_HEIGHT = 150

    PAD = 1 # Padding
    # Taille des poignées de redimensionnement    
    HANDLE_SIZE = 12

    # Son pour les MsgToast
    TOAST_SON = True

# Calcul de la taille du canvas
    CANVAS_WIDTH = SCREEN_WIDTH - LEFT_MENU_WIDTH - RIGHT_MENU_WIDTH 
    CANVAS_HEIGHT = SCREEN_HEIGHT - TOP_BANDEAU_HEIGHT
    # print(f"AppConfig: Left_menu={LEFT_MENU_WIDTH}, CANVAS_WIDTH={CANVAS_WIDTH}, Right_menu={RIGHT_MENU_WIDTH}")
    # print(f"AppConfig: Screen_widtht={SCREEN_WIDTH}, Top_bandeau={TOP_BANDEAU_HEIGHT}, CANVAS_HEIGHT={CANVAS_HEIGHT}")

# Calcul dynamique des LayoutBlocks
@dataclass(frozen=True)
class LayoutBlock:
    id: str
    x: int
    y: int
    w: int
    h: int
    text: str
#------------------------------------------------------------------
xa = AppConfig.PAD
ya = AppConfig.PAD
wa = AppConfig.CANVAS_WIDTH // 2 - 2 * AppConfig.PAD
ha = AppConfig.CANVAS_HEIGHT // 2 - 2 * AppConfig.PAD
#------------------------------------------------------------------
xd = AppConfig.PAD
yd = AppConfig.CANVAS_HEIGHT // 2 + AppConfig.PAD
wd = AppConfig.CANVAS_WIDTH // 2 - 2 * AppConfig.PAD
hd = AppConfig.CANVAS_HEIGHT // 2 - 2 * AppConfig.PAD
#------------------------------------------------------------------
xf = AppConfig.CANVAS_WIDTH // 2 + AppConfig.PAD
yf = AppConfig.PAD
wf = AppConfig.CANVAS_WIDTH // 2 - 2 * AppConfig.PAD
hf = AppConfig.CANVAS_HEIGHT - 2 * AppConfig.PAD
#------------------------------------------------------------------

LAYOUT_BLOCKS: Dict[str, LayoutBlock] = {
    "A": LayoutBlock("A", xa, ya, wa, ha, "Procédures d'arrêt"),
    "D": LayoutBlock("D", xd, yd, wd, hd, "Procédures en Défaillance"),
    "F": LayoutBlock("F", xf, yf, wf, hf, "Procédures de Fonctionnement"),
}


# Définition des StateBlocks (exemple fixe)
@dataclass(frozen=True)
class StateBlock:
    id: str
    x: int
    y: int
    w: int
    h: int
    text: str

# Liste des états avec coordonnées extraites du PDF
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
    {"code": "A1", "label": "Arrêt dans état initial", "x": 413, "y": 57, "w": 281, "h": 109}
]
# print(f"Résolution écran détectée : {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
# print(f"State Blocs : {STATE_BLOCKS}")
# print(f"Layout Blocs : {LAYOUT_BLOCKS}")
# print(f"Canvas : {AppConfig.CANVAS_WIDTH}x{AppConfig.CANVAS_HEIGHT}")



