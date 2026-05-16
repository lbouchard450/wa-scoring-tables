# World Athletics Scoring Tables 2025

Référentiel de données structurées pour les **tables de cotation officielles de World Athletics**, édition révisée d'avril 2025.

*Structured data repository for the official **World Athletics Scoring Tables**, April 2025 revised edition.*

---

## 🇫🇷 Français

### À propos

Ce dépôt contient les tables de cotation 2025 de World Athletics converties en formats exploitables par programmation (CSV, JSON), à partir du PDF officiel de 846 pages publié par WA en avril 2025.

**Pourquoi ce dépôt ?** Le PDF officiel WA est inaccessible aux scripts et calculateurs. Plusieurs outils en ligne utilisent des approximations par formule qui dévient parfois jusqu'à 17 points de la table officielle (notamment sur les haies hommes). Ce dépôt fournit les **valeurs exactes** de la table, prêtes à l'usage.

### Contenu

| Fichier | Taille | Usage recommandé |
|---------|--------|------------------|
| `wa_scoring_tables_2025.csv` | 16 MB | Excel, Google Sheets, Python pandas, R |
| `wa_scoring_tables_2025.json` | 12 MB | Lecture humaine, débogage |
| `wa_scoring_tables_2025.min.json` | 2.8 MB | Apps Script, JavaScript, fetch HTTP |
| `wa_pdf_to_data.py` | 29 KB | Script Python de regénération depuis le PDF |

### Statistiques

- **170 épreuves** (85 hommes + 85 femmes)
- **217 768 entrées** (1 entrée = 1 paire performance → points)
- **8 catégories** : course, hurdles, field, combined, relay, road, walk_track, walk_road
- **Édition 2025 révisée** (avril 2025) avec les nouvelles épreuves : Mile route, 4×400 mixte, semi-marathon marche (HMW), marathon marche (MarW), 300m haies

### Structure du CSV

```
sex,code,group_en,type,unit,label,points,mark_text,mark_value
M,100m,Sprints,course,seconds,100 m,1400,9.46,9.46
M,100m,Sprints,course,seconds,100 m,1356,9.58,9.58
W,HJ,Jump,field,meters,Saut en hauteur,1400,2.18,2.18
M,Marathon,Road Running,road,seconds,Marathon,1307,2:00:36.00,7236.0
```

- **sex** : `M` (Men) ou `W` (Women)
- **code** : code court de l'épreuve (`100m`, `Marathon`, `HJ`, `4x400mix`...)
- **group_en** : groupe WA officiel
- **type** : `course` / `hurdles` / `field` / `combined` / `relay` / `road` / `walk_track` / `walk_road`
- **unit** : `seconds` / `meters` / `points`
- **label** : libellé français pour affichage
- **points** : valeur de 1 à 1400
- **mark_text** : performance lisible (format original du PDF)
- **mark_value** : performance numérique (secondes décimales, mètres, ou points)

### Structure du JSON

Format hiérarchique compact pour lookup direct :

```json
{
  "_meta": { "version": "WA Scoring Tables 2025", ... },
  "M": {
    "100m": {
      "label": "100 m",
      "group_en": "Sprints",
      "type": "course",
      "unit": "seconds",
      "direction": "min",
      "data": [[1400, 9.46], [1396, 9.47], [1356, 9.58], ...]
    },
    "Marathon": { ... }
  },
  "W": { ... }
}
```

Chaque entrée `data` est une paire `[points, mark_value]`, triée par points décroissants.

### Règle de lookup officielle WA

> *Si une performance se situe entre deux valeurs de la table, la valeur INFÉRIEURE (de points) est retenue.*

Concrètement :
- **Courses (temps)** : on cherche le plus grand `points` tel que `mark_value >= performance_secondes`
- **Concours (distance/hauteur)** : on cherche le plus grand `points` tel que `mark_value <= performance_metres`
- **Combinés** : idem que concours

### Relais mixtes

Les codes `4x400mix` et `4x400mix sh` apparaissent dans **les deux sections M et W** avec des valeurs identiques, conformément au format du PDF officiel.

### Utilisation

#### Apps Script (Google Sheets)

