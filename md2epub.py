#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
md2epub.py
==========

Script pour convertir des fichiers Markdown en livres électroniques EPUB.
Supporte la conversion d'un fichier Markdown unique ou de plusieurs fichiers
organisés en chapitres, avec gestion des images et métadonnées.

Fonctionnalités :
- Conversion d'un fichier Markdown vers EPUB
- Support des métadonnées (titre, auteur, description)
- Gestion des images intégrées
- Support des fichiers de chapitres multiples
- Génération automatique de la table des matières
- Style CSS basique pour une lecture agréable

Ce module peut aussi être importé dans d'autres programmes Python
pour une conversion programmatique.
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import ebooklib
from ebooklib import epub
import markdown
from markdown.extensions import codehilite, fenced_code, tables, toc


def extract_metadata_from_md(content: str) -> Dict[str, str]:
    """Extrait les métadonnées YAML frontmatter du Markdown.
    
    Args:
        content: Contenu Markdown à analyser
        
    Returns:
        Dictionnaire des métadonnées trouvées
    """
    metadata = {}
    
    # Vérifier si le fichier commence par du frontmatter YAML
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            yaml_content = parts[1].strip()
            for line in yaml_content.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    metadata[key] = value
    
    return metadata


def split_into_chapters(content: str, base_title: str = "Chapitre") -> List[Tuple[str, str]]:
    """Divise le contenu Markdown en chapitres basés sur les titres.
    
    Args:
        content: Contenu Markdown complet
        base_title: Titre de base pour les chapitres sans titre
        
    Returns:
        Liste de tuples (titre, contenu) pour chaque chapitre
    """
    chapters = []
    
    # Diviser par les titres de niveau 1 (# Titre) ou 2 (## Titre)
    # Utiliser une regex pour capturer les titres
    pattern = r'^(#{1,2})\s+(.+)$'
    lines = content.split('\n')
    
    current_chapter = []
    current_title = None
    chapter_num = 1
    found_first_title = False
    
    for line in lines:
        match = re.match(pattern, line)
        if match and match.group(1) in ['#', '##']:
            # Si c'est le premier titre trouvé et qu'il n'y a pas encore de chapitre,
            # commencer un nouveau chapitre
            if not found_first_title:
                found_first_title = True
                current_title = match.group(2).strip()
                current_chapter = [line]
            else:
                # Sauvegarder le chapitre précédent
                if current_chapter:
                    title = current_title or f"{base_title} {chapter_num}"
                    chapters.append((title, '\n'.join(current_chapter)))
                    chapter_num += 1
                
                # Commencer un nouveau chapitre
                current_title = match.group(2).strip()
                current_chapter = [line]
        else:
            current_chapter.append(line)
    
    # Ajouter le dernier chapitre
    if current_chapter:
        title = current_title or f"{base_title} {chapter_num}"
        chapters.append((title, '\n'.join(current_chapter)))
    
    # Si aucun chapitre n'a été trouvé, traiter tout le contenu comme un seul chapitre
    if not chapters:
        chapters.append((base_title + " 1", content))
    
    return chapters


def markdown_to_html(content: str) -> str:
    """Convertit le Markdown en HTML.
    
    Args:
        content: Contenu Markdown
        
    Returns:
        HTML généré
    """
    md = markdown.Markdown(
        extensions=[
            'fenced_code',
            'tables',
            'nl2br'
        ]
    )
    return md.convert(content)


