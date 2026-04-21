# core/controller/app_controller.py

import json
import os
from PyQt6.QtWidgets import QFileDialog
from core.controller.mode_manager import ModeManager
from core.services.toast.toast import MsgToast

_DATA_DIR = os.path.join(os.path.dirname(__file__), "../data")
_PROJECTS_DIR = os.path.abspath(os.path.join(_DATA_DIR, "prjets"))


class AppController:

    def __init__(self, view):
        self.view = view

        # Création du ModeManager
        self.mode_manager = ModeManager(
            canvas=self.view.canvas,
            right_menu=self.view.right_menu
        )

        # Connexion des signaux de MainWindow aux méthodes d'activation
        self.view.layoutModeRequested.connect(self.activate_layout_mode)
        self.view.statesModeRequested.connect(self.activate_states_mode)
        self.view.transitionsModeRequested.connect(self.activate_transitions_mode)
        self.view.lockToggled.connect(self.view.canvas.set_canvas_locked)
        self.view.newProjectRequested.connect(self.new_project)
        self.view.appSaveRequested.connect(self.save_app)
        self.view.appLoadRequested.connect(self.load_app)
        self.view.loadProjectRequested.connect(self._load_project_from_dir)
        self._current_project_dir   = None   # dossier du projet courant (prjets/<nom>/)
        self._last_grafcets          = None   # tuple (gs, gc, gpn) de la dernière génération
        self._extra_grafcets: list   = []     # grafcets personnalisés créés par l'utilisateur
        self._generation_palette     = None   # référence à la GenerationPalette active
        self.view.simuler_btn.clicked.connect(self._on_simulate)
        self.view.generer_btn.clicked.connect(self._on_generate)
        self.view.grafcetPanelRequested.connect(self._on_grafcet_panel)
        self.view.auditRequested.connect(self._on_audit)

        # Mode par défaut
        self.mode_manager.activate("layout")

        # Chargement layout initial
        if self.mode_manager.current_controller:
            self.mode_manager.current_controller.load_layout()

        # Rechargement automatique de la dernière application
        self._auto_load_last_app()

    # -----------------------------
    # Appelé par menus / toolbar
    # -----------------------------
    def activate_layout_mode(self):
        self.mode_manager.activate("layout")
        self.view.set_mode_button_style("layout")

    def activate_states_mode(self):
        self.mode_manager.activate("states")
        self.view.set_mode_button_style("states")

    # ── Propriété dérivée ─────────────────────────────────────────────────
    @property
    def _current_gemma_path(self):
        """Chemin vers gemma.json du projet courant, ou None."""
        if self._current_project_dir:
            return os.path.join(self._current_project_dir, "gemma.json")
        return None

    def activate_transitions_mode(self):
        self.mode_manager.activate("transitions")
        self.view.set_mode_button_style("transitions")
        tc = self.mode_manager.transitions_controller
        if tc:
            tc._app_json_path = self._current_gemma_path
            # Re-peupler depuis les flèches du canvas (le TC est neuf à chaque activation)
            tc.repopulate_from_canvas()
            # Connexion du signal validationChanged
            try:
                tc.validationChanged.disconnect(self._update_validation_in_json)
            except (TypeError, RuntimeError):
                pass
            tc.validationChanged.connect(self._update_validation_in_json)
            # Auto-sauvegarde après questionnaire si un projet est ouvert
            try:
                tc.questionnaireApplied.disconnect(self.save_app)
            except (TypeError, RuntimeError):
                pass
            if self._current_project_dir:
                tc.questionnaireApplied.connect(self.save_app)
            # Auto-sauvegarde après toute modification de transitions
            try:
                tc.transitionsChanged.disconnect(self.save_app)
            except (TypeError, RuntimeError):
                pass
            if self._current_project_dir:
                tc.transitionsChanged.connect(self.save_app)

    # -----------------------------
    # Auditer
    # -----------------------------
    def _on_audit(self):
        """Déclenche la validation GEMMA depuis le bouton Auditer du menu gauche."""
        # Toujours re-activer le mode transitions pour recréer la palette
        # (l'ancienne peut avoir été détruite par un passage en mode simulation)
        self.activate_transitions_mode()
        tc = self.mode_manager.transitions_controller
        if tc:
            tc.validate_transitions()
            self.view.set_mode_button_style("auditer")

    # -----------------------------
    # Simuler / Générer
    # -----------------------------
    def _on_simulate(self):
        from core.view.canvas_view import TransitionArrow
        from core.view.palettes.simulation_palette import SimulationPalette
        from core.controller.simulation_controller import SimulationController

        # Collecte des transitions présentes sur le canvas
        transitions = []
        for item in self.view.canvas.scene.items():
            if isinstance(item, TransitionArrow):
                transitions.append({
                    "de":        item.start_item.code,
                    "vers":      item.end_item.code,
                    "condition": getattr(item, "condition", "") or "",
                })

        if not transitions:
            MsgToast.warning(
                "Simulation",
                "Aucune transition définie.\n"
                "Ajoutez des transitions avant de simuler.",
                parent=self.view,
            )
            return

        # Construire palette + contrôleur
        palette  = SimulationPalette()
        sim_ctrl = SimulationController(
            canvas=self.view.canvas,
            palette=palette,
            transitions=transitions,
        )
        self._sim_controller = sim_ctrl

        # Verrouiller le canvas (plus de déplacement / édition)
        self.view.canvas.set_canvas_locked(True)

        # Afficher la palette dans le menu droit
        self.view.right_menu.set_palette_widget(palette)

        # Mettre le bouton « Simuler » en surbrillance
        self.view.set_mode_button_style("simulation")

        # Quitter la simulation
        palette.quitRequested.connect(self._stop_simulation)

        # Démarrer automatiquement en A1
        sim_ctrl.init()

    def _stop_simulation(self):
        """Arrête la simulation, déverrouille le canvas et restaure le mode précédent."""
        if getattr(self, "_sim_controller", None):
            self._sim_controller.reset()
            self._sim_controller = None

        self.view.canvas.set_canvas_locked(False)

        # Retour au mode transitions s'il existe, sinon layout
        tc = getattr(self.mode_manager, "transitions_controller", None)
        if tc:
            self.activate_transitions_mode()
        else:
            self.activate_layout_mode()

    def _on_generate(self):
        from core.view.canvas_view import EtatGraphicsObject, TransitionArrow
        from core.utils.grafcet_generator import GrafcetGenerator

        # Vérification de la validation
        tc = getattr(self.mode_manager, 'transitions_controller', None)
        if tc is None or not tc._validation_ok:
            MsgToast.warning(
                "Validation requise",
                "Veuillez d'abord valider le graphe (aucune erreur)\navant de générer.",
                parent=self.view
            )
            return

        # Collecte des états et transitions depuis le canvas
        etats = []
        for item in self.view.canvas.scene.items():
            if isinstance(item, EtatGraphicsObject):
                etats.append({"code": item.code, "label": item.label})

        transitions = []
        for item in self.view.canvas.scene.items():
            if isinstance(item, TransitionArrow):
                transitions.append({
                    "de":        item.start_item.code,
                    "vers":      item.end_item.code,
                    "condition": getattr(item, "condition", "") or "",
                })

        if not etats:
            MsgToast.warning(
                "Génération",
                "Aucun état présent sur le canvas.",
                parent=self.view,
            )
            return

        # Génération des trois Grafcets
        gen = GrafcetGenerator(etats, transitions)
        gs  = gen.generate_gs()
        gc  = gen.generate_gc()
        gpn = gen.generate_gpn()

        # Mémorisation pour pouvoir les ré-afficher sans re-générer
        self._last_grafcets = (gs, gc, gpn)
        if self._current_project_dir:
            self._auto_save_grafcets(gs, gc, gpn)

        self._show_generation_palette(gs, gc, gpn)

    def _show_generation_palette(self, gs=None, gc=None, gpn=None, focus_last=False):
        from core.view.palettes.generation_palette import GenerationPalette
        palette = GenerationPalette(
            gs=gs, gc=gc, gpn=gpn,
            extra_grafcets=list(self._extra_grafcets),
        )
        self._generation_palette = palette
        self.view.show_fullpage(palette)
        self.view.set_mode_button_style("generer")
        palette.closeRequested.connect(self._close_generation)
        palette.grafcetAdded.connect(self._extra_grafcets.append)
        palette.generateRequested.connect(self._on_generate_and_refresh)
        if focus_last:
            palette.focus_last()

    def _close_generation(self):
        """Ferme la vue pleine-page de génération et retourne au canvas."""
        self._generation_palette = None
        self.view.show_canvas()
        tc = getattr(self.mode_manager, "transitions_controller", None)
        if tc:
            self.activate_transitions_mode()
        else:
            self.activate_layout_mode()

    def _on_generate_and_refresh(self):
        """Génère les grafcets et met à jour la palette ouverte."""
        from core.view.canvas_view import EtatGraphicsObject, TransitionArrow
        from core.utils.grafcet_generator import GrafcetGenerator

        tc = getattr(self.mode_manager, 'transitions_controller', None)
        if tc is None or not tc._validation_ok:
            from core.services.toast.toast import MsgToast
            MsgToast.warning(
                "Validation requise",
                "Veuillez d'abord valider le graphe (aucune erreur)\navant de générer.",
                parent=self.view
            )
            return

        etats = []
        for item in self.view.canvas.scene.items():
            if isinstance(item, EtatGraphicsObject):
                etats.append({"code": item.code, "label": item.label})
        transitions = []
        for item in self.view.canvas.scene.items():
            if isinstance(item, TransitionArrow):
                transitions.append({
                    "de": item.start_item.code,
                    "vers": item.end_item.code,
                    "condition": getattr(item, "condition", "") or "",
                })
        if not etats:
            from core.services.toast.toast import MsgToast
            MsgToast.warning("Génération", "Aucun état présent sur le canvas.", parent=self.view)
            return

        gen = GrafcetGenerator(etats, transitions)
        gs, gc, gpn = gen.generate_gs(), gen.generate_gc(), gen.generate_gpn()
        self._last_grafcets = (gs, gc, gpn)
        if self._current_project_dir:
            self._auto_save_grafcets(gs, gc, gpn)
        # Remplacer la palette en cours
        self._show_generation_palette(gs, gc, gpn)
        tc = getattr(self.mode_manager, "transitions_controller", None)
        if tc:
            self.activate_transitions_mode()
        else:
            self.activate_layout_mode()

    # -----------------------------
    # Éditeur Grafcet
    # -----------------------------
    def _on_grafcet_editor(self):
        from core.view.grafcet.grafcet_editor import GrafcetEditor
        editor = GrafcetEditor()
        if self._current_project_dir:
            editor.set_project_dir(self._current_project_dir)
        self.view.show_fullpage(editor)
        self.view.set_mode_button_style("grafcet")
        editor.closeRequested.connect(self._close_grafcet_editor)
        editor.addToProjectRequested.connect(self._add_grafcet_to_project)

    def _close_grafcet_editor(self):
        self.view.show_canvas()
        tc = getattr(self.mode_manager, "transitions_controller", None)
        if tc:
            self.activate_transitions_mode()
        else:
            self.activate_layout_mode()

    def _on_grafcet_panel(self):
        """Ouvre la GenerationPalette avec tous les grafcets du projet courant."""
        gs, gc, gpn = None, None, None
        if self._last_grafcets is not None:
            gs, gc, gpn = self._last_grafcets
        elif self._current_project_dir:
            # Charger depuis le disque si jamais générés en mémoire
            gdir = os.path.join(self._current_project_dir, "grafcets")
            gs  = self._load_grafcet_json(gdir, "GS")
            gc  = self._load_grafcet_json(gdir, "GC")
            gpn = self._load_grafcet_json(gdir, "GPN")
            if gs or gc or gpn:
                self._last_grafcets = (gs, gc, gpn)
        # Charger les extras depuis le disque si pas encore en mémoire
        if not self._extra_grafcets and self._current_project_dir:
            self._extra_grafcets = self._load_extra_grafcets()
        self._show_generation_palette(gs, gc, gpn)
        self.view.set_mode_button_style("grafcet")

    def _load_grafcet_json(self, grafcets_dir: str, nom: str):
        """Charge <grafcets_dir>/<nom>.json si le fichier existe."""
        path = os.path.join(grafcets_dir, f"{nom}.json")
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def _load_extra_grafcets(self) -> list:
        """Charge tous les grafcets non-GS/GC/GPN depuis <projet>/grafcets/."""
        grafcets_dir = os.path.join(self._current_project_dir, "grafcets")
        if not os.path.isdir(grafcets_dir):
            return []
        extras = []
        base_noms = {"GS", "GC", "GPN"}
        for fname in sorted(os.listdir(grafcets_dir)):
            if not fname.endswith(".json") or fname[:-5].upper() in base_noms:
                continue
            try:
                with open(os.path.join(grafcets_dir, fname), "r", encoding="utf-8") as f:
                    extras.append(json.load(f))
            except Exception:
                pass
        return extras

    def _auto_save_grafcets(self, gs: dict, gc: dict, gpn: dict):
        """Sauvegarde automatique de GS/GC/GPN en JSON dans <projet>/grafcets/."""
        grafcets_dir = os.path.join(self._current_project_dir, "grafcets")
        os.makedirs(grafcets_dir, exist_ok=True)
        for g, nom in [(gs, "GS"), (gc, "GC"), (gpn, "GPN")]:
            if g:
                try:
                    with open(os.path.join(grafcets_dir, f"{nom}.json"), "w", encoding="utf-8") as f:
                        json.dump(g, f, indent=2, ensure_ascii=False)
                except Exception:
                    pass

    def _on_show_all_grafcets(self):
        """Ré-affiche la GenerationPalette avec les derniers grafcets générés + personnalisés."""
        if self._last_grafcets is not None:
            gs, gc, gpn = self._last_grafcets
            self._show_generation_palette(gs, gc, gpn)
        else:
            self._show_generation_palette()   # uniquement les extras

    def _create_new_grafcet_inline(self):
        """Dialogue de saisie du nom, puis crée un onglet vide dans la GenerationPalette."""
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(
            self.view, "Nouveau Grafcet", "Nom du grafcet :"
        )
        if not ok or not name.strip():
            return
        name = name.strip()
        g = {"nom": name, "titre": name, "description": "",
             "etapes": [], "transitions": [], "avertissements": []}
        # Si la palette est déjà ouverte, ajouter l'onglet directement
        if self._generation_palette is not None:
            self._extra_grafcets.append(g)
            self._generation_palette.add_grafcet(g)
            return
        # Sinon, stocker et ouvrir la palette
        self._extra_grafcets.append(g)
        if self._last_grafcets is not None:
            gs, gc, gpn = self._last_grafcets
            self._show_generation_palette(gs, gc, gpn, focus_last=True)
        else:
            self._show_generation_palette(focus_last=True)

    def _add_grafcet_to_project(self, grafcet_data: dict):
        """Sauvegarde le Grafcet dans <projet>/grafcets/."""
        if not self._current_project_dir:
            MsgToast.warning(
                "Pas de projet ouvert",
                "Créez ou ouvrez un projet avant d'ajouter un Grafcet.",
                parent=self.view,
            )
            return
        nom = grafcet_data.get("nom", "grafcet").replace(" ", "_")
        grafcets_dir = os.path.join(self._current_project_dir, "grafcets")
        os.makedirs(grafcets_dir, exist_ok=True)
        path = os.path.join(grafcets_dir, f"{nom}.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(grafcet_data, f, indent=2, ensure_ascii=False)
            MsgToast.info(
                "Grafcet ajouté",
                f"Grafcet '{nom}' sauvegardé :\n{path}",
                parent=self.view,
            )
        except Exception as exc:
            MsgToast.warning(
                "Erreur",
                f"Impossible de sauvegarder le Grafcet :\n{exc}",
                parent=self.view,
            )

    def _update_validation_in_json(self, ok: bool):
        """Met à jour le champ validation_ok dans gemma.json du projet courant."""
        path = self._current_gemma_path
        if not path or not os.path.isfile(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["validation_ok"] = ok
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # -----------------------------
    # Création d'un nouveau projet
    # -----------------------------
    def new_project(self):
        """Ouvre le dialogue de création de projet, crée le dossier et vide le canvas."""
        from PyQt6.QtWidgets import QDialog
        from core.view.new_project_dialog import NewProjectDialog

        dialog = NewProjectDialog(parent=self.view)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        name = dialog.project_name()
        description = dialog.project_description()
        safe_name = name.replace(" ", "_").replace("/", "_")

        os.makedirs(_PROJECTS_DIR, exist_ok=True)
        project_dir = os.path.join(_PROJECTS_DIR, safe_name)
        if os.path.exists(project_dir):
            MsgToast.warning(
                "Projet existant",
                f"Un projet '{safe_name}' existe déjà dans prjets/.",
                parent=self.view,
            )
            return

        os.makedirs(os.path.join(project_dir, "grafcets"), exist_ok=True)
        self._current_project_dir = project_dir

        # ── 1. Charger les états GEMMA par défaut ────────────────────────
        from core.model.states_model import STATE_BLOCKS
        self.mode_manager.activate("states")
        self.view.set_mode_button_style("states")
        sc = self.mode_manager.states_controller
        if sc:
            sc.load_states_from_data(STATE_BLOCKS)

        # ── 2. Écrire gemma.json initial avec les états par défaut ───────
        data = {
            "nom": name,
            "description": description,
            "etats": STATE_BLOCKS,
            "transitions": [],
            "validation_ok": False,
        }
        with open(self._current_gemma_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # ── 3. Basculer en mode Transitions + charger le modèle fleches.json ───
        self.activate_transitions_mode()
        tc = self.mode_manager.transitions_controller
        if tc:
            tc.mettre_a_jour_fleches()
            # Mise à jour silencieuse de gemma.json avec les transitions + waypoints
            from core.view.canvas_view import TransitionArrow
            transitions_data = []
            for item in self.view.canvas.scene.items():
                if isinstance(item, TransitionArrow):
                    entry = {
                        "de": item.start_item.code,
                        "vers": item.end_item.code,
                        "condition": getattr(item, "condition", "") or "",
                    }
                    if item._waypoints:
                        entry["waypoints"] = [{"x": p.x(), "y": p.y()} for p in item._waypoints]
                    transitions_data.append(entry)
            data["transitions"] = transitions_data
            with open(self._current_gemma_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        self._save_last_project(project_dir)
        self.view.set_project(name)
        self.view.navigate_to("gemma")
        MsgToast.success(
            "Projet créé",
            f"Projet '{name}' créé depuis le modèle fleches.json.\n{project_dir}",
            parent=self.view,
        )

    # -----------------------------
    # Sauvegarde / Chargement d'une application complète
    # -----------------------------
    def save_app(self):
        """Sauvegarde états + transitions dans <projet>/gemma.json."""
        from core.view.canvas_view import EtatGraphicsObject, TransitionArrow

        if not self._current_project_dir:
            MsgToast.warning(
                "Pas de projet ouvert",
                "Créez d'abord un nouveau projet (bouton Nouveau).",
                parent=self.view,
            )
            return

        file_path = self._current_gemma_path

        etats = []
        for item in self.view.canvas.scene.items():
            if isinstance(item, EtatGraphicsObject):
                pos = item.pos()
                rect = item.boundingRect()
                etats.append({
                    "code": item.code,
                    "label": item.label,
                    "x": int(pos.x()),
                    "y": int(pos.y()),
                    "w": int(rect.width()),
                    "h": int(rect.height()),
                })

        transitions = []
        for item in self.view.canvas.scene.items():
            if isinstance(item, TransitionArrow):
                cond = getattr(item, "condition", "") or ""
                entry = {
                    "de": item.start_item.code,
                    "vers": item.end_item.code,
                    "condition": cond,
                }
                if item._waypoints is not None:
                    entry["waypoints"] = [{"x": p.x(), "y": p.y()} for p in item._waypoints]
                transitions.append(entry)

        tc = getattr(self.mode_manager, 'transitions_controller', None)
        # Conserver nom/description déjà présents dans le fichier
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = {}

        data = {
            "nom": existing.get("nom", os.path.basename(self._current_project_dir)),
            "description": existing.get("description", ""),
            "etats": etats,
            "transitions": transitions,
            "validation_ok": tc._validation_ok if tc else False,
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        tc2 = getattr(self.mode_manager, 'transitions_controller', None)
        if tc2:
            tc2._app_json_path = file_path
        self._save_last_project(self._current_project_dir)
        self.view.set_project(data['nom'])
        MsgToast.success(
            "Sauvegarde",
            f"{len(etats)} états, {len(transitions)} transitions enregistrés.",
            parent=self.view,
        )

    def load_app(self, file_path: str = None):
        """Charge un projet depuis <projet>/gemma.json."""
        if file_path is None:
            os.makedirs(_PROJECTS_DIR, exist_ok=True)
            file_path, _ = QFileDialog.getOpenFileName(
                self.view, "Ouvrir un projet", _PROJECTS_DIR,
                "GEMMA (gemma.json);;JSON (*.json)"
            )
            if not file_path:
                return

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Déduire le dossier projet depuis le chemin du fichier
        self._current_project_dir = os.path.dirname(os.path.abspath(file_path))

        etats = data.get("etats", [])
        transitions = data.get("transitions", [])

        # Si le projet ne contient aucun état, utiliser les états GEMMA par défaut
        if not etats:
            from core.model.states_model import STATE_BLOCKS
            etats = STATE_BLOCKS

        # 1. Mode États → StatesController → charger les blocs
        self.mode_manager.activate("states")
        self.view.set_mode_button_style("states")
        sc = self.mode_manager.states_controller
        if sc:
            sc.load_states_from_data(etats)

        # 2. Mode Transitions → TransitionsController → charger les flèches
        self.mode_manager.activate("transitions")
        self.view.set_mode_button_style("transitions")
        tc = self.mode_manager.transitions_controller
        if tc:
            # Connecter le signal avant de charger (pour que la restauration soit silencieuse)
            try:
                tc.validationChanged.disconnect(self._update_validation_in_json)
            except (TypeError, RuntimeError):
                pass
            tc.validationChanged.connect(self._update_validation_in_json)
            tc.load_transitions_from_data(transitions)
            # Restaurer le flag de validation depuis le JSON (émet le signal → met à jour le fichier)
            tc._app_json_path = self._current_gemma_path
            tc._set_validation_ok(data.get("validation_ok", False))

        self._save_last_project(self._current_project_dir)
        project_name = data.get("nom") or os.path.basename(self._current_project_dir)
        self.view.set_project(project_name)
        self.view.project_page.refresh()
        self.view.navigate_to("gemma")

    # -----------------------------
    # Persistance du dernier projet ouvert
    # -----------------------------
    def _settings_path(self) -> str:
        return os.path.abspath(os.path.join(_DATA_DIR, "settings.json"))

    def _save_last_project(self, project_dir: str):
        p = self._settings_path()
        try:
            with open(p, "r", encoding="utf-8") as f:
                settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            settings = {}
        settings["last_project"] = project_dir
        with open(p, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)

    def _auto_load_last_app(self):
        p = self._settings_path()
        try:
            with open(p, "r", encoding="utf-8") as f:
                settings = json.load(f)

            # Nouveau format : last_project = dossier projet
            last_project = settings.get("last_project", "")
            if last_project and os.path.isdir(last_project):
                gemma = os.path.join(last_project, "gemma.json")
                if os.path.isfile(gemma):
                    self.load_app(gemma)
                    return

            # Rétrocompatibilité : last_app = ancien chemin .json direct
            last = settings.get("last_app", "")
            if last and os.path.isfile(last):
                self.load_app(last)
                return
        except Exception as e:
            print(f"[auto_load] échec : {e}")

        # Aucun projet trouvé → charger les états GEMMA par défaut et passer en mode Transitions
        self._load_default_states_and_go_transitions()

    def _load_project_from_dir(self, project_dir: str):
        """Charge un projet depuis son dossier (appelé par ProjectPage)."""
        if not project_dir or not os.path.isdir(project_dir):
            return
        gemma = os.path.join(project_dir, "gemma.json")
        if os.path.isfile(gemma):
            self.load_app(gemma)
        else:
            MsgToast.warning(
                "Projet invalide",
                f"Aucun fichier gemma.json dans :\n{project_dir}",
                parent=self.view,
            )

    def _load_default_states_and_go_transitions(self):
        """Charge les 16 états GEMMA par défaut + les transitions du modèle fleches.json."""
        from core.model.states_model import STATE_BLOCKS
        self.mode_manager.activate("states")
        self.view.set_mode_button_style("states")
        sc = self.mode_manager.states_controller
        if sc:
            sc.load_states_from_data(STATE_BLOCKS)
        self.activate_transitions_mode()
        tc = self.mode_manager.transitions_controller
        if tc:
            tc.mettre_a_jour_fleches()