```javascript
function getWAPoints(sex, code, perfSeconds) {
  const url = 'https://raw.githubusercontent.com/lbouchard450/wa-scoring-tables/main/wa_scoring_tables_2025.min.json';
  const data = JSON.parse(UrlFetchApp.fetch(url).getContentText());
  const event = data[sex][code];
  for (const [pts, mark] of event.data) {
    if (event.direction === 'min' && mark >= perfSeconds) return pts;
    if (event.direction === 'max' && mark <= perfSeconds) return pts;
  }
  return null;
}
```

#### Python

```python
import json, urllib.request

URL = 'https://raw.githubusercontent.com/lbouchard450/wa-scoring-tables/main/wa_scoring_tables_2025.min.json'
data = json.loads(urllib.request.urlopen(URL).read())

def wa_points(sex, code, perf):
    event = data[sex][code]
    for pts, mark in event['data']:
        if event['direction'] == 'min' and mark >= perf: return pts
        if event['direction'] == 'max' and mark <= perf: return pts
    return None

# Exemples
print(wa_points('M', '100m', 9.58))      # → 1356 (Bolt)
print(wa_points('M', 'HJ', 2.45))        # → 1314 (Sotomayor)
print(wa_points('M', 'Marathon', 7235))  # → 1307 (Kiptum)
```

#### Google Sheets (formule directe)

```
=IMPORTDATA("https://raw.githubusercontent.com/lbouchard450/wa-scoring-tables/main/wa_scoring_tables_2025.csv")
```

### Reproductibilité

Le script `wa_pdf_to_data.py` permet de régénérer tous les fichiers à partir du PDF officiel WA. Utile quand WA publiera la prochaine édition (probablement 2028).

```bash
# Prérequis : Python 3.7+ et poppler-utils (pdftotext)
python3 wa_pdf_to_data.py World_Athletics_Scoring_Tables_of_Athletics.pdf
```

### Source

