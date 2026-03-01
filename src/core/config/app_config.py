from dataclasses import dataclass
from typing import Dict
from PyQt6.QtWidgets import QApplication


class AppConfig:
    
    # Dimensions du PDF GEMMA-vide.pdf (points)
    PDF_WIDTH = 792.0
    PDF_HEIGHT = 612.0
    SHOW_PDF = False  # Afficher le PDF en fond du canvas (pour debug)

    # Largeurs des menus latéraux
    LEFT_MENU_WIDTH = 180
    RIGHT_MENU_WIDTH = 120
    TOP_BANDEAU_HEIGHT = 150

    PAD = 1 # Padding
    # Taille des poignées de redimensionnement    
    HANDLE_SIZE = 12

    # Son pour les MsgToast
    TOAST_SON = True

    # Dimensions du canvas de référence
    REFERENCE_CANVAS_WIDTH = 1534
    REFERENCE_CANVAS_HEIGHT = 1008

