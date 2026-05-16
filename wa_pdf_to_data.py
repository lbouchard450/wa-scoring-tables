#!/usr/bin/env python3
"""
wa_pdf_to_data.py
=================

Extrait les World Athletics Scoring Tables of Athletics depuis le PDF officiel
et génère :
- wa_scoring_tables_2025.csv      : table longue, format universel
- wa_scoring_tables_2025.json     : structure hiérarchique avec métadonnées
- wa_scoring_tables_2025.min.json : version minifiée pour usage programmatique

Usage :
    python3 wa_pdf_to_data.py World_Athletics_Scoring_Tables_of_Athletics.pdf

Source PDF officielle :
    https://worldathletics.org/about-iaaf/documents/technical-information

Auteur : Comité des Maîtres (Luc) + Claude
Date : mai 2026
Licence : MIT
"""

import sys
import re
import subprocess
import json
import csv
from collections import OrderedDict, defaultdict
from datetime import date

# ============================================================
# CONFIGURATION
# ============================================================

# Structure de la table des matières du PDF 2025
# (titre_section, page_garde, page_début_données, page_fin_données, sexe, type_section)
SECTIONS = [
    # ── HOMMES ──
    ("Men's Sprints – Part I",                 8,   9,   37, "M", "sprints_1"),
    ("Men's Sprints – Part II",               38,  39,  67, "M", "sprints_2"),
    ("Men's Hurdles",                         68,  69,  97, "M", "hurdles"),
    ("Men's Relays",                          98,  99, 127, "M", "relays"),
    ("Men's Middle Distances – Part I",      128, 129, 157, "M", "middle_1"),
    ("Men's Middle Distances – Part II",     158, 159, 187, "M", "middle_2"),
    ("Men's Long Distances",                 188, 189, 217, "M", "long"),
    ("Men's Road Running – Part I",          218, 219, 247, "M", "road_1"),
    ("Men's Road Running – Part II",         248, 249, 277, "M", "road_2"),
    ("Men's Race Walking on Road – Part I",  278, 279, 307, "M", "rw_road_1"),
    ("Men's Race Walking on Road – Part II", 308, 309, 336, "M", "rw_road_2"),
    ("Men's Race Walking on Track – Part I", 337, 338, 366, "M", "rw_track_1"),
    ("Men's Race Walking on Track – Part II",367, 368, 396, "M", "rw_track_2"),
    ("Men's Jumps, Throws and Combined Events", 397, 398, 426, "M", "field"),
    # ── FEMMES ──
    ("Women's Sprints – Part I",             427, 428, 456, "W", "sprints_1"),
    ("Women's Sprints – Part II",            457, 458, 486, "W", "sprints_2"),
    ("Women's Hurdles",                      487, 488, 516, "W", "hurdles"),
    ("Women's Relays",                       517, 518, 546, "W", "relays"),
    ("Women's Middle Distances – Part I",    547, 548, 576, "W", "middle_1"),
    ("Women's Middle Distances – Part II",   577, 578, 606, "W", "middle_2"),
    ("Women's Long Distances",               607, 608, 636, "W", "long"),
    ("Women's Road Running – Part I",        637, 638, 666, "W", "road_1"),
    ("Women's Road Running– Part II",        667, 668, 696, "W", "road_2"),
    ("Women's Race Walking on Road – Part I",697, 698, 726, "W", "rw_road_1"),
    ("Women's Race Walking on Road – Part II", 727, 728, 756, "W", "rw_road_2"),
    ("Women's Race Walking on Track – Part I", 757, 758, 786, "W", "rw_track_1"),
    ("Women's Race Walking on Track – Part II",787, 788, 816, "W", "rw_track_2"),
    ("Women's Jumps, Throws and Combined Events", 817, 818, 845, "W", "field"),
]

