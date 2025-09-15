# epub2md

`epub2md` est un outil en ligne de commande simple mais puissant pour convertir
des livres électroniques EPUB en Markdown. Il peut générer un fichier Markdown unique
ou diviser le livre en plusieurs fichiers de chapitres, extraire les images (y compris
la couverture), et maintenir l'ordre de lecture original défini par la
structure EPUB.

Le projet inclut également `md2epub`, un outil pour convertir des fichiers Markdown
vers le format EPUB.

**Bonus** : Le projet démontre un workflow complet de traduction de livres, 
de l'EPUB anglais original vers une traduction française complète en EPUB.

## Fonctionnalités

### epub2md (EPUB → Markdown)
- **Sortie unique ou multiple** – génère un fichier `.md` unique ou divise
  la sortie en fichiers par chapitre avec une table des matières automatique (`index.md`).
- **Extraction d'images** – copie toutes les images de l'EPUB dans un
  dossier dédié et met à jour les références dans le Markdown. La couverture
  du livre est détectée automatiquement et renommée en `cover.ext`.
- **Bannière de couverture** – insère optionnellement l'image de couverture en haut
  du Markdown généré ou de l'index pour un contexte visuel rapide.
- **Gestion robuste de la structure** – respecte la structure EPUB pour préserver
  l'ordre de lecture prévu ; utilise des valeurs par défaut sensées si la
  structure est manquante.
- **Sortie Markdown propre** – convertit HTML en Markdown sans
  retour à la ligne automatique et préserve les liens et images.
- **CLI flexible** – configure les chemins de sortie, préfixes, répertoires
  d'images, et désactive des fonctionnalités via des drapeaux en ligne de commande.

### md2epub (Markdown → EPUB)
- **Conversion Markdown vers EPUB** – convertit des fichiers Markdown en livres électroniques EPUB.
- **Support des métadonnées** – lit les métadonnées frontmatter YAML (titre, auteur, description).
- **Gestion des chapitres** – divise automatiquement le contenu en chapitres basés sur les titres.
- **Intégration d'images** – gère les images référencées dans le Markdown.
- **CSS personnalisé** – applique un style CSS pour une lecture agréable.
- **Table des matières** – génère automatiquement une table des matières navigable.

## Prérequis

