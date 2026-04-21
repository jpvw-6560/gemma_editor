
import os
from PyQt6.QtCore import QObject, Qt, QEvent, pyqtSignal
from PyQt6.QtGui import QColor
from core.view.canvas_view import EtatGraphicsObject, TransitionArrow
from core.services.toast.toast import MsgToast
from core.utils.gemma_transitions_tools import GemmaTransitionsTools, GEMMA_ALLOWED_TRANSITIONS

class TransitionsController(QObject):
    validationChanged    = pyqtSignal(bool)   # émis quand _validation_ok change de valeur
    questionnaireApplied = pyqtSignal()       # émis après l'application du questionnaire
    transitionsChanged   = pyqtSignal()       # émis après toute modification de transitions

    def __init__(self, canvas, palette):
        super().__init__()
        self.canvas = canvas
        self.palette = palette
        self._adding_transition = False
        self._origin_state = None
        self._end_state = None
        self._transitions = []   # Liste de tuples (origine, fin)
        self._conditions  = {}   # dict {(origine, fin): str}
        self._validation_ok = False  # True uniquement après vérification sans erreurs
        self._app_json_path = None   # chemin du JSON courant (mis à jour par AppController)
        # Connexions des boutons de la palette
        self.palette.addTransitionRequested.connect(self.start_add_transition)
        self.palette.initBaseRequested.connect(self.init_base_transitions)
        self.palette.mettreAJourRequested.connect(self.mettre_a_jour_fleches)
        self.palette.sauvegarderFlechesRequested.connect(self.sauvegarder_fleches_json)
        self.palette.resetRequested.connect(self.reset_transitions)
        self.palette.deleteTransitionRequested.connect(self.delete_transition)
        self.palette.transitionSelected.connect(self.highlight_transition)
        self.palette.conditionEditRequested.connect(self.set_transition_condition)
        self.palette.questionnaireRequested.connect(self.open_questionnaire)
        self.palette.saveRequested.connect(self.save_transitions)
        self.palette.openRequested.connect(self.load_transitions)
        self.palette.validateRequested.connect(self.validate_transitions)

    def repopulate_from_canvas(self):
        """Re-peuple _transitions et _conditions depuis les flèches déjà sur le canvas."""
        from core.view.canvas_view import TransitionArrow
        from core.model.fleches_model import FLECHES_MODEL
        self._transitions.clear()
        self._conditions.clear()
        for item in self.canvas.scene.items():
            if isinstance(item, TransitionArrow):
                o = item.start_item.code
                e = item.end_item.code
                key = (o, e)
                if key not in self._transitions:
                    self._transitions.append(key)
                cond = getattr(item, 'condition', '') or ''
                if not cond:
                    # Fallback : condition par défaut définie dans FLECHES_MODEL
                    cond = FLECHES_MODEL.get(f"{o}_{e}", {}).get("condition", "")
                    if cond:
                        item.set_condition(cond)   # rétablit l'affichage sur la flèche
                if cond:
                    self._conditions[key] = cond
        self.palette.set_transitions_list(self._get_transitions_with_conditions())

    def _set_validation_ok(self, val: bool):
        """Met à jour _validation_ok, émet validationChanged si changement, et écrit dans le JSON."""
        if self._validation_ok != val:
            self._validation_ok = val
            self.validationChanged.emit(val)
        # Écriture directe dans le fichier JSON courant (indépendante du signal)
        if self._app_json_path:
            import json as _json, os as _os
            try:
                if _os.path.isfile(self._app_json_path):
                    with open(self._app_json_path, "r", encoding="utf-8") as f:
                        data = _json.load(f)
                    data["validation_ok"] = val
                    with open(self._app_json_path, "w", encoding="utf-8") as f:
                        _json.dump(data, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

    def _get_transitions_with_conditions(self):
        """Retourne la liste [(origin, end, condition), ...] pour la palette."""
        return [(o, e, self._conditions.get((o, e), "")) for (o, e) in self._transitions]

    def set_transition_condition(self, origin_code, end_code, condition):
        """Met à jour la condition d'une transition et son affichage sur le canvas."""
        key = (origin_code, end_code)
        if key not in self._transitions:
            return
        self._conditions[key] = condition
        # Mettre à jour la flèche sur le canvas
        for item in self.canvas.scene.items():
            if isinstance(item, TransitionArrow) \
               and item.start_item.code == origin_code \
               and item.end_item.code == end_code:
                item.set_condition(condition)
                break
        self.palette.set_transitions_list(self._get_transitions_with_conditions())
        self.transitionsChanged.emit()

    def auto_layout_states(self):
        # Utilise NetworkX pour calculer les positions
        # Récupère tous les codes d'états présents
        state_items = [item for item in self.canvas.scene.items() if isinstance(item, EtatGraphicsObject)]
        state_codes = [item.code for item in state_items]
        # Recalcule les positions
        gtools = GemmaTransitionsTools(self._transitions)
        positions = gtools.get_layout_positions(layout='spring', scale=500)
        # Applique les positions
        for item in state_items:
            if item.code in positions:
                x, y = positions[item.code]
                # Utilise la méthode originale pour éviter la récursion
                if hasattr(item, '_original_setPos'):
                    item._original_setPos(x, y)
                else:
                    item.setPos(x, y)
        # Met à jour toutes les flèches
        for arrow in [item for item in self.canvas.scene.items() if isinstance(item, TransitionArrow)]:
            arrow.update_arrow()

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

        if not self._adding_transition:
            return False
        if event.type() == QEvent.Type.MouseButtonPress:
            pos = self.canvas.mapToScene(event.pos())
            # Chercher l'état sous le clic
            for item in self.canvas.scene.items():
                if isinstance(item, EtatGraphicsObject) and item.contains(item.mapFromScene(pos)):
                    if self._origin_state is None:
                        self._origin_state = item
                        # Bordure rouge
                        self._origin_state._border_color = Qt.GlobalColor.red
                        self._origin_state.update()
                        MsgToast.info("Sélection", f"État origine sélectionné : {item.code}. Cliquez sur l'état de fin.", parent=self.canvas.window())
                        return True
                    elif self._end_state is None and item != self._origin_state:
                        self._end_state = item
                        # Bordure rouge
                        self._end_state._border_color = Qt.GlobalColor.red
                        self._end_state.update()
                        self.finish_add_transition()
                        return True
        return False

    def _is_allowed(self, origin_code, end_code):
        """Vérifie que la transition est autorisée par la topologie GEMMA."""
        return (origin_code, end_code) in GEMMA_ALLOWED_TRANSITIONS

    def _add_arrow_to_scene(self, origin_item, end_item):
        """Crée et ajoute la flèche sur la scène (itemChange/arrows[] gère le suivi dynamique)."""
        arrow = TransitionArrow(origin_item, end_item)
        self.canvas.scene.addItem(arrow)
        return arrow

    def finish_add_transition(self):
        origin_code = self._origin_state.code
        end_code = self._end_state.code

        # Vérifier si la transition existe déjà
        if (origin_code, end_code) in self._transitions:
            MsgToast.warning("Doublon", f"La transition {origin_code} → {end_code} existe déjà.", parent=self.canvas.window())
        # Vérifier la topologie GEMMA
        elif not self._is_allowed(origin_code, end_code):
            MsgToast.error(
                "Transition non autorisée",
                f"{origin_code} → {end_code} n'existe pas dans le diagramme GEMMA standard.",
                parent=self.canvas.window()
            )
        else:
            self._transitions.append((origin_code, end_code))
            self._set_validation_ok(False)
            self._add_arrow_to_scene(self._origin_state, self._end_state)
            self.palette.set_transitions_list(self._get_transitions_with_conditions())
            self.transitionsChanged.emit()
            MsgToast.success("Ajout", f"Transition ajoutée : {origin_code} → {end_code}", parent=self.canvas.window())

        # Remettre les bordures à la normale et nettoyer l'état
        for item in (self._origin_state, self._end_state):
            if item:
                item._border_color = Qt.GlobalColor.black
                item.update()
        self._adding_transition = False
        self._origin_state = None
        self._end_state = None
        self.canvas.viewport().removeEventFilter(self)

    def _clear_highlight(self):
        """Retire la surbrillance de tous les éléments du canvas."""
        for item in self.canvas.scene.items():
            if isinstance(item, TransitionArrow):
                item.set_highlighted(False)
                item._show_condition = False
            elif isinstance(item, EtatGraphicsObject):
                item.animate_state_block_unhighlight()
        # Forcer un rafraîchissement complet de la scène : le label de condition
        # peut dépasser la bounding rect de la flèche et ne pas être effacé par update()
        self.canvas.scene.update()

    def highlight_transition(self, origin_code, end_code):
        """Met en surbrillance la flèche et les deux états correspondants."""
        self._clear_highlight()
        for item in self.canvas.scene.items():
            if isinstance(item, TransitionArrow) \
               and item.start_item.code == origin_code \
               and item.end_item.code == end_code:
                item.set_highlighted(True)
                item._show_condition = True
                item.update()
            elif isinstance(item, EtatGraphicsObject) \
               and item.code in (origin_code, end_code):
                item._border_color = QColor("#f39c12")
                item.update()

    def delete_transition(self, origin_code, end_code):
        """Supprime une seule transition depuis la liste (clic droit)."""
        key = (origin_code, end_code)
        if key not in self._transitions:
            return
        # Retirer la flèche correspondante du canvas
        for arrow in list(self.canvas.scene.items()):
            if isinstance(arrow, TransitionArrow) \
               and arrow.start_item.code == origin_code \
               and arrow.end_item.code == end_code:
                arrow._clear_handles()
                if arrow in arrow.start_item.arrows:
                    arrow.start_item.arrows.remove(arrow)
                if arrow in arrow.end_item.arrows:
                    arrow.end_item.arrows.remove(arrow)
                self.canvas.scene.removeItem(arrow)
                break
        self._conditions.pop(key, None)
        self._transitions.remove(key)
        self._set_validation_ok(False)
        self.palette.set_transitions_list(self._get_transitions_with_conditions())
        self.transitionsChanged.emit()
        MsgToast.info("Suppression", f"Transition {origin_code} → {end_code} supprimée.",
                      parent=self.canvas.window())

    def reset_transitions(self):
        """Supprime toutes les flèches du canvas et vide la liste des transitions."""
        arrows = [item for item in self.canvas.scene.items()
                  if isinstance(item, TransitionArrow)]
        for arrow in arrows:
            # Nettoyer les handles éventuels
            arrow._clear_handles()
            # Désenregistrer auprès des états
            if arrow in arrow.start_item.arrows:
                arrow.start_item.arrows.remove(arrow)
            if arrow in arrow.end_item.arrows:
                arrow.end_item.arrows.remove(arrow)
            self.canvas.scene.removeItem(arrow)
        self._transitions.clear()
        self._conditions.clear()
        self._set_validation_ok(False)
        self.palette.set_transitions_list([])
        self.transitionsChanged.emit()
        MsgToast.info("Réinitialisation", "Toutes les transitions ont été supprimées.",
                      parent=self.canvas.window())

    def init_base_transitions(self):
        """Charge toutes les transitions standard GEMMA sur le canvas."""
        # Récupérer les items présents sur la scène
        state_items = {item.code: item
                       for item in self.canvas.scene.items()
                       if isinstance(item, EtatGraphicsObject)}

        added = 0
        skipped = 0
        all_transitions = list(GEMMA_ALLOWED_TRANSITIONS)

        for origin_code, end_code in sorted(all_transitions):
            if origin_code not in state_items or end_code not in state_items:
                skipped += 1
                continue
            if (origin_code, end_code) in self._transitions:
                skipped += 1
                continue
            self._transitions.append((origin_code, end_code))
            self._add_arrow_to_scene(state_items[origin_code], state_items[end_code])
            added += 1

        self.palette.set_transitions_list(self._get_transitions_with_conditions())
        MsgToast.success(
            "Transitions initialisées",
            f"{added} transitions ajoutées ({skipped} ignorées).",
            parent=self.canvas.window()
        )

    def mettre_a_jour_fleches(self):
        """Charge le modèle FLECHES_MODEL, supprime toutes les flèches existantes
        puis redessine uniquement celles dont les deux états sont présents sur le canvas."""
        from PyQt6.QtCore import QPointF
        from core.view.canvas_view import TransitionArrow
        from core.model.fleches_model import FLECHES_MODEL

        data = FLECHES_MODEL

        # ── Positions des états depuis le canvas ─────────────────────────
        state_items = {item.code: item
                       for item in self.canvas.scene.items()
                       if isinstance(item, EtatGraphicsObject)}
        if not state_items:
            MsgToast.error("Erreur", "Aucun état sur le canvas.", parent=self.canvas.window())
            return

        def _bounds(code):
            """Retourne un dict L/R/T/B/CX/CY pour un état donné."""
            item = state_items[code]
            r = item.sceneBoundingRect()
            return {
                "L": r.left(), "R": r.right(),
                "T": r.top(),  "B": r.bottom(),
                "CX": r.center().x(), "CY": r.center().y(),
            }

        def _resolve(expr) -> float:
            """Résout 'A5.L', 'A5.L+26' (str) ou directement un nombre (int/float)."""
            if isinstance(expr, (int, float)):
                return float(expr)
            offset = 0.0
            for sep in ("+", "-"):
                if sep in expr[3:]:
                    idx = expr.index(sep, 3)
                    offset = float(expr[idx:])
                    expr   = expr[:idx]
                    break
            code, attr = expr.split(".")
            return _bounds(code)[attr] + offset

        # ── Suppression de toutes les flèches existantes ─────────────────
        for arrow in [it for it in self.canvas.scene.items()
                      if isinstance(it, TransitionArrow)]:
            arrow._clear_handles()
            if arrow in arrow.start_item.arrows:
                arrow.start_item.arrows.remove(arrow)
            if arrow in arrow.end_item.arrows:
                arrow.end_item.arrows.remove(arrow)
            self.canvas.scene.removeItem(arrow)
        self._transitions.clear()
        self._conditions.clear()

        # ── Ajout des flèches décrites dans fleches.json ─────────────────
        added = 0
        errors = []
        for key, entry in data.items():
            if key.startswith("_"):          # ignorer les clés de métadonnées
                continue
            orig = entry.get("de")
            dest = entry.get("vers")
            pts  = entry.get("points", [])
            if orig not in state_items or dest not in state_items:
                errors.append(f"{orig}→{dest} : état inconnu")
                continue
            try:
                waypoints = [QPointF(_resolve(p["x"]), _resolve(p["y"])) for p in pts]
            except Exception as e:
                errors.append(f"{orig}→{dest} : {e}")
                continue

            self._transitions.append((orig, dest))
            # Condition par défaut depuis le modèle
            cond = entry.get("condition", "")
            if cond:
                self._conditions[(orig, dest)] = cond
            arrow = self._add_arrow_to_scene(state_items[orig], state_items[dest])
            if cond:
                arrow.set_condition(cond)
            if waypoints:
                arrow._waypoints = waypoints
                arrow._locked = True
                from PyQt6.QtWidgets import QGraphicsItem
                arrow.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
                arrow._redraw_custom()
            added += 1

        self._set_validation_ok(False)
        self.palette.set_transitions_list(self._get_transitions_with_conditions())
        self.transitionsChanged.emit()

        msg = f"{added} flèche(s) chargée(s) depuis le modèle GEMMA."
        if errors:
            msg += "\n\nErreurs :\n" + "\n".join(errors)
            MsgToast.warning("Mise à jour", msg, parent=self.canvas.window())
        else:
            MsgToast.success("Mise à jour", msg, parent=self.canvas.window())

    def sauvegarder_fleches_json(self):
        """Sauvegarde toutes les flèches présentes sur le canvas dans fleches.json.
        Les waypoints sont enregistrés en coordonnées pixel absolues (nombres)."""
        import json as _json
        from core.view.canvas_view import TransitionArrow

        _data_dir = os.path.join(os.path.dirname(__file__), "../data")
        json_path = os.path.abspath(os.path.join(_data_dir, "fleches.json"))

        # Lire le fichier existant pour conserver la clé _notation
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                existing = _json.load(f)
        except Exception:
            existing = {}

        data = {}
        if "_notation" in existing:
            data["_notation"] = existing["_notation"]

        for item in self.canvas.scene.items():
            if not isinstance(item, TransitionArrow):
                continue
            orig = item.start_item.code
            dest = item.end_item.code
            key  = f"{orig}_{dest}"
            entry = {"de": orig, "vers": dest, "points": []}
            if item._waypoints:
                entry["points"] = [
                    {"x": round(p.x(), 1), "y": round(p.y(), 1)}
                    for p in item._waypoints
                ]
            data[key] = entry

        with open(json_path, "w", encoding="utf-8") as f:
            _json.dump(data, f, indent=2, ensure_ascii=False)

        n = sum(1 for k in data if not k.startswith("_"))
        MsgToast.success("Sauvegarde", f"{n} flèche(s) sauvegardée(s) dans fleches.json.",
                         parent=self.canvas.window())

    # =========================
    # VALIDATION
    # =========================
    def validate_transitions(self):
        """
        Vérifie :
          1. Chaque état présent sur le canvas a au moins une transition entrante.
          2. Chaque état présent sur le canvas a au moins une transition sortante.
          3. Chaque transition possède une condition non vide.
        Affiche un rapport détaillé dans une boîte de dialogue.
        """
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QDialogButtonBox

        # Collecter uniquement les états qui participent à au moins une transition
        all_state_codes = {
            item.code for item in self.canvas.scene.items()
            if isinstance(item, EtatGraphicsObject)
        }
        trans_codes = set()
        for (o, e) in self._transitions:
            trans_codes.add(o)
            trans_codes.add(e)
        # Les états sans aucune transition sont ignorés (non connectés volontairement)
        state_codes = all_state_codes & trans_codes

        errors = []
        warnings = []

        if not self._transitions:
            errors.append("❌  Aucune transition définie.")

        # 1 & 2 — Couverture des états participant au graphe
        has_in  = {c: False for c in state_codes}
        has_out = {c: False for c in state_codes}
        for (o, e) in self._transitions:
            if o in has_out:
                has_out[o] = True
            if e in has_in:
                has_in[e]  = True

        for code in sorted(state_codes):
            if not has_out[code]:
                errors.append(f"❌  {code} : aucune transition sortante")
            if not has_in[code]:
                errors.append(f"❌  {code} : aucune transition entrante")

        # 3 — Conditions manquantes
        for (o, e) in sorted(self._transitions):
            cond = self._conditions.get((o, e), "").strip()
            if not cond:
                warnings.append(f"⚠️  {o} → {e} : condition de transition manquante")

        # 4 — R3 : atteignabilité de A1 depuis tout état
        if "A1" in state_codes and self._transitions:
            # Construit un graphe orienté de la liste des transitions
            reach_to_a1 = set()
            changed = True
            while changed:
                changed = False
                for (o, e) in self._transitions:
                    if (e == "A1" or e in reach_to_a1) and o not in reach_to_a1:
                        reach_to_a1.add(o)
                        changed = True
            unreachable = [
                c for c in state_codes
                if c != "A1" and c not in reach_to_a1
            ]
            for code in sorted(unreachable):
                warnings.append(f"⚠️  {code} : aucun chemin vers A1 (risque de blocage)")

        # 5 — R4 : atteignabilité de D1 depuis états de production F1..F6
        prod_states = {c for c in state_codes if c.startswith("F") or c == "D3"}
        if "D1" in state_codes and prod_states:
            reach_to_d1 = set()
            changed = True
            while changed:
                changed = False
                for (o, e) in self._transitions:
                    if (e == "D1" or e in reach_to_d1) and o not in reach_to_d1:
                        reach_to_d1.add(o)
                        changed = True
            isolated_prod = [
                c for c in sorted(prod_states)
                if c not in reach_to_d1
            ]
            for code in isolated_prod:
                warnings.append(f"⚠️  {code} : aucun chemin vers D1 (urgence non atteignable)")

        # 6 — R5 : transitions non admissibles selon le graphe GEMMA
        from core.model.gemma_graph import ADJACENCE_ADMISSIBLE as _GEMMA_ADJ
        forbidden_set: set[tuple[str, str]] = set()
        for (o, e) in sorted(self._transitions):
            if o in _GEMMA_ADJ and e not in _GEMMA_ADJ[o]:
                forbidden_set.add((o, e))
                errors.append(f"❌  {o} → {e} : transition interdite (graphe GEMMA)")

        # — États problématiques (manque entrante OU sortante)
        problem_states = set()
        for code in state_codes:
            if not has_in.get(code, True) or not has_out.get(code, True):
                problem_states.add(code)

        # — Transitions sans condition
        no_cond = {(o, e) for (o, e) in self._transitions
                   if not self._conditions.get((o, e), "").strip()}

        # — Construire le dict de couleurs pour la liste
        # Violet  : transition interdite par le graphe GEMMA
        # Rouge   : l'une des extrémités est un état problématique
        # Orange  : condition manquante
        colors = {}
        for (o, e) in self._transitions:
            if (o, e) in forbidden_set:
                colors[(o, e)] = "#9b59b6"   # violet = transition interdite
            elif o in problem_states or e in problem_states:
                colors[(o, e)] = "#e74c3c"   # rouge
            elif (o, e) in no_cond:
                colors[(o, e)] = "#e67e22"   # orange
            # sinon : pas de couleur (laissé neutre)

        self.palette.color_transitions_list(colors)
        self._set_validation_ok(not bool(errors))

        # Construire le rapport
        lines = []
        if not errors and not warnings:
            lines.append("✅  Validation réussie : le graphe GEMMA est cohérent.")
        else:
            if errors:
                lines.append(f"=== Erreurs ({len(errors)}) ===")
                lines.extend(errors)
                lines.append("")
            if warnings:
                lines.append(f"=== Avertissements ({len(warnings)}) ===")
                lines.extend(warnings)

        # Afficher dans une QDialog
        dlg = QDialog(self.canvas.window())
        dlg.setWindowTitle("Validation du graphe GEMMA")
        dlg.resize(480, 340)
        vbox = QVBoxLayout(dlg)
        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setFontFamily("monospace")
        txt.setPlainText("\n".join(lines))
        vbox.addWidget(txt)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        bb.accepted.connect(dlg.accept)
        vbox.addWidget(bb)
        dlg.exec()

    # =========================
    # SAVE / LOAD
    # =========================
    def save_transitions(self, file_path: str):
        """Sérialise toutes les transitions (de, vers, condition, waypoints) en JSON."""
        import json
        from core.view.canvas_view import TransitionArrow

        data = []
        for (o, e) in self._transitions:
            cond = self._conditions.get((o, e), "")
            waypoints = None
            # Rechercher la flèche correspondante pour récupérer ses waypoints
            for item in self.canvas.scene.items():
                if isinstance(item, TransitionArrow) \
                   and item.start_item.code == o \
                   and item.end_item.code == e:
                    if item._waypoints is not None:
                        waypoints = [{"x": p.x(), "y": p.y()} for p in item._waypoints]
                    break
            renvoi = getattr(item, '_is_renvoi', False) if item else False
            renvoi_pos = None
            if renvoi and item and item._renvoi_items:
                renvoi_pos = [
                    {"x": r.x(), "y": r.y()} for r in item._renvoi_items
                ]
            entry = {"de": o, "vers": e, "condition": cond}
            if waypoints is not None:
                entry["waypoints"] = waypoints
            if renvoi:
                entry["renvoi"] = True
            if renvoi_pos is not None:
                entry["renvoi_pos"] = renvoi_pos
            data.append(entry)

        if not file_path.endswith(".json"):
            file_path += ".json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        MsgToast.success("Sauvegarde", f"{len(data)} transitions enregistrées.",
                         parent=self.canvas.window())

    def load_transitions(self, file_path: str):
        """Charge les transitions depuis un fichier JSON et les applique sur le canvas."""
        import json
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.load_transitions_from_data(data)

    def load_transitions_from_data(self, transitions: list):
        """Charge les transitions depuis une liste de dicts (sans FileDialog)."""
        from PyQt6.QtCore import QPointF
        from core.view.canvas_view import TransitionArrow, EtatGraphicsObject

        # Supprimer toutes les flèches existantes
        for arrow in [item for item in self.canvas.scene.items()
                      if isinstance(item, TransitionArrow)]:
            arrow._clear_handles()
            if arrow in arrow.start_item.arrows:
                arrow.start_item.arrows.remove(arrow)
            if arrow in arrow.end_item.arrows:
                arrow.end_item.arrows.remove(arrow)
            self.canvas.scene.removeItem(arrow)
        self._transitions.clear()
        self._conditions.clear()
        self._validation_ok = False  # silencieux — AppController restaurera depuis le JSON

        state_items = {item.code: item for item in self.canvas.scene.items()
                       if isinstance(item, EtatGraphicsObject)}
        loaded = 0
        skipped = 0
        for entry in transitions:
            o = entry.get("de")
            e = entry.get("vers")
            cond = entry.get("condition", "")
            waypoints_data = entry.get("waypoints")
            if not o or not e:
                skipped += 1
                continue
            if o not in state_items or e not in state_items:
                skipped += 1
                continue
            if (o, e) in self._transitions:
                skipped += 1
                continue
            # Fallback : si condition absente du JSON, prendre la valeur du modèle
            if not cond:
                from core.model.fleches_model import FLECHES_MODEL
                cond = FLECHES_MODEL.get(f"{o}_{e}", {}).get("condition", "")
            self._transitions.append((o, e))
            if cond:
                self._conditions[(o, e)] = cond
            arrow = self._add_arrow_to_scene(state_items[o], state_items[e])
            if cond:
                arrow.set_condition(cond)
            if waypoints_data:
                arrow._waypoints = [QPointF(wp["x"], wp["y"]) for wp in waypoints_data]
                arrow._redraw_custom()
            if entry.get("renvoi"):
                arrow.convert_to_renvoi()
                renvoi_pos = entry.get("renvoi_pos")
                if renvoi_pos and len(renvoi_pos) == 2 and len(arrow._renvoi_items) == 2:
                    for ri, rp in zip(arrow._renvoi_items, renvoi_pos):
                        ri.setPos(rp["x"], rp["y"])
            loaded += 1

        # ── Rafraîchissement global : recalcule tous les offsets avec le
        # bon nombre de frères (les flèches créées une à une n'avaient pas
        # encore tous leurs frères au moment de leur premier update_arrow).
        for _it in list(self.canvas.scene.items()):
            if isinstance(_it, TransitionArrow) and _it._waypoints is None:
                _it.update_arrow()

        self.palette.set_transitions_list(self._get_transitions_with_conditions())
        msg = f"{loaded} transitions chargées."
        if skipped:
            msg += f" ({skipped} ignorées — états absents ou doublons)"
        MsgToast.success("Chargement", msg, parent=self.canvas.window())

    # =========================
    # QUESTIONNAIRE GEMMA
    # =========================
    def open_questionnaire(self):
        """Ouvre le dialogue du questionnaire GEMMA."""
        from core.view.questionnaire_dialog import QuestionnaireDialog
        from core.view.canvas_view import EtatGraphicsObject
        from core.model.states_model import StatesModel

        dlg = QuestionnaireDialog(parent=self.palette.window())
        dlg.questionnaire_validated.connect(self._on_questionnaire_validated)
        dlg.exec()

    def _on_questionnaire_validated(self, state_codes: list, transitions: list):
        """
        Reçoit les codes d'états et transitions déduits du questionnaire.
        - Ajoute les états absents du canvas
        - Ajoute les transitions correspondantes
        """
        from core.view.canvas_view import EtatGraphicsObject
        from core.model.states_model import StatesModel
        from core.services.toast.toast import MsgToast

        states_model = StatesModel()

        # ── Ajout des états manquants ──────────────────────────
        drawn_codes = {item.code for item in self.canvas.scene.items()
                       if isinstance(item, EtatGraphicsObject)}
        added_states = []
        for code in state_codes:
            if code in drawn_codes:
                continue
            etat = states_model.get_by_code(code)
            if etat is None:
                continue
            item = EtatGraphicsObject(etat.code, etat.label, etat.w, etat.h)
            item.setPos(etat.x, etat.y)
            self.canvas.scene.addItem(item)
            drawn_codes.add(code)
            added_states.append(code)

        if hasattr(self.canvas, 'apply_states_interactive'):
            self.canvas.apply_states_interactive()

        # ── Flèches filtrées : uniquement entre les états sélectionnés ───────────
        # On ne dessine que les flèches du modèle dont les DEUX bouts font partie
        # des états répondus «Oui» dans le questionnaire.
        from PyQt6.QtCore import QPointF
        from PyQt6.QtWidgets import QGraphicsItem
        from core.model.fleches_model import FLECHES_MODEL

        selected_codes = set(state_codes)   # uniquement les états choisis

        state_items = {item.code: item for item in self.canvas.scene.items()
                       if isinstance(item, EtatGraphicsObject)}

        # Supprimer toutes les flèches existantes
        for arrow in [it for it in self.canvas.scene.items()
                      if isinstance(it, TransitionArrow)]:
            arrow._clear_handles()
            if arrow in arrow.start_item.arrows:
                arrow.start_item.arrows.remove(arrow)
            if arrow in arrow.end_item.arrows:
                arrow.end_item.arrows.remove(arrow)
            self.canvas.scene.removeItem(arrow)
        self._transitions.clear()
        self._conditions.clear()

        # Index des conditions fournies par le questionnaire
        conditions_questionnaire: dict[tuple, str] = {}
        for t in transitions:
            o, e, cond = t.get("de"), t.get("vers"), t.get("condition", "")
            if o and e and cond:
                conditions_questionnaire[(o, e)] = cond

        # Ajouter uniquement les flèches dont les deux états sont sélectionnés
        added = 0
        for entry in FLECHES_MODEL.values():
            orig, dest = entry["de"], entry["vers"]
            if orig not in selected_codes or dest not in selected_codes:
                continue                          # filtrage par réponses questionnaire
            if orig not in state_items or dest not in state_items:
                continue                          # état absent du canvas (ne devrait pas arriver)
            waypoints = [QPointF(float(p["x"]), float(p["y"]))
                         for p in entry.get("points", [])]
            self._transitions.append((orig, dest))
            arrow = self._add_arrow_to_scene(state_items[orig], state_items[dest])
            if waypoints:
                arrow._waypoints = waypoints
                arrow._locked = True
                arrow.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
                arrow._redraw_custom()
            # Condition : questionnaire en priorité, sinon défaut du modèle
            cond = conditions_questionnaire.get((orig, dest), "") or entry.get("condition", "")
            if cond:
                self._conditions[(orig, dest)] = cond
                arrow.set_condition(cond)
            added += 1

        self._set_validation_ok(False)
        self.palette.set_transitions_list(self._get_transitions_with_conditions())

        msg_parts = []
        if added_states:
            msg_parts.append(f"États ajoutés : {', '.join(added_states)}")
        msg_parts.append(f"{added} transition(s) selon le questionnaire")
        MsgToast.success("Questionnaire GEMMA", " — ".join(msg_parts),
                         parent=self.canvas.window())

        # Émettre le signal pour déclencher l'auto-sauvegarde du projet
        self.questionnaireApplied.emit()