# Mapping section_type → groupe canonique
SECTION_GROUP = {
    "sprints_1": "Sprints", "sprints_2": "Sprints",
    "hurdles":   "Hurdles",
    "relays":    "Relays",
    "middle_1":  "Middle Distances", "middle_2": "Middle Distances",
    "long":      "Long Distances",
    "road_1":    "Road Running", "road_2": "Road Running",
    "rw_road_1": "Race Walking on Road", "rw_road_2": "Race Walking on Road",
    "rw_track_1":"Race Walking on Track", "rw_track_2":"Race Walking on Track",
    "field":     None,  # field: pages mixtes Jump/Throws/Combined Events
}

# Catégorisation type/unit/direction par code
def categorize(group, code):
    if group == "Jump":
        return ("field", "meters", "max")
    if group == "Throws":
        return ("field", "meters", "max")
    if group == "Combined Events":
        return ("combined", "points", "max")
    if group == "Hurdles":
        return ("hurdles", "seconds", "min")
    if group in ("Sprints", "Middle Distances", "Long Distances"):
        return ("course", "seconds", "min")
    if group == "Road Running":
        return ("road", "seconds", "min")
    if group == "Race Walking on Track":
        return ("walk_track", "seconds", "min")
    if group == "Race Walking on Road":
        return ("walk_road", "seconds", "min")
    if group == "Relays":
        return ("relay", "seconds", "min")
    return ("?", "?", "?")

# Détermine le groupe (Jump/Throws/Combined) d'un code dans la section "field"
def field_group_of(code):
    if code in ("HJ", "PV", "LJ", "TJ"):
        return "Jump"
    if code in ("SP", "DT", "HT", "JT"):
        return "Throws"
    if code in ("Hept. sh", "Hept.", "Dec.", "Pent. sh", "Pent."):
        return "Combined Events"
    return "?"

# Labels FR (pour le champ 'label' du JSON)
LABELS_FR = {
    "50m": "50 m", "55m": "55 m", "60m": "60 m",
    "100m": "100 m", "200m": "200 m", "200m sh": "200 m (short track)",
    "300m": "300 m", "300m sh": "300 m (short track)",
    "400m": "400 m", "400m sh": "400 m (short track)",
    "500m": "500 m", "500m sh": "500 m (short track)",
    "50mH": "50 m haies", "55mH": "55 m haies", "60mH": "60 m haies",
    "100mH": "100 m haies", "110mH": "110 m haies", "400mH": "400 m haies",
    "600m": "600 m", "600m sh": "600 m (short track)",
    "800m": "800 m", "800m sh": "800 m (short track)",
    "1000m": "1000 m", "1000m sh": "1000 m (short track)",
    "1500m": "1500 m", "1500m sh": "1500 m (short track)",
    "Mile": "Mile", "Mile sh": "Mile (short track)",
    "2000m": "2000 m", "2000m sh": "2000 m (short track)",
    "2000m SC": "2000 m steeple",
    "3000m SC": "3000 m steeple",
    "3000m": "3000 m", "3000m sh": "3000 m (short track)",
    "2 Miles": "2 Miles", "2 Miles sh": "2 Miles (short track)",
    "5000m": "5000 m", "5000m sh": "5000 m (short track)",
    "10000m": "10 000 m",
    "HJ": "Saut en hauteur", "PV": "Saut à la perche",
    "LJ": "Saut en longueur", "TJ": "Triple saut",
    "SP": "Lancer du poids", "DT": "Lancer du disque",
    "HT": "Lancer du marteau", "JT": "Lancer du javelot",
    "Dec.": "Décathlon", "Hept.": "Heptathlon",
    "Hept. sh": "Heptathlon (short track)", "Pent. sh": "Pentathlon (short track)",
    "Mile route": "Mile route",
    "5 km": "5 km route", "10 km": "10 km route", "15 km": "15 km route",
    "10 Miles": "10 Miles route", "20 km": "20 km route",
    "HM": "Semi-marathon", "25 km": "25 km route",
    "30 km": "30 km route", "Marathon": "Marathon", "100 km": "100 km route",
    "3kmW": "3 km marche route", "5kmW": "5 km marche route",
    "10kmW": "10 km marche route", "15kmW": "15 km marche route",
    "20kmW": "20 km marche route", "30kmW": "30 km marche route",
    "35kmW": "35 km marche route", "50kmW": "50 km marche route",
    "3000mW": "3000 m marche (piste)", "5000mW": "5000 m marche (piste)",
    "10000mW": "10 000 m marche (piste)",
    "15000mW": "15 000 m marche (piste)",
    "20000mW": "20 000 m marche (piste)",
    "30000mW": "30 000 m marche (piste)",
    "50000mW": "50 000 m marche (piste)",
    "4x100m": "4×100 m", "4x200m": "4×200 m", "4x200m sh": "4×200 m (short track)",
    "4x400m": "4×400 m", "4x400m sh": "4×400 m (short track)",
    "4x400mix": "4×400 m mixte", "4x400mix sh": "4×400 m mixte (short track)",
}

