"""
Générateur de Grafcets depuis un GEMMA.

Entrées :
  - etats      : list[dict]  — [{"code", "label", ...}, ...]
  - transitions: list[dict]  — [{"de", "vers", "condition"}, ...]

Sorties (méthodes publiques) :
  - generate_gs()   → dict  — Grafcet de Sécurité
  - generate_gc()   → dict  — Grafcet de Commande
  - generate_gpn()  → dict  — Grafcet de Production Normale (ébauche)

Structure d'un Grafcet retourné :
{
  "nom": str,
  "description": str,
  "etapes": [{"num": int, "nom": str, "actions": [str], "initiale": bool}, ...],
  "transitions": [{"de": int, "vers": int, "receptivite": str}, ...],
  "avertissements": [str]
}
"""

# ─── Groupes GEMMA ────────────────────────────────────────────────────────────
_GRP_A = {"A1", "A2", "A3", "A4", "A5", "A6", "A7"}
_GRP_F = {"F1", "F2", "F3", "F4", "F5", "F6"}
_GRP_D = {"D1", "D2", "D3"}

# États qui appartiennent au GS (Surveillance) — PAS au GC
# D1/D2/A5 = chaîne de défaillance gérée en sécurité
# Référence : Moreno & Peulot, §5.56 (fig. GS) et Ch.II §4
_GS_CODES = {"D1", "D2", "A5"}

# Priorités pour les étapes du GC — excluent les états gérés par le GS
_GC_ORDER = ["A1", "A6", "A7", "F2", "F1", "F3", "F4", "F5", "F6",
             "D3", "A2", "A3", "A4"]

# Conditions par défaut calquées sur les noms GEMMA standard (IEC 60848)
# Utilisées quand la condition dans le GEMMA est vide.
_DEFAULT_COND: dict[tuple[str, str], str] = {
    # ─── GC : marches de fonctionnement F ────────────────────────────────────
    ("A1", "F1"): "dcy",
    ("A1", "F2"): "Mode_preparation",
    ("A1", "F4"): "manu",
    ("A1", "F5"): "Mode_verif_seq",
    ("A1", "F6"): "Mode_test",
    ("A2", "F1"): "dcy",
    ("A2", "F3"): "mc",
    ("A3", "A4"): "Arret_fige_obtenu",
    ("A4", "F1"): "dfig",
    ("A4", "A6"): "Init_position",
    ("A6", "A1"): "Init_OK",
    ("A7", "A4"): "Arret_obtenu",
    ("A7", "A6"): "Quitter_reglage",
    ("F1", "A2"): "acy",
    ("F1", "A3"): "fig",
    ("F2", "F1"): "Preparation_ok",
    ("F3", "A1"): "Cloture_ok",
    ("F4", "A1"): "Quitter_manu",
    ("F4", "A6"): "CI",
    ("F5", "F1"): "Fin_verif",
    ("F6", "F1"): "Fin_test",
    # ─── GS : chaîne de défaillance D1/D2/A5/A6-1 ────────────────────────────
    ("F1", "D1"): "Defaut",
    ("D1", "D2"): "EU_relachee",
    ("D2", "A5"): "Acquit_defaut",
    ("A5", "A6"): "Reset_machine",
    ("A5", "A1"): "Init_OK",
}