def create_default_css() -> str:
    """Retourne le CSS par défaut pour l'EPUB.
    
    Returns:
        CSS stylé pour une lecture agréable
    """
    return """
body {
    font-family: Georgia, serif;
    line-height: 1.6;
    margin: 1em;
    color: #333;
}

h1, h2, h3, h4, h5, h6 {
    color: #2c3e50;
    margin-top: 1.5em;
    margin-bottom: 0.5em;
}

h1 {
    border-bottom: 2px solid #3498db;
    padding-bottom: 0.3em;
}

h2 {
    border-bottom: 1px solid #bdc3c7;
    padding-bottom: 0.2em;
}

p {
    margin-bottom: 1em;
    text-align: justify;
}

blockquote {
    margin: 1em 2em;
    padding: 0.5em 1em;
    border-left: 4px solid #3498db;
    background-color: #f8f9fa;
    font-style: italic;
}

code {
    background-color: #f4f4f4;
    padding: 0.2em 0.4em;
    border-radius: 3px;
    font-family: 'Courier New', monospace;
}

pre {
    background-color: #f8f8f8;
    padding: 1em;
    border-radius: 5px;
    overflow-x: auto;
    border: 1px solid #ddd;
}

pre code {
    background: none;
    padding: 0;
}

img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 1em auto;
}

table {
    border-collapse: collapse;
    width: 100%;
    margin: 1em 0;
}

th, td {
    border: 1px solid #ddd;
    padding: 0.5em;
    text-align: left;
}

th {
    background-color: #f2f2f2;
    font-weight: bold;
}

ul, ol {
    margin: 1em 0;
    padding-left: 2em;
}

li {
    margin-bottom: 0.5em;
}

a {
    color: #3498db;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

.toc {
    background-color: #f8f9fa;
    padding: 1em;
    border-radius: 5px;
    margin: 1em 0;
}

.toc h2 {
    margin-top: 0;
    border-bottom: none;
}

.toc ul {
    list-style-type: none;
    padding-left: 0;
}

.toc li {
    margin: 0.5em 0;
}

.toc a {
    color: #2c3e50;
    font-weight: bold;
}
"""


def collect_images_from_markdown(content: str, base_dir: str) -> Dict[str, str]:
    """Collecte les images référencées dans le Markdown.
    
    Args:
        content: Contenu Markdown
        base_dir: Répertoire de base pour les images
        
    Returns:
        Dictionnaire mapping les chemins d'images vers les chemins EPUB
    """
    image_map = {}
    
    # Trouver toutes les références d'images ![alt](path)
    img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    matches = re.findall(img_pattern, content)
    
    for alt_text, img_path in matches:
        if os.path.isabs(img_path):
            full_path = img_path
        else:
            full_path = os.path.join(base_dir, img_path)
        
        if os.path.exists(full_path):
            # Générer un nom unique pour l'image dans l'EPUB
            img_name = os.path.basename(full_path)
            # Éviter les conflits de noms
            counter = 1
            original_name = img_name
            while img_name in image_map.values():
                name, ext = os.path.splitext(original_name)
                img_name = f"{name}_{counter}{ext}"
                counter += 1
            
            image_map[img_path] = img_name
    
    return image_map


