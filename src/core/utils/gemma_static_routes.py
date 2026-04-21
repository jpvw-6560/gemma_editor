"""
Routes statiques du diagramme GEMMA.

Chaque transition autorisée associe une liste de points (x, y) définissant
le chemin orthogonal de la flèche.  Ces waypoints sont extraits pixel par pixel
du fichier de référence :
    /doc/le_gemma_plus_fleches.gif  (803 × 595 px, niveaux de gris)
Facteurs d'échelle GIF→canvas : sx=1620/803≈2.017, sy=1020/595≈1.714

Colonnes V identifiées (pixels pointillés dans le GIF) :
    gif x= 86 → canvas x= 173  (bord gauche ext A/D)
    gif x=154 → canvas x= 311  (colonne centre A7/D2)
    gif x=264 → canvas x= 533  (corridor A1↔A4, A7→A6)
    gif x=359 → canvas x= 724  (colonne A3/D3)
    gif x=387 → canvas x= 781  (bord droit zone A)
    gif x=407 → canvas x= 821  (séparateur A/F)
    gif x=537 → canvas x=1083  (colonne F2)
    gif x=648 → canvas x=1307  (bord droit F1 / couloir F→F456)
    gif x=675 → canvas x=1362  (couloir ext droite F)
    gif x=744 → canvas x=1501  (colonne F4/F5/F6)

Lignes H identifiées (pixels pointillés dans le GIF) :
    gif y= 48 → canvas y=  82  (corridor supérieur global)
    gif y= 78 → canvas y= 134  (entre F4.T=84 et A1.T=110)
    gif y= 87 → canvas y= 149  (niveau A1/A6 centre)
    gif y=109 → canvas y= 187  (dessous A1.B=185, corridor H)
    gif y=182 → canvas y= 312  (niveau A4/A7 centre)
    gif y=361 → canvas y= 619  (niveau F1 centre)
    gif y=473 → canvas y= 811  (corridor D, entre A5.B=638 et D2.T=684)
    gif y=516 → canvas y= 885  (niveau D1 centre)

Positions des états (x, y, w, h) → bords = L/R/T/B, centre = CX/CY :
    A1: x=510 y=110 w=266 h=75   L=510  R=776  T=110  B=185  CX=643  CY=147
    A2: x=506 y=425 w=109 h=213  L=506  R=615  T=425  B=638  CX=560  CY=531
    A3: x=673 y=425 w=107 h=161  L=673  R=780  T=425  B=586  CX=726  CY=505
    A4: x=589 y=264 w=192 h=96   L=589  R=781  T=264  B=360  CX=685  CY=312
    A5: x=147 y=425 w=270 h=213  L=147  R=417  T=425  B=638  CX=282  CY=531
    A6: x=147 y=106 w=270 h=84   L=147  R=417  T=106  B=190  CX=282  CY=148
    A7: x=192 y=264 w=226 h=96   L=192  R=418  T=264  B=360  CX=305  CY=312
    D1: x=147 y=837 w=633 h=84   L=147  R=780  T=837  B=921  CX=463  CY=879
    D2: x=192 y=684 w=226 h=87   L=192  R=418  T=684  B=771  CX=305  CY=727
    D3: x=506 y=684 w=274 h=87   L=506  R=780  T=684  B=771  CX=643  CY=727
    F1: x=946 y=466 w=359 h=305  L=946  R=1305 T=466  B=771  CX=1125 CY=618
    F2: x=1031 y=266 w=109 h=153 L=1031 R=1140 T=266  B=419  CX=1085 CY=342
    F3: x=1196 y=266 w=109 h=153 L=1196 R=1305 T=266  B=419  CX=1250 CY=342
    F4: x=1428 y=84  w=147 h=144 L=1428 R=1575 T=84   B=228  CX=1501 CY=156
    F5: x=1428 y=293 w=147 h=386 L=1428 R=1575 T=293  B=679  CX=1501 CY=486
    F6: x=1428 y=729 w=147 h=192 L=1428 R=1575 T=729  B=921  CX=1501 CY=825

Corridors utilisés :
    y_top   = 62   (au-dessus de tout : A6.T=106, F4.T=84)
    y_mid_A = 225  (entre A6.B=190 et A7.T=264)
    y_gap_A = 393  (entre A7.B=360 et A2.T=425)
    y_gap_D = 660  (entre A5.B=638 et D2.T=684)
    y_mid_D = 810  (entre D2.B=771 et D1.T=837)
    x_left  = 108  (à gauche de A5.L=147, D1.L=147)
    x_mid   = 860  (entre A.R≈830 et F1.L=946)
    x_f_sep = 1381 (entre F1.R=1305 et F4.L=1428)
    A2: L=486  R=611  T=427  B=555  CX=549  CY=491
    A3: L=644  R=769  T=427  B=522  CX=707  CY=475
    A4: L=566  R=768  T=310  B=380  CX=667  CY=345
    A5: L=157  R=418  T=427  B=555  CX=289  CY=491
    A6: L=161  R=422  T=192  B=277  CX=292  CY=234
    A7: L=219  R=421  T=310  B=380  CX=320  CY=345
    D1: L=157  R=768  T=829  B=904  CX=463  CY=867
    D2: L=209  R=418  T=635  B=763  CX=314  CY=699
    D3: L=486  R=768  T=635  B=763  CX=627  CY=699
    F1: L=916  R=1280 T=475  B=730  CX=1098 CY=603
    F2: L=1002 R=1119 T=305  B=428  CX=1061 CY=367
    F3: L=1153 R=1270 T=305  B=428  CX=1212 CY=367
    F4: L=1374 R=1531 T=167  B=304  CX=1453 CY=236
    F5: L=1374 R=1531 T=352  B=640  CX=1453 CY=496
    F6: L=1374 R=1531 T=687  B=904  CX=1453 CY=796

Corridors de routage :
    NORD (y=140)     : au-dessus de tous les états supérieurs
    MID (y=403)      : entre A4 bas (380) et A2/A3 haut (427)
    GAUCHE (x=130)   : à gauche de tous les états
"""