# ============================================================
# EXTRACTION DU TEXTE PDF
# ============================================================

def extract_page_text(pdf_path, page_num):
    """Retourne le texte d'une page en mode layout."""
    out = subprocess.run(
        ["pdftotext", "-layout", "-f", str(page_num), "-l", str(page_num), pdf_path, "-"],
        capture_output=True, text=True, check=True
    )
    return out.stdout

# ============================================================
# PARSING D'UNE PAGE DE DONNÉES
# ============================================================

# Regex pour identifier les codes d'épreuves dans la ligne d'en-tête
# Doit capturer : 50m, 60mH, 100m, 200m sh, 4x100m, HJ, PV, Dec., Hept. sh,
#                  5 km, HM, Marathon, 3kmW, 3km W, Mile route, etc.
# La ligne d'en-tête a "Points" et 4 à 10 codes d'épreuves séparés par des espaces.

def parse_header_line(line):
    """
    Reçoit une ligne contenant "Points" et les codes d'épreuves.
    Identifie chaque code en cherchant dans la liste de codes connus (KNOWN_CODES_SORTED).
    Retourne ("left"/"right", [(code_normalized, col_start, col_end)])
    """
    idx_points = line.find("Points")
    if idx_points == -1:
        return None
    line_clean = line.rstrip()
    is_right = idx_points > len(line_clean) / 2

    # Pour chaque code connu (du plus long au plus court), chercher s'il apparaît
    # dans la ligne et noter sa position. Les codes plus longs sont prioritaires
    # pour éviter "2000m" qui matche "2000m SC".
    matches = []  # liste de (start, end, code_raw)
    occupied = [False] * len(line)
    # Trier KNOWN_CODES par longueur décroissante (déjà fait dans KNOWN_CODES_SORTED)
    for code in KNOWN_CODES_SORTED:
        # Chercher toutes les occurrences non encore consommées
        idx = 0
        while True:
            pos = line.find(code, idx)
            if pos == -1:
                break
            end = pos + len(code)
            # Vérifier que la position n'est pas déjà occupée
            if any(occupied[pos:end]):
                idx = pos + 1
                continue
            # Vérifier que ce n'est pas un sous-mot (caractère adjacent doit être un séparateur)
            before_ok = (pos == 0) or (not line[pos-1].isalnum() and line[pos-1] != '.')
            after_ok = (end == len(line)) or (not line[end].isalnum() and line[end] != '.')
            # Exception pour "Mile" vs "Mile sh" vs "Mile route" : le matching du plus long en premier gère déjà ce cas
            if before_ok and after_ok:
                matches.append((pos, end, code))
                for i in range(pos, end):
                    occupied[i] = True
            idx = pos + 1

    if not matches:
        return None

    # Trier par position et réordonner (start, end, code) -> (code, start, end)
    matches.sort(key=lambda m: m[0])
    cols = [(code, start, end) for (start, end, code) in matches]

    return ("right" if is_right else "left", cols)


