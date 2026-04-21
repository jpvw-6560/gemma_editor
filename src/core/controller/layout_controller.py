from .base_mode_controller import BaseModeController
from core.model.layout_model import LayoutModel
from core.config.app_config import AppConfig
from core.model.layout_block import LayoutBlock


class LayoutController(BaseModeController):

    def __init__(self, canvas, palette=None):
        super().__init__(canvas)
        self.canvas = canvas
        self.canvas_width = AppConfig.REFERENCE_CANVAS_WIDTH
        self.canvas_height = AppConfig.REFERENCE_CANVAS_HEIGHT
        self.model = LayoutModel(self.canvas_width, self.canvas_height)
        self.palette = palette


        if self.palette:
            self._connect_palette_signals()

    def on_resize_layout(self, w, h):
        layout_data = self.recalc_blocks_for_canvas(w, h)
        print(f"[LayoutController] layout_data {layout_data}")
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
        print("Layout mode activated")
        #self.update_palette()

    def disconnect(self):
        pass

    # =====================================
    # Chargement initial ou redessin
    # =====================================
    def load_layout(self):
        layout_data = self.model.get_blocks()
        self.canvas.draw_layout_blocks(layout_data)
        pad = AppConfig.PAD
        # Générer dynamiquement les blocs à chaque appel
        blocks = {
            "A": LayoutBlock(
                "A", pad, pad,
                self.canvas_width // 2 - 2 * pad,
                self.canvas_height // 2 - 2 * pad,
                "Procédures d'arrêt"
            ),
            "D": LayoutBlock(
                "D", pad,
                self.canvas_height // 2 + pad,
                self.canvas_width // 2 - 2 * pad,
                self.canvas_height // 2 - 2 * pad,
                "Procédures en Défaillance"
            ),
            "F": LayoutBlock(
                "F",
                self.canvas_width // 2 + pad,
                pad,
                self.canvas_width // 2 - 2 * pad,
                self.canvas_height - 2 * pad,
                "Procédures de Fonctionnement"
            ),
        }
        return blocks