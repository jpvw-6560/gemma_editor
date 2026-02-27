from .base_mode_controller import BaseModeController
from core.model.layout_model import LayoutModel
from core.config.app_config import AppConfig
from core.model.layout_block import LayoutBlock


class LayoutController(BaseModeController):

    def __init__(self, canvas, palette=None):
        super().__init__(canvas)
        self.model = LayoutModel(canvas.width(), canvas.height())
        self.palette = palette

        # Connexion au signal resize du canvas
        self.canvas.resizeLayoutRequested.connect(self.on_resize_layout)

        if self.palette:
            self._connect_palette_signals()

    def on_resize_layout(self, w, h):
        layout_data = self.recalc_blocks_for_canvas(w, h)
        self.canvas.draw_layout_blocks(layout_data)


    def _connect_palette_signals(self):
        self.palette.zoneHovered.connect(self.on_zone_hovered)
        self.palette.zoneLeft.connect(self.on_zone_left)
    
    # HighLight Item de la liste + zone sur le canvas
    def on_zone_hovered(self, letter: str):
        if self.canvas:
            self.canvas.highlight_zone(letter)

    def on_zone_left(self):
        if self.canvas:
            self.canvas.highlight_zone(None)

    def connect(self):
        self.load_layout()

    def disconnect(self):
        pass

    # =====================================
    # Chargement initial ou redessin
    # =====================================
    def load_layout(self):
        layout_data = self.recalc_blocks_for_canvas(
            self.canvas.viewport().width(),
            self.canvas.viewport().height()
        )
        self.canvas.draw_layout_blocks(layout_data)

    # =====================================
    # Recalcul dynamique pour resize
    # =====================================
    def recalc_blocks_for_canvas(self, canvas_width, canvas_height) -> dict[str, LayoutBlock]:
        # print(f"Recalcul des blocs pour canvas {canvas_width}x{canvas_height}")
        pad = AppConfig.PAD
        # Générer dynamiquement les blocs à chaque appel
        blocks = {
            "A": LayoutBlock(
                "A", pad, pad,
                canvas_width // 2 - 2 * pad,
                canvas_height // 2 - 2 * pad,
                "Procédures d'arrêt"
            ),
            "D": LayoutBlock(
                "D", pad,
                canvas_height // 2 + pad,
                canvas_width // 2 - 2 * pad,
                canvas_height // 2 - 2 * pad,
                "Procédures en Défaillance"
            ),
            "F": LayoutBlock(
                "F",
                canvas_width // 2 + pad,
                pad,
                canvas_width // 2 - 2 * pad,
                canvas_height - 2 * pad,
                "Procédures de Fonctionnement"
            ),
        }
        return blocks