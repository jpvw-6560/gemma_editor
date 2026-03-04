
from PyQt6.QtCore import QObject
from core.view.canvas_view import EtatGraphicsObject, TransitionArrow
from core.services.toast.toast import MsgToast

class TransitionsController(QObject):
    from core.view.canvas_view import TransitionArrow
    def __init__(self, canvas, palette):
        super().__init__()
        self.canvas = canvas
        self.palette = palette
        self._adding_transition = False
        self._origin_state = None
        self._end_state = None
        self._transitions = []  # Liste des transitions (origine, fin)
        # Connexion du bouton +Transition
        self.palette.addTransitionRequested.connect(self.start_add_transition)

    def start_add_transition(self):
        # Vérifier s'il existe des états sur le canvas
        states = [item for item in self.canvas.scene.items() if isinstance(item, EtatGraphicsObject)]
        if not states:
            MsgToast.error("Erreur", "Aucun état sur le canvas !\nVeuillez charger les Etats", parent=self.canvas.window())
            return
        # Lancer la procédure de sélection
        self._adding_transition = True
        self._origin_state = None
        self._end_state = None
        # Informer l'utilisateur
        MsgToast.info("Ajout de transition", "Cliquez sur l'état d'origine, puis sur l'état de fin.", parent=self.canvas.window())
        # Installer un event filter sur le canvas pour capter les clics
        self.canvas.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if not self._adding_transition:
            return False
        if event.type() == QEvent.Type.MouseButtonPress:
            pos = self.canvas.mapToScene(event.pos())
            # Chercher l'état sous le clic
            for item in self.canvas.scene.items():
                if isinstance(item, EtatGraphicsObject) and item.contains(item.mapFromScene(pos)):
                    if self._origin_state is None:
                        self._origin_state = item
                        MsgToast.info("Sélection", f"État origine sélectionné : {item.code}. Cliquez sur l'état de fin.", parent=self.canvas.window())
                        return True
                    elif self._end_state is None and item != self._origin_state:
                        self._end_state = item
                        self.finish_add_transition()
                        return True
        return False

    def finish_add_transition(self):
        origin_code = self._origin_state.code
        end_code = self._end_state.code
        # Vérifier si la transition existe déjà
        if (origin_code, end_code) in self._transitions:
            MsgToast.warning("Doublon", f"La transition {origin_code} → {end_code} existe déjà.", parent=self.canvas.window())
        else:
            self._transitions.append((origin_code, end_code))
            MsgToast.success("Ajout", f"Transition ajoutée : {origin_code} → {end_code}", parent=self.canvas.window())
            self.palette.set_transitions_list(self._transitions)
            # Ajout de la flèche à la scène
            arrow = TransitionArrow(self._origin_state, self._end_state)
            self.canvas.scene.addItem(arrow)
            # Mise à jour dynamique : connecte les signaux de déplacement/redimensionnement
            def update_arrow():
                arrow.update_arrow()
            # Connecte setPos et prepareGeometryChange pour mise à jour dynamique
            self._origin_state._original_setPos = self._origin_state.setPos
            self._end_state._original_setPos = self._end_state.setPos
            def origin_setPos(*args, **kwargs):
                result = self._origin_state._original_setPos(*args, **kwargs)
                update_arrow()
                return result
            def end_setPos(*args, **kwargs):
                result = self._end_state._original_setPos(*args, **kwargs)
                update_arrow()
                return result
            self._origin_state.setPos = origin_setPos
            self._end_state.setPos = end_setPos
            # Pour resize
            self._origin_state._original_prepareGeometryChange = self._origin_state.prepareGeometryChange
            self._end_state._original_prepareGeometryChange = self._end_state.prepareGeometryChange
            def origin_prepareGeometryChange(*args, **kwargs):
                result = self._origin_state._original_prepareGeometryChange(*args, **kwargs)
                update_arrow()
                return result
            def end_prepareGeometryChange(*args, **kwargs):
                result = self._end_state._original_prepareGeometryChange(*args, **kwargs)
                update_arrow()
                return result
            self._origin_state.prepareGeometryChange = origin_prepareGeometryChange
            self._end_state.prepareGeometryChange = end_prepareGeometryChange

    def _wrap_setPos(self, orig_setPos, update_arrow):
        def new_setPos(*args, **kwargs):
            result = orig_setPos(*args, **kwargs)
            update_arrow()
            return result
        return new_setPos

    def _wrap_prepareGeometryChange(self, orig_func, update_arrow):
        def new_func(*args, **kwargs):
            result = orig_func(*args, **kwargs)
            update_arrow()
            return result
        return new_func
        # Nettoyer
        self._adding_transition = False
        self._origin_state = None
        self._end_state = None
        self.canvas.viewport().removeEventFilter(self)