class GrafcetGenerator:

    def __init__(self, etats: list, transitions: list):
        self._etats_by_code = {e["code"]: e for e in etats}
        self._raw_transitions = transitions  # list[{"de", "vers", "condition"}]

    # ═══════════════════════════════════════════════════════════════════════════
    # GS — Grafcet de Sécurité
    # ═══════════════════════════════════════════════════════════════════════════

    def generate_gs(self) -> dict:
        """
        GS — Grafcet de Surveillance (Sécurité) conforme GEMMA.

        Structure canonique (Moreno & Peulot, fig. 5.56, Ch.II §4) :

          E0  (Autorisé)      kXS := 1  ← étape initiale
            ↓  condition défaut (AU, /kPO, /p5, …)
          E1  (D1 — Mise en sécurité)   kXS := 0
              F/GC, GPN > {INIT}  — P.O. hors énergie — Balise
            ↓  EU_relachee  (condition D1→D2 du GEMMA)
          E2  (D2 — Diagnostic)         kXS := 0
              Messages défauts
            ↓  Acquit_defaut  (condition D2→A5)
          E3  (A5 — Préparation remise en route)
              Remise énergie P.O. — Balise := 0
            ↓  Reset_machine  (condition A5→A6)
          E4  (A6-1 — Mise P.O. dans état initial)
              Lancement référence P.O.
            ↓  Init_OK  (condition A6→A1)
          E0  (retour autorisation)

        kXS = X0  (= 1 seulement quand E0 est actif).
        D1/D2/A5 sont dans ce GS — ils n'apparaissent PLUS dans le GC.
        """
        avertissements = []
        present = set(self._etats_by_code.keys())

        has_d1 = "D1" in present
        has_d2 = "D2" in present
        has_a5 = "A5" in present
        has_a6 = "A6" in present

        # ── Helpers : extraire une condition du GEMMA ou utiliser le défaut ─
        def _cond(src: str, dst: str) -> str:
            matches = [t for t in self._raw_transitions
                       if t["de"] == src and t["vers"] == dst and t.get("condition")]
            return matches[0]["condition"] if matches else _DEFAULT_COND.get((src, dst), "1")

        # ── Condition d'entrée dans D1 ─────────────────────────────────────
        # Chercher toute transition menant vers D1
        to_d1 = [t for t in self._raw_transitions if t["vers"] == "D1"]
        if to_d1:
            cond_defaut = to_d1[0]["condition"] or _DEFAULT_COND.get(
                (to_d1[0]["de"], "D1"), "Defaut"
            )
        else:
            cond_defaut = "Defaut"
            if has_d1:
                avertissements.append(
                    "Aucune transition vers D1 dans le GEMMA — 'Defaut' utilisé par défaut."
                )

        # ── Étapes ────────────────────────────────────────────────────────
        etapes: list[dict] = [
            {
                "num": 0,
                "nom": "GS_Autorise",
                "label": "Production autorisée",
                "actions": ["kXS := 1"],
                "initiale": True,
            }
        ]
        step_idx: dict[str, int] = {}   # étiquette interne → num d'étape

        if has_d1:
            etapes.append({
                "num": 1,
                "nom": "GS_D1",
                "label": "D1 — Mise en sécurité",
                "actions": [
                    "kXS := 0",
                    "F/GC, GPN > {INIT}",
                    "P.O. hors énergie électrique et pneumatique",
                    "Balise_lumineuse := 1",
                ],
                "initiale": False,
            })
            step_idx["D1"] = 1

        if has_d2:
            etapes.append({
                "num": 2,
                "nom": "GS_D2",
                "label": "D2 — Diagnostic / Traitement défaillance",
                "actions": [
                    "kXS := 0",
                    "Balise_lumineuse := 1",
                    "# Afficher messages défauts",
                ],
                "initiale": False,
            })
            step_idx["D2"] = 2

        if has_a5:
            etapes.append({
                "num": 3,
                "nom": "GS_A5",
                "label": "A5 — Préparation pour remise en route",
                "actions": [
                    "Remise_energie_PO",
                    "Remise_progressive_pression",
                    "Balise_lumineuse := 0",
                ],
                "initiale": False,
            })
            step_idx["A5"] = 3

        # A6-1 : copie sécurité de A6 utilisée uniquement via le chemin A5→A6
        if has_a5 and has_a6:
            etapes.append({
                "num": 4,
                "nom": "GS_A6_1",
                "label": "A6-1 — Mise P.O. dans état initial (depuis sécurité)",
                "actions": [
                    "Lancement_reference_PO",
                    "# kXS provisoirement actif pour mouvements de référence",
                ],
                "initiale": False,
            })
            step_idx["A6_1"] = 4

        # ── Transitions ───────────────────────────────────────────────────
        transitions: list[dict] = []

        if has_d1:
            # E0 → D1
            transitions.append({
                "de": 0, "vers": step_idx["D1"],
                "receptivite": cond_defaut,
                "commentaire": "Défaut détecté → D1 Mise en sécurité",
            })
            next_after_d1 = (
                step_idx["D2"]  if has_d2 else
                step_idx.get("A5", 0)
            )
            # D1 → D2 (ou A5, ou E0 si chaine incomplète)
            transitions.append({
                "de": step_idx["D1"],
                "vers": next_after_d1,
                "receptivite": _cond("D1", "D2") if has_d2 else _cond("D1", "A5") if has_a5 else _cond("D1", "A1"),
                "commentaire": "D1 → " + ("D2" if has_d2 else "A5" if has_a5 else "Autorisé"),
            })
        else:
            # Pas de D1 → GS ne produit qu'E0
            avertissements.append(
                "D1 absent — GS minimal (E0 seul). "
                "Activez la question 5 (sécurités/défauts) pour un GS complet."
            )

        if has_d2:
            next_after_d2 = step_idx.get("A5", 0)
            transitions.append({
                "de": step_idx["D2"],
                "vers": next_after_d2,
                "receptivite": _cond("D2", "A5") if has_a5 else _cond("D2", "A1"),
                "commentaire": "D2 → " + ("A5" if has_a5 else "Autorisé"),
            })

        if has_a5:
            if "A6_1" in step_idx:
                transitions.append({
                    "de": step_idx["A5"],
                    "vers": step_idx["A6_1"],
                    "receptivite": _cond("A5", "A6"),
                    "commentaire": "A5 → A6-1 Mise en référence",
                })
            else:
                transitions.append({
                    "de": step_idx["A5"],
                    "vers": 0,
                    "receptivite": _cond("A5", "A1"),
                    "commentaire": "A5 → Production autorisée",
                })

        if "A6_1" in step_idx:
            transitions.append({
                "de": step_idx["A6_1"],
                "vers": 0,
                "receptivite": _cond("A6", "A1"),
                "commentaire": "A6-1 → Production autorisée",
            })

        return {
            "nom": "GS",
            "titre": "Grafcet de Surveillance (Sécurité)",
            "description": (
                "Conforme GEMMA (Moreno & Peulot, Ch.II §4 / fig. 5.56).\n"
                "kXS = 1 uniquement quand E0 est actif (production autorisée).\n"
                "D1/D2/A5/A6-1 sont dans ce GS — ils n'apparaissent plus dans le GC.\n"
                "Émet F/GC, GPN > {INIT} en D1 (forçage vers état initial)."
            ),
            "sorties": {"kXS": 0},
            "etapes": etapes,
            "transitions": transitions,
            "avertissements": avertissements,
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # GC — Grafcet de Commande
    # ═══════════════════════════════════════════════════════════════════════════

    def generate_gc(self) -> dict:
        """
        Grafcet de Commande : modes de marche et d'arrêt (GEMMA).

        Contient uniquement les états qui NE sont PAS dans le GS :
          - Groupes A (sauf A5), F, D3, A6, A7
          - D1 / D2 / A5 sont gérés par le GS (chaîne de défaillance)

        Référence : Moreno & Peulot, Ch.II §5 (fig. 5.60).
        """
        avertissements = []
        present = set(self._etats_by_code.keys())

        # États dans le GC = présents dans le GEMMA ET non réservés au GS
        gc_codes = [c for c in _GC_ORDER if c in present and c not in _GS_CODES]
        if not gc_codes:
            avertissements.append("Aucun état présent dans le GEMMA.")

        # ── Étapes ───────────────────────────────────────────────────────────
        etapes = []
        step_map = {}
        for num, code in enumerate(gc_codes):
            e = self._etats_by_code[code]
            # F1 → appelle le Grafcet de Production Normale (G_PN)
            # Tous les autres états → G_<code> (ex. G_F2, G_A1…)
            procedure = "G_PN" if code == "F1" else f"G_{code}"
            etapes.append({
                "num": num,
                "nom": f"GC_{code}",
                "label": e["label"],
                "actions": [procedure],
                "initiale": code == "A1",
            })
            step_map[code] = num

        # ── Transitions ──────────────────────────────────────────────────────
        # Exclure les transitions dont la source ou la destination
        # appartient aux états gérés par le GS (_GS_CODES)
        gc_trans = []
        for t in self._raw_transitions:
            src, dst = t["de"], t["vers"]
            if src in _GS_CODES or dst in _GS_CODES:
                continue   # cette transition appartient au GS
            if src in step_map and dst in step_map:
                cond = t["condition"] or _DEFAULT_COND.get((src, dst), "1")
                gc_trans.append({
                    "de": step_map[src],
                    "vers": step_map[dst],
                    "receptivite": cond,
                    "commentaire": f"{src} → {dst}",
                })

        if not gc_trans:
            avertissements.append(
                "Aucune transition entre états du GC — "
                "vérifiez les transitions dans l'éditeur."
            )

        return {
            "nom": "GC",
            "titre": "Grafcet de Commande",
            "description": (
                "Grafcet de conduite : modes de marche et d'arrêt (GEMMA).\n"
                "Chaque étape active le grafcet de mode associé :\n"
                "  F1 → G_PN  |  autres → G_<code> (ex. G_F2, G_A2…)\n"
                "D1/D2/A5 sont dans le GS (pas dans ce grafcet)."
            ),
            "etapes": etapes,
            "transitions": gc_trans,
            "avertissements": avertissements,
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # GPN — Grafcet de Production Normale (ébauche)
    # ═══════════════════════════════════════════════════════════════════════════

    def generate_gpn(self) -> dict:
        """
        Grafcet de Production Normale : ébauche des cycles de production.
        Inclut uniquement F1 et les états F impliqués dans la production.
        Les actions sont vides (à remplir par le programmeur).
        """
        avertissements = [
            "GPN généré en ébauche : les actions des étapes sont à compléter manuellement.",
            "La séquence interne de production dépend du process — seuls les états "
            "F et leurs transitions sont extraits du GEMMA.",
        ]
        present = set(self._etats_by_code.keys())

        # F1 est l'étape principale ; F2/F3 sont des marches spéciales liées à F1
        gpn_codes_ordered = ["F2", "F3", "F1", "F4", "F5", "F6"]
        gpn_codes = [c for c in gpn_codes_ordered if c in present]

        if "F1" not in present:
            avertissements.append(
                "ATTENTION : F1 (Production normale) absent — GPN très incomplet."
            )

        # ── Étapes ───────────────────────────────────────────────────────────
        etapes = []
        step_map = {}

        # Étape 0 : Attente démarrage (toujours présente)
        etapes.append({
            "num": 0,
            "nom": "GPN_Attente",
            "label": "Attente départ cycle",
            "actions": ["# Pré-actions à compléter"],
            "initiale": True,
        })

        for num, code in enumerate(gpn_codes, start=1):
            e = self._etats_by_code[code]
            etapes.append({
                "num": num,
                "nom": f"GPN_{code}",
                "label": e["label"],
                "actions": [
                    f"# --- Étape {code} ---",
                    f"# Actionneurs à compléter",
                ],
                "initiale": False,
            })
            step_map[code] = num

        # ── Transitions ──────────────────────────────────────────────────────
        gpn_trans = []

        # Transition 0 → F1 (ou F2 si présent) : condition de démarrage depuis A1
        f_start = "F2" if "F2" in step_map else ("F1" if "F1" in step_map else None)
        if f_start:
            # Chercher la condition dans le GEMMA
            starts = [t for t in self._raw_transitions
                      if t["vers"] == f_start and t["de"] in _GRP_A]
            if starts:
                cond = starts[0]["condition"] or _DEFAULT_COND.get((starts[0]["de"], f_start), "Depart_cycle")
            else:
                cond = _DEFAULT_COND.get(("A1", f_start), "Depart_cycle")
            gpn_trans.append({
                "de": 0,
                "vers": step_map[f_start],
                "receptivite": cond,
                "commentaire": f"Démarrage → {f_start}",
            })

        # Transitions internes F↔F
        for t in self._raw_transitions:
            src, dst = t["de"], t["vers"]
            if src in step_map and dst in step_map:
                cond = t["condition"] or _DEFAULT_COND.get((src, dst), "1")
                gpn_trans.append({
                    "de": step_map[src],
                    "vers": step_map[dst],
                    "receptivite": cond,
                    "commentaire": f"{src} → {dst}",
                })

        # Retour au début : F1 → 0 (fin de cycle)
        # On préfère F1→A2 (arrêt en fin de cycle) comme condition de base ;
        # sinon "Fin_cycle" comme valeur par défaut GPN.
        f1_step = step_map.get("F1")
        if f1_step is not None:
            fin_conds_a2 = [t for t in self._raw_transitions
                            if t["de"] == "F1" and t["vers"] == "A2"]
            fin_conds_any = [t for t in self._raw_transitions
                             if t["de"] == "F1" and t["vers"] in _GRP_A]
            fin_conds = fin_conds_a2 or fin_conds_any
            cond_fin = (fin_conds[0]["condition"] or "Fin_cycle") if fin_conds else "Fin_cycle"
            gpn_trans.append({
                "de": f1_step,
                "vers": 0,
                "receptivite": cond_fin,
                "commentaire": "Fin de cycle → Attente",
            })

        # Fermetures : F sans sortie interne → retour à Attente (E0)
        # (ex. F3 → A1, F4 → A6 dans le GEMMA, non représentables en GPN)
        gpn_outgoing = {t["de"] for t in gpn_trans}
        for code in gpn_codes:
            src_step = step_map[code]
            if src_step not in gpn_outgoing:
                exits = [t for t in self._raw_transitions
                         if t["de"] == code and t["vers"] not in step_map]
                raw_cond = exits[0]["condition"] if exits else ""
                # Fallback 1 : condition par défaut selon la paire (Fx → Ay)
                fallback = _DEFAULT_COND.get((code, exits[0]["vers"]), "1") if exits else "1"
                cond = raw_cond or fallback
                from_lbl = f" (remappé depuis {code}→{exits[0]['vers']})"\
                    if exits else ""
                gpn_trans.append({
                    "de": src_step,
                    "vers": 0,
                    "receptivite": cond,
                    "commentaire": f"{code} → Attente{from_lbl}",
                })

        if not gpn_trans:
            avertissements.append(
                "Aucune transition de production détectée dans le GEMMA."
            )

        return {
            "nom": "GPN",
            "titre": "Grafcet de Production Normale (ébauche)",
            "description": (
                "Ébauche du cycle de production issue du GEMMA.\n"
                "Les actions des étapes sont à remplir selon le process.\n"
                "La séquence F2→F1 (préparation → production) est extraite automatiquement."
            ),
            "etapes": etapes,
            "transitions": gpn_trans,
            "avertissements": avertissements,
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # Export texte (pour affichage palette ou fichier)
    # ═══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def grafcet_to_text(g: dict) -> str:
        """Retourne une représentation textuelle lisible d'un Grafcet."""
        lines = []
        lines.append(f"{'═'*60}")
        lines.append(f"  {g['titre']}")
        lines.append(f"{'═'*60}")
        lines.append(g.get("description", ""))
        lines.append("")

        lines.append("── ÉTAPES ──────────────────────────────────────────────")
        for e in g["etapes"]:
            init_mark = " ◆ (initiale)" if e["initiale"] else ""
            lines.append(f"  [{e['num']:>2}]  {e['nom']}{init_mark}")
            lines.append(f"        {e['label']}")
            for a in e["actions"]:
                lines.append(f"        → {a}")

        lines.append("")
        lines.append("── TRANSITIONS ─────────────────────────────────────────")
        for t in g["transitions"]:
            comment = f"  # {t['commentaire']}" if t.get("commentaire") else ""
            lines.append(
                f"  [{t['de']:>2}] ──( {t['receptivite']} )──▶ [{t['vers']:>2}]{comment}"
            )

        if g.get("avertissements"):
            lines.append("")
            lines.append("── AVERTISSEMENTS ──────────────────────────────────────")
            for w in g["avertissements"]:
                lines.append(f"  ⚠  {w}")

        return "\n".join(lines)

    @staticmethod
    def grafcet_to_structured_text(g: dict) -> str:
        """
        Génère un texte structuré (pseudo-IL/ST IEC 61131-3 simplifié)
        pour faciliter l'intégration dans un automate.
        """
        lines = []
        nom = g["nom"]
        lines.append(f"(* ===== {g['titre']} ===== *)")
        lines.append(f"(* {g['description'].replace(chr(10), ' ')} *)")
        lines.append("")

        # Variables d'étapes
        lines.append("(* --- Étapes (BOOL) --- *)")
        for e in g["etapes"]:
            init = " := TRUE" if e["initiale"] else " := FALSE"
            lines.append(f"VAR  {nom}_E{e['num']:02d} : BOOL{init};  (* {e['label']} *)")
        lines.append("")

        # Actions
        lines.append("(* --- Actions --- *)")
        for e in g["etapes"]:
            lines.append(f"(* Étape {e['num']} : {e['label']} *)")
            for a in e["actions"]:
                lines.append(f"  {a}")
        lines.append("")

        # Transitions
        lines.append("(* --- Transitions --- *)")
        for t in g["transitions"]:
            comment = t.get("commentaire", "")
            lines.append(
                f"IF {nom}_E{t['de']:02d} AND ({t['receptivite']}) THEN  "
                f"(* {comment} *)"
            )
            lines.append(f"    {nom}_E{t['de']:02d} := FALSE;")
            lines.append(f"    {nom}_E{t['vers']:02d} := TRUE;")
            lines.append("END_IF;")
        lines.append("")

        return "\n".join(lines)
