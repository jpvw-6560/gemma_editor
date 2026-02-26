from core.controllers.layout_controller import LayoutController
#from core.controllers.etats_controller import EtatsController
#from core.controllers.transitions_controller import TransitionsController

from core.view.palettes.layout_palette import LayoutPalette
#from core.view.palettes.etats_palette import EtatsPalette
#from core.view.palettes.transitions_palette import TransitionsPalette

def routes(router, canvas):
    router.register("layout", LayoutController, lambda _container: LayoutPalette(canvas=canvas))
    # router.register("etats", EtatsController, lambda _container: EtatsPalette(canvas=canvas))
    #router.register("transitions", TransitionsController, lambda _container: TransitionsPalette(canvas=canvas))