def parse_data_line(line, header_layout, header_cols):
    """
    Parse une ligne de données. header_cols = liste ordonnée [(code, start, end), ...]
    header_layout: 'left' = Points à gauche, 'right' = Points à droite

    Stratégie :
    1. Détecter les tokens dans la ligne
    2. Identifier le token Points (1er ou dernier nombre 1-1400)
    3. Mapper les tokens restants aux codes d'épreuves dans l'ORDRE
       (le mode -layout du PDF préserve l'ordre des colonnes même si le layout
       Points-gauche vs Points-droite change)
    """
    line = line.rstrip()
    if not line.strip():
        return None

    pieces = [(m.group(), m.start(), m.end()) for m in re.finditer(r'\S+', line)]
    if not pieces:
        return None

    # Identifier les nombres aux extrémités potentiels pour Points
    first_token = pieces[0][0]
    last_token = pieces[-1][0]
    first_is_pts = first_token.isdigit() and 1 <= int(first_token) <= 1400
    last_is_pts = last_token.isdigit() and 1 <= int(last_token) <= 1400

    # Choisir Points selon le layout (avec fallback si layout ne matche pas)
    if header_layout == "left" and first_is_pts:
        points = int(first_token)
        data_tokens = pieces[1:]
    elif header_layout == "right" and last_is_pts:
        points = int(last_token)
        data_tokens = pieces[:-1]
    elif first_is_pts and not last_is_pts:
        points = int(first_token)
        data_tokens = pieces[1:]
    elif last_is_pts and not first_is_pts:
        points = int(last_token)
        data_tokens = pieces[:-1]
    else:
        return None

    # Vérifier qu'on a le bon nombre de tokens
    if len(data_tokens) == 0:
        return None

    # Si le nombre de tokens correspond exactement au nombre de codes,
    # on peut mapper directement par ordre (plus robuste que par position)
    n_codes = len(header_cols)
    if len(data_tokens) == n_codes:
        marks_by_code = {}
        for i, (code, _, _) in enumerate(header_cols):
            mark = data_tokens[i][0]
            marks_by_code[code] = mark
        return (points, marks_by_code)

    # Sinon : mapping par position (plus fragile mais peut sauver certains cas)
    marks_by_code = {}
    for token, tstart, tend in data_tokens:
        tcenter = (tstart + tend) / 2
        best_code = None
        best_dist = 1e9
        for code, hstart, hend in header_cols:
            hcenter = (hstart + hend) / 2
            d = abs(tcenter - hcenter)
            if d < best_dist:
                best_dist = d
                best_code = code
        if best_code is not None and best_code not in marks_by_code:
            marks_by_code[best_code] = token

    return (points, marks_by_code)


# ============================================================
# NORMALISATION DES MARKS
# ============================================================

def mark_to_value(mark_str, group):
    """
    Convertit un mark en (text_clean, value_numeric).
    Le 'group' indique si c'est field (mètres/points) ou course (temps).
    Retourne (None, None) si le mark est "-".
    """
    if mark_str is None or mark_str == "-":
        return (None, None)

    # Field (jumps, throws) : valeur en mètres décimale
    if group in ("Jump", "Throws"):
        try:
            return (mark_str, float(mark_str))
        except ValueError:
            return (mark_str, None)

    # Combined : entier
    if group == "Combined Events":
        try:
            return (mark_str, float(int(mark_str)))
        except ValueError:
            return (mark_str, None)

    # Temps : peut être X.XX (secondes), M:SS.xx, H:MM:SS
    if ":" in mark_str:
        parts = mark_str.split(":")
        try:
            if len(parts) == 2:
                secs = int(parts[0]) * 60 + float(parts[1])
            elif len(parts) == 3:
                secs = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
            else:
                return (mark_str, None)
            return (mark_str, round(secs, 3))
        except ValueError:
            return (mark_str, None)

    # Sinon : nombre décimal direct (secondes)
    try:
        return (mark_str, float(mark_str))
    except ValueError:
        return (mark_str, None)


# ============================================================
# NORMALISATION DES CODES D'ÉPREUVES
# ============================================================

