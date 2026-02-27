
from dataclasses import dataclass
from typing import Dict
from PyQt6.QtWidgets import QApplication


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

