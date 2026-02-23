from PyQt6.QtWidgets import QVBoxLayout, QWidget


class Router:
    """
    Router minimal pour GEMMA Editor.
    Il mappe un 'mode' sur un controller et une palette.
    """

    def __init__(self):
        self._routes = {}
        self.current_mode = None

    def register(self, mode_name, controller_cls=None, palette_cls=None):
        """
        Enregistre un mode.
        :param mode_name: str, nom du mode (ex: "layout", "etats", "transitions")
        :param controller_cls: classe du controller à instancier
        :param palette_cls: classe de la palette à instancier
        """
        self._routes[mode_name] = {
            "controller_cls": controller_cls,
            "palette_cls": palette_cls
        }


    def navigate(self, mode_name, container, ui_right_menu):
        if mode_name not in self._routes:
            raise ValueError(f"Mode '{mode_name}' non enregistré dans le Router.")

        self.current_mode = mode_name
        route = self._routes[mode_name]

        controller = route["controller_cls"](container) if route["controller_cls"] else None

        palette_cls_or_instance = route["palette_cls"]
        if palette_cls_or_instance:
            palette = palette_cls_or_instance(container) if callable(palette_cls_or_instance) else palette_cls_or_instance
        else:
            palette = None

        # 👉 on délègue totalement à RightMenu
        ui_right_menu.set_palette(palette)

        return controller