# Liste exhaustive des codes d'épreuves WA valides (utilisé pour parsing robuste des en-têtes)
KNOWN_CODES = {
    # Sprints
    "50m", "55m", "60m", "100m", "200m", "200m sh",
    "300m", "300m sh", "400m", "400m sh", "500m", "500m sh",
    # Hurdles
    "50mH", "55mH", "60mH", "100mH", "110mH", "300mH", "400mH",
    # Middle distances
    "600m", "600m sh", "800m", "800m sh",
    "1000m", "1000m sh", "1500m", "1500m sh",
    "Mile", "Mile sh",
    "2000m", "2000m sh", "2000m SC", "3000m SC",
    # Long distances
    "3000m", "3000m sh", "2 Miles", "2 Miles sh",
    "5000m", "5000m sh", "10000m",
    # Road running
    "5 km", "10 km", "15 km", "10 Miles", "20 km",
    "HM", "25 km", "30 km", "Marathon", "100 km",
    "Mile route",
    # Race Walking on road
    "3km W", "5km W", "10km W", "15km W", "20km W",
    "30km W", "35km W", "35 km W", "50km W",
    "HMW", "MarW",
    # Race Walking on track (avec et sans virgule selon le PDF)
    "3000mW", "5000mW", "10000mW", "15000mW", "20000mW",
    "30000mW", "35000mW", "50000mW",
    "3,000mW", "5,000mW", "10,000mW", "15,000mW", "20,000mW",
    "30,000mW", "35,000mW", "50,000mW",
    # Field
    "HJ", "PV", "LJ", "TJ", "SP", "DT", "HT", "JT",
    # Combined
    "Dec.", "Hept.", "Hept. sh", "Pent.", "Pent. sh",
    # Relays
    "4x100m", "4x200m", "4x200m sh", "4x400m", "4x400m sh",
    "4x400mix", "4x400mix sh",
}

# Liste triée par longueur décroissante pour matcher les plus longs en premier
# (ex: "2000m SC" avant "2000m", sinon "2000m" matche d'abord)
KNOWN_CODES_SORTED = sorted(KNOWN_CODES, key=lambda c: -len(c))

def normalize_code(code, section_type):
    """Normalise un code d'épreuve. Distingue Mile piste vs route et nettoie les variantes."""
    code = code.strip()
    # Normalisation des codes de marche piste : retirer les virgules
    code = code.replace(",", "")
    # Normaliser les espaces dans codes marche route (3km W → 3kmW, 35 km W → 35kmW)
    if re.match(r"^\d+\s*km\s+W$", code):
        code = re.sub(r"\s+", "", code)
    # Mile : "Mile" en road = Mile route ; ailleurs = Mile piste
    if code == "Mile" and section_type in ("road_1", "road_2"):
        return "Mile route"
    return code


# ============================================================
# EXTRACTION COMPLÈTE D'UNE PAGE
# ============================================================

def extract_page(pdf_path, page_num, section_type):
    """
    Extrait toutes les données d'une page de tableau de scoring.
    Retourne dict { code: [(points, mark_str, mark_value)] }
    """
    text = extract_page_text(pdf_path, page_num)
    lines = text.split("\n")

    # Trouver la ligne d'en-tête (contient "Points")
    header_idx = None
    for i, line in enumerate(lines):
        if "Points" in line:
            header_idx = i
            break

    if header_idx is None:
        return {}

    header_line = lines[header_idx]
    parsed_header = parse_header_line(header_line)
    if parsed_header is None:
        return {}
    layout, header_cols = parsed_header

    # Normaliser les codes
    header_cols_normalized = [
        (normalize_code(code, section_type), start, end)
        for (code, start, end) in header_cols
    ]

    # Extraire les données ligne par ligne
    result = defaultdict(list)
    for line in lines[header_idx + 1:]:
        parsed = parse_data_line(line, layout, header_cols_normalized)
        if parsed is None:
            continue
        points, marks = parsed
        for code, mark_str in marks.items():
            if mark_str == "-":
                continue
            # Identifier le groupe pour la normalisation
            group = SECTION_GROUP.get(section_type)
            if group is None:  # section "field" → déterminer par code
                group = field_group_of(code)
            mark_clean, mark_val = mark_to_value(mark_str, group)
            if mark_clean is not None:
                result[code].append((points, mark_clean, mark_val))

    return dict(result)


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================

