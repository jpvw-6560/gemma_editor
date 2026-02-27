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
        pad = AppConfig.PAD
        w = self.canvas_width
        h = self.canvas_height

        return {
            "A": LayoutBlock(
                "A", pad, pad,
                w // 2 - 2 * pad,
                h // 2 - 2 * pad,
                "Procédures d'arrêt"
            ),
            "D": LayoutBlock(
                "D", pad,
                h // 2 + pad,
                w // 2 - 2 * pad,
                h // 2 - 2 * pad,
                "Procédures en Défaillance"
            ),
            "F": LayoutBlock(
                "F",
                w // 2 + pad,
                pad,
                w // 2 - 2 * pad,
                h - 2 * pad,
                "Procédures de Fonctionnement"
            ),
        }

    def get_blocks(self) -> dict[str, LayoutBlock]:
        return self.blocks