def convert_md_to_epub(
    md_path: str,
    epub_path: str,
    title: Optional[str] = None,
    author: Optional[str] = None,
    description: Optional[str] = None,
    language: str = "fr"
) -> None:
    """Convertit un fichier Markdown en EPUB.
    
    Args:
        md_path: Chemin vers le fichier Markdown
        epub_path: Chemin de sortie pour l'EPUB
        title: Titre du livre (optionnel, sera extrait du MD si absent)
        author: Auteur du livre (optionnel)
        description: Description du livre (optionnel)
        language: Langue du livre (défaut: "fr")
    """
    # Lire le fichier Markdown
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extraire les métadonnées du frontmatter
    metadata = extract_metadata_from_md(content)
    
    # Utiliser les paramètres fournis ou les métadonnées extraites
    book_title = title or metadata.get('title') or Path(md_path).stem
    book_author = author or metadata.get('author') or "Auteur inconnu"
    book_description = description or metadata.get('description') or ""
    
    # Créer le livre EPUB
    book = epub.EpubBook()
    
    # Définir les métadonnées
    book.set_identifier(f"md2epub_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    book.set_title(book_title)
    book.set_language(language)
    book.add_author(book_author)
    
    if book_description:
        book.add_metadata('DC', 'description', book_description)
    
    # Ajouter la date de création
    book.add_metadata('DC', 'date', datetime.now().strftime('%Y-%m-%d'))
    
    # Créer le style CSS
    style = epub.EpubItem(
        uid="style_default",
        file_name="style/default.css",
        media_type="text/css",
        content=create_default_css()
    )
    book.add_item(style)
    
    # Collecter les images
    base_dir = os.path.dirname(md_path) or "."
    image_map = collect_images_from_markdown(content, base_dir)
    
    # Ajouter les images au livre
    for original_path, epub_name in image_map.items():
        full_path = os.path.join(base_dir, original_path)
        if os.path.exists(full_path):
            with open(full_path, 'rb') as img_file:
                img_content = img_file.read()
            
            img_item = epub.EpubItem(
                uid=f"img_{epub_name}",
                file_name=f"images/{epub_name}",
                media_type="image/jpeg" if epub_name.lower().endswith(('.jpg', '.jpeg')) else "image/png",
                content=img_content
            )
            book.add_item(img_item)
    
    # Diviser en chapitres
    chapters = split_into_chapters(content)
    
    # Vérifier qu'on a des chapitres
    if not chapters:
        raise ValueError("Aucun chapitre trouvé dans le contenu Markdown")
    
    # Créer les chapitres EPUB
    spine_items = []
    toc_items = []
    
    for i, (chapter_title, chapter_content) in enumerate(chapters, 1):
        # Vérifier que le contenu n'est pas vide
        if not chapter_content.strip():
            print(f"Attention: Le chapitre '{chapter_title}' est vide, ignoré.")
            continue
            
        # Convertir le Markdown en HTML
        html_content = markdown_to_html(chapter_content)
        
        # Vérifier que le HTML généré n'est pas vide
        if not html_content.strip():
            print(f"Attention: Le chapitre '{chapter_title}' a généré du HTML vide, ignoré.")
            continue
        
        # Créer l'élément chapitre
        chapter = epub.EpubHtml(
            title=chapter_title,
            file_name=f'chapter_{i:02d}.xhtml',
            lang=language
        )
        
        # Créer le contenu HTML complet
        html_doc = f'''<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{chapter_title}</title>
    <link rel="stylesheet" type="text/css" href="style/default.css"/>
</head>
<body>
    <h1>{chapter_title}</h1>
    {html_content}
</body>
</html>'''
        
        chapter.set_content(html_doc.encode('utf-8'))
        
        book.add_item(chapter)
        spine_items.append(chapter)
        toc_items.append(chapter)
    
    # Vérifier qu'on a au moins un chapitre valide
    if not spine_items:
        raise ValueError("Aucun chapitre valide trouvé pour créer l'EPUB")
    
    # Définir la structure du livre
    book.toc = toc_items
    book.spine = spine_items
    
    # Ajouter le guide de navigation
    book.add_item(epub.EpubNcx())
    
    # Créer une page de navigation personnalisée
    nav = epub.EpubNav()
    
    nav_content = '''<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
<title>Table des matières</title>
</head>
<body>
<nav epub:type="toc">
<h1>Table des matières</h1>
<ol>
'''
    
    # Ajouter les liens vers les chapitres
    for i, chapter in enumerate(spine_items, 1):
        nav_content += f'<li><a href="{chapter.file_name}">{chapter.title}</a></li>\n'
    
    nav_content += '''</ol>
</nav>
</body>
</html>'''
    
    nav.set_content(nav_content.encode('utf-8'))
    book.add_item(nav)
    
    # Créer l'EPUB
    os.makedirs(os.path.dirname(epub_path) or ".", exist_ok=True)
    epub.write_epub(epub_path, book, {})


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Convertit un fichier Markdown en livre électronique EPUB. "
            "Supporte les métadonnées frontmatter, les images, et la "
            "division automatique en chapitres."
        )
    )
    parser.add_argument("input", help="Fichier Markdown à convertir")
    parser.add_argument(
        "output",
        nargs="?",
        help="Fichier EPUB de sortie (optionnel, basé sur l'entrée si omis)"
    )
    parser.add_argument(
        "--title",
        help="Titre du livre (remplace celui du frontmatter)"
    )
    parser.add_argument(
        "--author",
        help="Auteur du livre (remplace celui du frontmatter)"
    )
    parser.add_argument(
        "--description",
        help="Description du livre (remplace celle du frontmatter)"
    )
    parser.add_argument(
        "--language",
        default="fr",
        help="Langue du livre (défaut: fr)"
    )
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"Erreur : fichier introuvable : {args.input}", file=sys.stderr)
        sys.exit(1)
    
    # Déterminer le chemin de sortie
    if args.output:
        output_path = args.output
    else:
        base_name = Path(args.input).stem
        output_path = f"{base_name}.epub"
    
    try:
        convert_md_to_epub(
            md_path=args.input,
            epub_path=output_path,
            title=args.title,
            author=args.author,
            description=args.description,
            language=args.language
        )
        print(f"✅ Conversion terminée : {output_path}")
        print(f"📚 Fichier EPUB créé avec succès")
    except Exception as e:
        print(f"❌ Erreur lors de la conversion : {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