- Python 3.7 ou plus récent
- Packages pip : [ebooklib](https://pypi.org/project/ebooklib/),
  [html2text](https://pypi.org/project/html2text/),
  [beautifulsoup4](https://pypi.org/project/beautifulsoup4/),
  [markdown](https://pypi.org/project/markdown/)

Installez les dépendances avec :

```sh
pip install ebooklib html2text beautifulsoup4 markdown
```

## Installation

Clone this repository or copy `epub2md.py` somewhere on your
`$PATH`.  The script is standalone; no other files in the repository
are required at runtime.

```sh
git clone https://github.com/your-user/epub2md.git
cd epub2md
pip install -r requirements.txt  # optional if you create a requirements file
```

Alternatively, run the script directly with Python after installing
the dependencies.

## Utilisation

### epub2md (EPUB → Markdown)

```sh
python epub2md.py input.epub [output.md]

python epub2md.py input.epub --split [--outdir OUTDIR]
```

### md2epub (Markdown → EPUB)

```sh
python md2epub.py input.md [output.epub]

# Avec des métadonnées personnalisées
python md2epub.py input.md --title "Mon Livre" --author "Mon Nom" --description "Description du livre"
```

### Single file conversion

Convert an EPUB into a single Markdown file.  If you omit the
`output.md` argument, a file named after the input (with a `.md`
extension) will be created in the current directory.

```sh
python epub2md.py book.epub book.md
```

By default all images are extracted into an `images/` subdirectory and
their references are rewritten.  The cover image, if detected, will
be renamed `cover.ext` and inserted as a banner at the top of the
Markdown.  Use `--no-images` to disable extraction or
`--no-cover-banner` to avoid inserting the cover banner (the cover
will still be exported and renamed).

### Split into chapters

Use `--split` to generate individual chapter files and an `index.md`
file listing them.  You can specify the output directory with
`--outdir`.  Chapter files are named using a prefix and a slugified
version of the chapter title.

```sh
python epub2md.py book.epub --split

# Specify output directory and prefixes
python epub2md.py book.epub --split --outdir out_md --prefix chapitre
```

Images are exported to `outdir/images/` by default and references in
all generated Markdown files are updated accordingly.  The index will
include the cover image banner unless `--no-cover-banner` is used.

### Options

| Option | Description |
|-------|-------------|
| `--split` | Split output into chapter files and generate an `index.md`. |
| `--outdir OUTDIR` | Directory for split output (default: `md_chapitres`). |
| `--prefix PREFIX` | Prefix for chapter files when splitting (default: `chapitre`). |
| `--imgdir DIR` | Subdirectory name for exported images (default: `images`). |
| `--no-images` | Do not export images or rewrite image references. |
| `--no-cover-banner` | Export and rename the cover image but do not insert it into the Markdown or index. |

The positional arguments are:

| Argument | Description |
|---------|-------------|
| `input` | Path to the input `.epub` file. |
| `output` | Path to the output `.md` file (only used in single file mode). |

### Examples

Convert an EPUB to a single Markdown file in the current directory,
with images extracted:

```sh
python epub2md.py alice.epub
# results in alice.md and an images/ folder
```

Convert to a Markdown file without extracting any images:

```sh
python epub2md.py alice.epub output.md --no-images
```

Diviser le livre en chapitres, stocker tout dans `out_md/`, et
préfixer les fichiers avec `part` :

```sh
python epub2md.py alice.epub --split --outdir out_md --prefix part
```

### Exemples md2epub

Convertir un fichier Markdown simple en EPUB :

```sh
python md2epub.py mon_livre.md
# génère mon_livre.epub
```

Convertir avec des métadonnées personnalisées :

```sh
python md2epub.py mon_livre.md --title "Le Grand Livre" --author "Jean Dupont" --language "fr"
```

Utiliser des métadonnées frontmatter YAML dans le Markdown :

```markdown
---
title: "Mon Premier Livre"
author: "Jean Dupont"
description: "Un livre de test créé avec md2epub"
---

# Introduction

Contenu du livre...
```

Puis convertir :

```sh
python md2epub.py livre_avec_metadata.md
```

### Exemple complet : Traduction et conversion

Voici un exemple complet de workflow pour traduire un livre et le convertir en EPUB :

```sh
# 1. Convertir EPUB anglais vers Markdown
python epub2md.py TheTheoryoftheLeisureClass.epub

# 2. Traduire le fichier Markdown (manuellement ou avec un outil de traduction)
# Résultat : LaTheorieDeLaClasseDeLoisir.md

# 3. Convertir la traduction française vers EPUB
python md2epub.py LaTheorieDeLaClasseDeLoisir.md
# Génère : LaTheorieDeLaClasseDeLoisir.epub
```

### Options md2epub

| Option | Description |
|-------|-------------|
| `--title TITRE` | Titre du livre (remplace celui du frontmatter) |
| `--author AUTEUR` | Auteur du livre (remplace celui du frontmatter) |
| `--description DESCRIPTION` | Description du livre (remplace celle du frontmatter) |
| `--language LANGUE` | Langue du livre (défaut: "fr") |

Les arguments positionnels sont :

| Argument | Description |
|---------|-------------|
| `input` | Chemin vers le fichier Markdown d'entrée |
| `output` | Chemin vers le fichier EPUB de sortie (optionnel, basé sur l'entrée si omis) |

## Fichiers du projet

Ce projet contient :

### Scripts principaux
- `epub2md.py` - Convertisseur EPUB vers Markdown
- `md2epub.py` - Convertisseur Markdown vers EPUB
- `requirements.txt` - Dépendances Python

### Exemple de traduction complète
- `TheTheoryoftheLeisureClass.epub` - Livre original en anglais (468 KB)
- `TheTheoryoftheLeisureClass.md` - Version Markdown du livre original (1683 lignes)
- `LaTheorieDeLaClasseDeLoisir.md` - Traduction française en Markdown (369 lignes)
- `LaTheorieDeLaClasseDeLoisir.epub` - Version EPUB de la traduction française (247 KB)
- `images/` - Images extraites du livre original

### Fichiers de test
- `example.md` - Exemple simple avec métadonnées frontmatter
- `example.epub` - EPUB généré à partir de l'exemple

## License

This project is released under the [MIT License](https://opensource.org/licenses/MIT).  See the
`LICENSE` file for details.

---

Feel free to contribute or open issues if you encounter any problems
or have ideas for improvements.  Happy reading! 📚