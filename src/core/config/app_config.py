from dataclasses import dataclass
from typing import Dict



class AppConfig:
    
    # Dimensions du PDF GEMMA-vide.pdf (points)
    PDF_WIDTH = 792.0
    PDF_HEIGHT = 612.0
    SHOW_PDF = False  # Afficher le PDF en fond du canvas (pour debug)

    # Largeurs des menus latéraux
    LEFT_MENU_WIDTH = 150
    RIGHT_MENU_WIDTH = 180
    TOP_BANDEAU_HEIGHT = 150

    PAD = 1 # Padding
    # Taille des poignées de redimensionnement    
    HANDLE_SIZE = 12

    # Son pour les MsgToast
    TOAST_SON = True

    # Style QToolTip global (fond jaune, bord noir)
    # À inclure dans tout setStyleSheet() appliqué directement sur un widget
    # (les bulles CSS isolées n'héritent pas du stylesheet de l'application)
    TOOLTIP_QSS = (
        " QToolTip { background-color:#FFFF00; color:black;"
        " border:1px solid black; padding:0px 3px; margin:0px; font-size:11px; }"
    )

    # Dimensions du canvas de référence
    REFERENCE_CANVAS_WIDTH = 1620
    REFERENCE_CANVAS_HEIGHT = 1020