# Coordonnées canvas extraites pixel par pixel du GIF de référence (803×595).
# Facteurs : sx=1620/803≈2.017, sy=1020/595≈1.714
#
# Corridors pixel-exact du GIF (canvas coords) :
#   x=173  gif86   bord gauche ext zone A/D
#   x=311  gif154  colonne centre A7/D2
#   x=533  gif264  corridor vertical A1↔A4/A7→A6
#   x=724  gif359  colonne A3/D3
#   x=781  gif387  bord droit zone A (= A1.R=776 arrondi)
#   x=821  gif407  séparateur A/F (entre A.R et F1.L=946)
#   x=1083 gif537  colonne F2 (= F2.CX)
#   x=1307 gif648  bord droit F1 / couloir F→F456
#   x=1362 gif675  couloir ext droite F1
#   x=1501 gif744  colonne F4/F5/F6 (= F4.CX)
#
#   y=82   gif48   corridor supérieur global (au-dessus A1.T=110)
#   y=134  gif78   entre F4.T=84 et A1.T=110
#   y=149  gif87   niveau centre A1/A6 (A1.CY=147)
#   y=187  gif109  juste sous A1.B=185
#   y=312  gif182  niveau centre A4/A7 (A4.CY=312)
#   y=619  gif361  niveau centre F1 (F1.CY=618)
#   y=811  gif473  corridor D (entre A5.B=638 et D2.T=684)
#   y=885  gif516  haut D1 (D1.T=837, D1.CY=879)
#
# Tuple (src, dst) → liste de (x, y) orthogonaux, du bord source au bord dest.

STATIC_ROUTES: dict[tuple[str, str], list[tuple[int, int]]] = {

    # ── Validées contre le GIF de référence le_gemma_plus_fleches.gif ────────

    # A5 → A6 : gauche A5(147,531) → col x=173 → haut jusqu'à A6.B=190
    ("A5", "A6"):  [(147, 531), (173, 531), (173, 190)],

    # A6 → A1 : droite A6(417,147) → gauche A1.L=510
    ("A6", "A1"):  [(417, 147), (510, 147)],

    # A2 → A1 : haut A2(559,425) → col x=559 → bas A1.B=185
    ("A2", "A1"):  [(559, 425), (559, 185)],

    # D3 → A2 : haut D3(559,684) → col x=559 → bas A2.B=638
    ("D3", "A2"):  [(559, 684), (559, 638)],

    # D1 → D2 : haut D1(305,837) → D2.B=771
    ("D1", "D2"):  [(305, 837), (305, 771)],

    # F6 → D1 : bas F6(1501,921) → y=885 → col x=780 → droite D1.R=780
    ("F6", "D1"):  [(1501, 921), (1501, 885), (780, 885)],

    # ── À valider ─────────────────────────────────────────────────────────────
}