def extract_all(pdf_path):
    """
    Extrait toute la table à partir du PDF.
    Retourne dict { (sexe, code) -> [(points, mark_str, mark_value)] }
    + metadata par épreuve { (sexe, code) -> {group, type, unit, direction, label} }

    Note: certaines pages n'ont pas leur header (cellule de header tronquée par le
    moteur de rendu PDF). On mémorise donc le dernier header valide PAR SECTION
    et on l'utilise comme fallback.
    """
    all_data = defaultdict(list)
    meta = {}

    for (title, page_garde, page_start, page_end, sexe, section_type) in SECTIONS:
        print(f"  [{sexe}] {title} (p.{page_start}-{page_end}) ...", flush=True)
        # Pour cette section, mémoriser le dernier header valide
        last_header_layout = None
        last_header_cols = None

        for p in range(page_start, page_end + 1):
            try:
                page_data, header_info = extract_page_with_header(
                    pdf_path, p, section_type,
                    fallback_layout=last_header_layout,
                    fallback_cols=last_header_cols
                )
                if header_info is not None:
                    last_header_layout, last_header_cols = header_info
            except Exception as e:
                print(f"    ⚠ Erreur page {p}: {e}")
                continue

            for code, rows in page_data.items():
                group = SECTION_GROUP.get(section_type)
                if group is None:
                    group = field_group_of(code)
                t, u, d = categorize(group, code)
                meta[(sexe, code)] = {
                    "group_en": group,
                    "type": t,
                    "unit": u,
                    "direction": d,
                    "label": LABELS_FR.get(code, code),
                }
                all_data[(sexe, code)].extend(rows)

    # Dédupliquer + trier par points décroissant
    for k in all_data:
        seen = set()
        unique = []
        for row in sorted(all_data[k], key=lambda x: -x[0]):
            if row[0] in seen:
                continue
            seen.add(row[0])
            unique.append(row)
        all_data[k] = unique

    return dict(all_data), meta


def extract_page_with_header(pdf_path, page_num, section_type,
                              fallback_layout=None, fallback_cols=None):
    """
    Variante d'extract_page qui :
    - Détecte le header si présent, sinon utilise le fallback
    - Retourne (data, header_info_for_next_page)
    """
    text = extract_page_text(pdf_path, page_num)
    lines = text.split("\n")

    # Chercher la ligne d'en-tête
    header_idx = None
    for i, line in enumerate(lines):
        if "Points" in line:
            header_idx = i
            break

    if header_idx is not None:
        parsed = parse_header_line(lines[header_idx])
        if parsed is not None:
            layout, header_cols = parsed
            header_cols_normalized = [
                (normalize_code(code, section_type), start, end)
                for (code, start, end) in header_cols
            ]
            data_start = header_idx + 1
            current_layout = layout
            current_cols = header_cols_normalized
            header_info = (layout, header_cols_normalized)
        else:
            if fallback_layout is None:
                return ({}, None)
            current_layout = fallback_layout
            current_cols = fallback_cols
            data_start = header_idx + 1
            header_info = None
    else:
        # Pas de header sur cette page : utiliser fallback, mais détecter le layout réel
        if fallback_layout is None or fallback_cols is None:
            return ({}, None)

        # Détecter le layout réel : chercher la 1ère ligne de données
        # et regarder si elle commence ou finit par un nombre 1-1400
        current_layout = fallback_layout  # par défaut
        data_start = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            tokens = stripped.split()
            if not tokens:
                continue
            first_num = tokens[0].isdigit() and 1 <= int(tokens[0]) <= 1400
            last_num = tokens[-1].isdigit() and 1 <= int(tokens[-1]) <= 1400
            if first_num and not last_num:
                current_layout = "left"
                data_start = i
                break
            elif last_num and not first_num:
                current_layout = "right"
                data_start = i
                break
            elif first_num and last_num:
                # Cas ambigu (rare) : on utilise le fallback
                data_start = i
                break

        # Ajuster les positions des colonnes selon le layout réel
        # Si le fallback est dans le même layout, on garde les positions
        # Sinon, le positionnement par centre doit toujours fonctionner car les
        # colonnes de données sont à des x absolus dans le PDF, indépendamment
        # de la position de Points
        current_cols = fallback_cols
        header_info = None

    # Extraire les données ligne par ligne
    result = defaultdict(list)
    for line in lines[data_start:]:
        parsed = parse_data_line(line, current_layout, current_cols)
        if parsed is None:
            continue
        points, marks = parsed
        for code, mark_str in marks.items():
            if mark_str == "-":
                continue
            group = SECTION_GROUP.get(section_type)
            if group is None:
                group = field_group_of(code)
            mark_clean, mark_val = mark_to_value(mark_str, group)
            if mark_clean is not None:
                result[code].append((points, mark_clean, mark_val))

    return (dict(result), header_info)


