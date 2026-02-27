# Analyse du flux de données et du comportement

## 1. Flux de démarrage
- `main.py` crée un `Container`, qui instancie `MainWindow` et `AppController`.
- `MainWindow` crée l'interface graphique (canvas, menus, boutons, signaux), mais ne doit pas créer directement de `LayoutController` ou de `LayoutPalette`.
- C'est le `ModeManager` (via `AppController`) qui gère la création et l'injection des contrôleurs et palettes selon le mode actif.
- Lors de l'activation du mode "layout", le `ModeManager` crée un `LayoutController` et une `LayoutPalette`, puis les connecte au canvas et à l'UI.

## 2. Chargement des palettes
- Au démarrage, deux instances de `LayoutPalette` et de `LayoutController` sont créées :
  - Une dans `MainWindow` (directement).
  - Une dans `ModeManager.activate("layout")` (via `AppController`).
- La palette affichée dans le menu de droite est celle du `ModeManager`, car il la remplace via `RightMenu.set_palette_widget()`.

## 3. Clic sur "Layout"
- Le bouton "Layout" de `MainWindow` émet le signal `layoutModeRequested`.
- Mais il n’y a pas de connexion explicite dans `MainWindow` pour relier ce signal à `AppController.activate_layout_mode()` ou à une méthode du `ModeManager`.
- Si tu cliques sur "Layout", il se peut que rien ne soit connecté, ou que la méthode appelée tente de ré-instancier des objets déjà détruits ou non valides, d’où le plantage.

## 4. Pourquoi le plantage ?
- **Double instanciation** : Deux palettes/controllers sont créés, mais un seul est géré par le `ModeManager` (celui affiché).
- **Connexion manquante** : Le signal du bouton "Layout" n’est pas relié à la logique du `ModeManager` (via `AppController`).
- **Widget orphelin** : Si tu réactives le mode "layout", l’ancienne palette peut être détruite, mais des références (ou signaux) persistent, causant un crash lors d’un accès.

---

## Résumé du flux de données

```mermaid
flowchart TD
    main.py --> Container
    Container --> MainWindow
    Container --> AppController
    MainWindow --> LayoutPalette1
    MainWindow --> LayoutController1
    AppController --> ModeManager
    ModeManager --> LayoutPalette2
    ModeManager --> LayoutController2
    ModeManager -->|set_palette_widget| RightMenu
    MainWindow -->|layout_btn.clicked| (connexion manquante)
```

---

## Conseils pour corriger
- **Supprimer la création directe de `LayoutPalette` et `LayoutController` dans `MainWindow`** : laisse le `ModeManager` gérer ces objets.
- **Connecter le signal `layoutModeRequested` du bouton à `AppController.activate_layout_mode()`**.
- **Vérifier que les widgets ne sont pas utilisés après suppression**.

---

*Document généré automatiquement par GitHub Copilot (GPT-4.1)*
