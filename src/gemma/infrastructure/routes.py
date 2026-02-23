from gemma.ui_qt.controllers.layout_controller import LayoutController
from gemma.ui_qt.controllers.etats_controller import EtatsController
from gemma.ui_qt.controllers.transitions_controller import TransitionsController
from gemma.ui_qt.palettes.layout_palette import LayoutPalette
from gemma.ui_qt.palettes.etats_palette import EtatsPalette
from gemma.ui_qt.palettes.transitions_palette import TransitionsPalette

def register_routes(router, canvas):
    router.register("layout", LayoutController, lambda _container: LayoutPalette(canvas=canvas))
    router.register("etats", EtatsController, lambda _container: EtatsPalette(canvas=canvas))
    router.register("transitions", TransitionsController, lambda _container: TransitionsPalette(canvas=canvas))