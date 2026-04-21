from core.config.app_config import AppConfig
from core.model.layout_block import LayoutBlock

# =========================
# MODEL
# =========================
class LayoutModel:
    def __init__(self, canvas_width: int, canvas_height: int):
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.blocks = self._build_default_layout()

    def _build_default_layout(self) -> dict[str, LayoutBlock]:
        # Canvas 1620×1020 — blocs étendus jusqu'aux marges (10 px des bords et entre blocs)
        return {
            "A": LayoutBlock(
                "A", 10, 10, 910, 645,
                "PROCÉDURES D'ARRÊT"
            ),
            "D": LayoutBlock(
                "D", 10, 665, 910, 345,
                "PROCÉDURES en DÉFAILLANCE"
            ),
            "F": LayoutBlock(
                "F", 930, 10, 680, 1000,
                "PROCÉDURES DE FONCTIONNEMENT"
            ),
        }

    def get_blocks(self) -> dict[str, LayoutBlock]:
        return self.blocks