PDF officiel : World Athletics, *Scoring Tables of Athletics — 2025 Revised Edition*, par Dr. Bojidar Spiriev, mis à jour par Attila Spiriev. Disponible sur [worldathletics.org/about-iaaf/documents/technical-information](https://worldathletics.org/about-iaaf/documents/technical-information).

Le PDF source utilisé pour l'extraction est inclus dans ce dépôt : [World Athletics Scoring Tables of Athletics 2025.pdf](./World%20Athletics%20Scoring%20Tables%20of%20Athletics%202025.pdf)

### Licence

Les données proviennent de World Athletics (© 2025 World Athletics, tous droits réservés). Ce dépôt fournit une **reformulation structurée** des données pour faciliter l'usage technique, sans modification des valeurs.

Le **code** (`wa_pdf_to_data.py` et autres scripts) est sous licence **MIT** — voir [LICENSE](./LICENSE).

L'usage des **données** doit respecter les conditions de World Athletics. Pour un usage commercial des tables WA, contacter World Athletics directement.

### Crédits

Maintenu par **Luc Bouchard** dans le cadre des travaux du Comité des Maîtres (athlétisme masters, Québec). Conversion PDF → données structurées réalisée avec assistance IA.

---

## 🇬🇧 English

### About

This repository contains the **World Athletics Scoring Tables 2025** (revised edition, April 2025) converted to programmable formats (CSV, JSON) from the official 846-page PDF.

**Why this repository?** The official WA PDF is not accessible to scripts and calculators. Several online tools use polynomial approximations that deviate up to 17 points from the official table (especially for men's hurdles). This repository provides the **exact values** from the table, ready to use.

### Contents

| File | Size | Recommended use |
|------|------|-----------------|
| `wa_scoring_tables_2025.csv` | 16 MB | Excel, Google Sheets, Python pandas, R |
| `wa_scoring_tables_2025.json` | 12 MB | Human reading, debugging |
| `wa_scoring_tables_2025.min.json` | 2.8 MB | Apps Script, JavaScript, HTTP fetch |
| `wa_pdf_to_data.py` | 29 KB | Python script for PDF re-extraction |

### Statistics

- **170 events** (85 men + 85 women)
- **217,768 entries** (1 entry = 1 mark→points pair)
- **8 categories**: course, hurdles, field, combined, relay, road, walk_track, walk_road
- **2025 revised edition** (April 2025) with new events: Mile road, mixed 4×400, half-marathon walk (HMW), marathon walk (MarW), 300m hurdles

### CSV structure

Columns: `sex, code, group_en, type, unit, label, points, mark_text, mark_value`

- **sex**: `M` (Men) or `W` (Women)
- **code**: short event code (`100m`, `Marathon`, `HJ`, `4x400mix`...)
- **type**: `course` / `hurdles` / `field` / `combined` / `relay` / `road` / `walk_track` / `walk_road`
- **unit**: `seconds` / `meters` / `points`
- **points**: 1 to 1400
- **mark_value**: numeric performance (decimal seconds, meters, or points)

### Official WA lookup rule

> *If a performance falls between two values, use the LOWER points value.*

In practice:
- **Time events**: find the largest `points` such that `mark_value >= performance_seconds`
- **Field events**: find the largest `points` such that `mark_value <= performance_meters`

### Mixed relays

Codes `4x400mix` and `4x400mix sh` appear in **both M and W sections** with identical values, mirroring the official PDF format.

### Usage

#### Python

```python
import json, urllib.request

URL = 'https://raw.githubusercontent.com/lbouchard450/wa-scoring-tables/main/wa_scoring_tables_2025.min.json'
data = json.loads(urllib.request.urlopen(URL).read())

def wa_points(sex, code, perf):
    event = data[sex][code]
    for pts, mark in event['data']:
        if event['direction'] == 'min' and mark >= perf: return pts
        if event['direction'] == 'max' and mark <= perf: return pts
    return None

# Examples
print(wa_points('M', '100m', 9.58))      # → 1356 (Bolt)
print(wa_points('M', 'HJ', 2.45))        # → 1314 (Sotomayor)
print(wa_points('M', 'Marathon', 7235))  # → 1307 (Kiptum)
```

#### Apps Script (Google Sheets)

```javascript
function getWAPoints(sex, code, perfSeconds) {
  const url = 'https://raw.githubusercontent.com/lbouchard450/wa-scoring-tables/main/wa_scoring_tables_2025.min.json';
  const data = JSON.parse(UrlFetchApp.fetch(url).getContentText());
  const event = data[sex][code];
  for (const [pts, mark] of event.data) {
    if (event.direction === 'min' && mark >= perfSeconds) return pts;
    if (event.direction === 'max' && mark <= perfSeconds) return pts;
  }
  return null;
}
```

### Reproducibility

The `wa_pdf_to_data.py` script regenerates all files from the official WA PDF. Useful when WA publishes the next edition (likely 2028).

```bash
# Requires: Python 3.7+ and poppler-utils (pdftotext)
python3 wa_pdf_to_data.py World_Athletics_Scoring_Tables_of_Athletics.pdf
```

### Source

Official PDF: World Athletics, *Scoring Tables of Athletics — 2025 Revised Edition*, by Dr. Bojidar Spiriev, updated by Attila Spiriev. Available at [worldathletics.org/about-iaaf/documents/technical-information](https://worldathletics.org/about-iaaf/documents/technical-information).

The source PDF used for extraction is included in this repository: [World Athletics Scoring Tables of Athletics 2025.pdf](./World%20Athletics%20Scoring%20Tables%20of%20Athletics%202025.pdf)


### License

The data is from World Athletics (© 2025 World Athletics, all rights reserved). This repository provides a **structured reformulation** of the data for technical convenience, without modifying any values.

The **code** (`wa_pdf_to_data.py` and other scripts) is licensed under **MIT** — see [LICENSE](./LICENSE).

Use of the **data** must comply with World Athletics' terms. For commercial use of WA tables, contact World Athletics directly.

### Credits

Maintained by **Luc Bouchard** as part of the Comité des Maîtres (masters athletics, Quebec). PDF → structured data conversion performed with AI assistance.

---

## Validation

All world records yield identical points to the official PDF (15 records tested, 100% concordance):

| Athlete | Event | Performance | Points |
|---------|-------|-------------|--------|
| Usain Bolt | M 100m | 9.58 | 1356 |
| Kelvin Kiptum | M Marathon | 2:00:35 | 1307 |
| Javier Sotomayor | M HJ | 2.45 m | 1314 |
| Armand Duplantis | M PV | 6.30 m | 1350 |
| Kevin Mayer | M Decathlon | 9126 | 1302 |
| Florence Griffith-Joyner | W 100m | 10.49 | 1314 |
| Yaroslava Mahuchikh | W HJ | 2.10 m | 1319 |
| Toshikazu Yamanishi | M HMW | 1:20:34 | 1286 |
| United States | 4×400 mixed | 3:07.41 | 1234 |