# ============================================================
# EXPORTS
# ============================================================

def export_csv(data, meta, out_path):
    """
    Export CSV au format long.
    Les épreuves mixtes (4x400mix, 4x400mix sh) apparaissent dans M ET W
    avec les mêmes valeurs, comme dans le PDF officiel WA.
    """
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        w.writerow(["sex","code","group_en","type","unit","label","points","mark_text","mark_value"])
        for (sexe, code) in sorted(data.keys()):
            m = meta[(sexe, code)]
            for (pts, txt, val) in data[(sexe, code)]:
                w.writerow([sexe, code, m["group_en"], m["type"], m["unit"],
                            m["label"], pts, txt, val])

def export_json(data, meta, out_path, minified=False):
    obj = OrderedDict()

    obj["_meta"] = {
        "version": "WA Scoring Tables 2025",
        "edition": "April 2025 revised",
        "source": "World Athletics official PDF, extracted via wa_pdf_to_data.py",
        "generated": date.today().isoformat(),
        "schema": {
            "data_format": "Each event has a 'data' array of [points, mark_value] pairs, sorted by points descending.",
            "sex_codes": {
                "M": "Men",
                "W": "Women"
            },
            "mark_value_units": {
                "seconds": "for time-based events",
                "meters": "for distance/height events",
                "points": "for combined events"
            },
            "lookup_rule": "WA rule: if a performance falls between two values, use the LOWER points value.",
            "direction": "'min' = smaller mark is better (time), 'max' = larger mark is better (distance/points)",
            "mixed_relays": "Codes '4x400mix' and '4x400mix sh' appear in BOTH M and W sections with identical values, mirroring the official PDF structure."
        },
        "stats": {
            "events_M": sum(1 for (s,c) in data if s == "M"),
            "events_W": sum(1 for (s,c) in data if s == "W"),
            "total_rows": sum(len(v) for v in data.values()),
        }
    }

    for sexe in ("M", "W"):
        obj[sexe] = OrderedDict()
        codes = sorted({c for (s,c) in data if s == sexe})
        for code in codes:
            m = meta[(sexe, code)]
            obj[sexe][code] = {
                "label": m["label"],
                "group_en": m["group_en"],
                "type": m["type"],
                "unit": m["unit"],
                "direction": m["direction"],
                "data": [[pts, val] for (pts, txt, val) in data[(sexe, code)]],
            }

    with open(out_path, "w", encoding="utf-8") as f:
        if minified:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
        else:
            json.dump(obj, f, ensure_ascii=False, indent=2)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 wa_pdf_to_data.py <PDF_path> [output_dir]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "."

    print(f"Extracting {pdf_path} ...")
    data, meta = extract_all(pdf_path)

    print(f"\n=== Résultat ===")
    print(f"Épreuves indexées : {len(data)}")
    print(f"Lignes totales : {sum(len(v) for v in data.values())}")
    print(f"Hommes : {sum(1 for (s,c) in data if s == 'M')} épreuves")
    print(f"Femmes : {sum(1 for (s,c) in data if s == 'W')} épreuves")

    csv_path = f"{out_dir}/wa_scoring_tables_2025.csv"
    json_path = f"{out_dir}/wa_scoring_tables_2025.json"
    json_min_path = f"{out_dir}/wa_scoring_tables_2025.min.json"

    export_csv(data, meta, csv_path)
    export_json(data, meta, json_path, minified=False)
    export_json(data, meta, json_min_path, minified=True)

    print(f"\nFichiers générés :")
    print(f"  {csv_path}")
    print(f"  {json_path}")
    print(f"  {json_min_path}")
