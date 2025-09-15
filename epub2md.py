#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
epub2md.py
===============

This script provides a command‑line interface for converting EPUB ebooks
into Markdown files. It supports both generating a single Markdown file
and splitting the output into per‑chapter files, complete with an
index and optional cover image handling. Images embedded in the EPUB
are extracted to a configurable subdirectory and all internal image
references are rewritten to point at the exported files.

Key features:

* Convert an EPUB to a single Markdown document or split it into
  individual chapters. When splitting, each chapter is saved as its
  own `.md` file and an `index.md` table of contents is generated.
* Automatically extract and rename the book’s cover image to
  `cover.ext` (preserving the original extension). The cover can be
  displayed as a banner at the top of the generated Markdown.
* Export all images into a designated folder and rewrite image paths
  within the Markdown so that they reference the exported files.
* Preserve the reading order defined by the EPUB spine so that the
  structure of the original book is respected.
* Optionally disable image extraction or the inclusion of the cover
  banner via command line flags.

This module can also be imported into other Python programs to
programmatically convert EPUB files to Markdown.
"""

import argparse
import os
import re
import sys
from typing import Dict, Iterable, Tuple

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import html2text


def slugify(name: str, fallback: str = "chapitre") -> str:
    """Return a slugified version of the given name.

    Strips leading/trailing whitespace, replaces spaces with hyphens,
    removes non‑alphanumeric characters and collapses multiple
    hyphens. If the resulting name is empty, uses the fallback.

    Args:
        name: The original name to slugify.
        fallback: The fallback slug if name produces an empty string.
    """
    name = re.sub(r"\s+", " ", (name or "").strip())
    if not name:
        name = fallback
    name = name.lower()
    name = re.sub(r"[^\w\s-]", "", name, flags=re.UNICODE)
    name = name.strip().replace(" ", "-")
    name = re.sub(r"-+", "-", name)
    return name or fallback


def extract_title_from_html(html: str) -> str:
    """Extract a title from HTML content.

    Looks for a first occurrence of `<h1>`, `<title>` or `<h2>` in
    this order. If none are found returns None.

    Args:
        html: HTML string to parse.

    Returns:
        The cleaned title or None if not found.
    """
    soup = BeautifulSoup(html, "html.parser")
    for selector in ["h1", "title", "h2"]:
        el = soup.find(selector)
        if el and el.get_text(strip=True):
            return el.get_text(strip=True)
    return None


def html_to_markdown_converter() -> html2text.HTML2Text:
    """Return a configured html2text converter.

    The converter is configured to preserve images and links and
    prevents automatic line wrapping so the Markdown is easier to
    process further or view in editors.
    """
    converter = html2text.HTML2Text()
    converter.ignore_links = False
    converter.ignore_images = False
    converter.body_width = 0  # no automatic line wrapping
    converter.unicode_snob = True
    return converter


def iter_spine_items(book: epub.EpubBook) -> Iterable[epub.EpubHtml]:
    """Yield document items from the book in reading order.

    Uses the spine information from the EPUB to respect the original
    reading order. If the spine is empty or malformed the function
    falls back to returning all document items.

    Args:
        book: The EPUB book object.

    Yields:
        Document items (`epub.EpubHtml`) in order.
    """
    idref_to_item = {i.id: i for i in book.get_items_of_type(ebooklib.ITEM_DOCUMENT)}
    yielded = False
    for spine_entry in book.spine:
        idref = None
        if isinstance(spine_entry, tuple):
            meta = spine_entry[1] if len(spine_entry) > 1 else {}
            idref = meta.get("idref")
        else:
            idref = spine_entry
        if idref and idref in idref_to_item:
            yielded = True
            yield idref_to_item[idref]
    if not yielded:
        for it in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            yield it


def detect_cover_item(book: epub.EpubBook) -> epub.EpubImage:
    """Detect the cover image item in an EPUB.

    The function attempts to detect the cover image in a robust
    manner. First it checks for an OPF metadata entry specifying
    a cover ID. Then it searches for an EPUB3 property designating
    the cover image. If those fail, it uses a heuristic based on
    filenames and identifiers containing words like 'cover' or
    translations thereof. If multiple candidates are found the
    shortest file path is chosen.

    Args:
        book: The EPUB book object.

    Returns:
        The `epub.EpubImage` corresponding to the cover or None.
    """
    # 1) EPUB2: <meta name="cover" content="cover-image-id"/>
    try:
        metas = book.get_metadata("OPF", "meta") or []
        for value, attrs in metas:
            if isinstance(attrs, dict) and attrs.get("name", "").lower() == "cover":
                cover_id = attrs.get("content")
                if cover_id:
                    for it in book.get_items_of_type(ebooklib.ITEM_IMAGE):
                        if it.id == cover_id:
                            return it
    except Exception:
        pass
    # 2) EPUB3: property "cover-image" or "cover" on an image item
    for it in book.get_items_of_type(ebooklib.ITEM_IMAGE):
        props = getattr(it, "properties", None)
        if props and ("cover-image" in props or "cover" in props):
            return it
    # 3) Heuristic on file names or IDs
    candidates = []
    for it in book.get_items_of_type(ebooklib.ITEM_IMAGE):
        fn = (it.file_name or "").lower()
        iid = (it.id or "").lower()
        if any(k in fn for k in ["cover", "couverture", "front", "titlepage"]) or \
           any(k in iid for k in ["cover", "couverture"]):
            candidates.append(it)
    if candidates:
        candidates.sort(key=lambda x: len(x.file_name or "z" * 999))
        return candidates[0]
    return None


def export_images(book: epub.EpubBook, outdir: str, imgdir: str = "images") -> Dict[str, str]:
    """Export all images from an EPUB to a directory and rewrite names.

    The function exports each image from the EPUB into
    `outdir/imgdir`, preserving original filenames unless the image is
    identified as the cover image. In that case, the image is renamed
    to `cover.ext` (with its original extension). A mapping of
    original internal hrefs and basenames to their new relative paths
    is returned, enabling path rewriting in HTML.

    Args:
        book: The EPUB book object.
        outdir: Destination directory for exported files.
        imgdir: Subdirectory within `outdir` for images.

    Returns:
        A dictionary mapping original hrefs and basenames to relative
        file paths within the Markdown output.
    """
    images_path = os.path.join(outdir, imgdir)
    os.makedirs(images_path, exist_ok=True)
    mapping: Dict[str, str] = {}
    cover_item = detect_cover_item(book)
    cover_src = cover_item.file_name if cover_item else None
    for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
        src_name = os.path.basename(item.file_name)
        if cover_src and item.file_name == cover_src:
            ext = os.path.splitext(src_name)[1] or ".jpg"
            dst_name = f"cover{ext}"
        else:
            dst_name = src_name
        dst_path = os.path.join(images_path, dst_name)
        with open(dst_path, "wb") as f:
            f.write(item.get_content())
        rel_path = os.path.join(imgdir, dst_name)
        mapping[item.file_name] = rel_path
        mapping[src_name] = rel_path
    return mapping


def rewrite_img_paths_in_html(html: str, image_map: Dict[str, str]) -> str:
    """Replace image references in HTML with exported paths.

    Performs simple replacement of href strings with their mapped
    destinations. This approach works for most EPUB files where
    images are referenced directly by file name or full path.

    Args:
        html: The HTML string to process.
        image_map: Mapping of original hrefs/basenames to new paths.

    Returns:
        The HTML with image paths rewritten.
    """
    for href, newpath in image_map.items():
        html = html.replace(href, newpath)
    return html


def convert_epub_to_single_md(
    epub_path: str,
    md_path: str,
    imgdir: str = "images",
    extract_images: bool = True,
    cover_banner: bool = True,
) -> None:
    """Convert an EPUB to a single Markdown file.

    Extracts the book title and optionally inserts the cover image at
    the top. The contents of each spine item are appended in order.
    Optionally extracts images and rewrites references.

    Args:
        epub_path: Path to the input EPUB file.
        md_path: Path to the output Markdown file.
        imgdir: Name of the subdirectory for exported images.
        extract_images: Whether to export images and rewrite paths.
        cover_banner: Whether to insert the cover image at the top.
    """
    book = epub.read_epub(epub_path)
    converter = html_to_markdown_converter()
    outdir = os.path.dirname(os.path.abspath(md_path)) or "."
    os.makedirs(outdir, exist_ok=True)
    image_map: Dict[str, str] = {}
    if extract_images:
        image_map = export_images(book, outdir, imgdir=imgdir)
    with open(md_path, "w", encoding="utf-8") as out:
        book_title_meta = book.get_metadata("DC", "title")
        book_title = (
            book_title_meta[0][0]
            if book_title_meta
            else os.path.splitext(os.path.basename(epub_path))[0]
        )
        out.write(f"# {book_title}\n\n")
        # Insert cover image banner
        if cover_banner and image_map:
            cover_rel = None
            for rel in image_map.values():
                if os.path.basename(rel).lower().startswith("cover."):
                    cover_rel = rel
                    break
            if cover_rel:
                out.write(f"![]({cover_rel})\n\n")
        # Write spine contents
        for item in iter_spine_items(book):
            html = item.get_content().decode("utf-8", errors="ignore")
            if image_map:
                html = rewrite_img_paths_in_html(html, image_map)
            md = converter.handle(html)
            seg_title = extract_title_from_html(html)
            if seg_title and not re.search(r"^#\s", md.lstrip(), flags=re.M):
                out.write(f"## {seg_title}\n\n")
            out.write(md)
            out.write("\n\n")


def convert_epub_to_split_md(
    epub_path: str,
    outdir: str,
    prefix: str = "chapitre",
    imgdir: str = "images",
    extract_images: bool = True,
    cover_banner: bool = True,
) -> Tuple[str, int]:
    """Convert an EPUB into multiple chapter files and an index.

    Each spine item is saved to a separate Markdown file named
    ``{prefix}-{N:02d}-{slug}.md``. An ``index.md`` file is created
    listing the chapters with hyperlinks. Optionally exports images
    and inserts a cover banner in the index. Returns the path to the
    index and the number of chapters created.

    Args:
        epub_path: Path to the input EPUB file.
        outdir: Output directory where chapter files and assets will
                be saved.
        prefix: Filename prefix for chapter files.
        imgdir: Name of the subdirectory for exported images.
        extract_images: Whether to export images.
        cover_banner: Whether to include a cover in the index.

    Returns:
        A tuple ``(index_path, chapter_count)``.
    """
    os.makedirs(outdir, exist_ok=True)
    book = epub.read_epub(epub_path)
    converter = html_to_markdown_converter()
    image_map: Dict[str, str] = {}
    if extract_images:
        image_map = export_images(book, outdir, imgdir=imgdir)
    index_lines = []
    chapter_num = 1
    for item in iter_spine_items(book):
        html = item.get_content().decode("utf-8", errors="ignore")
        if image_map:
            html = rewrite_img_paths_in_html(html, image_map)
        title = extract_title_from_html(html) or f"Chapitre {chapter_num}"
        base_slug = slugify(title, fallback=f"{prefix}-{chapter_num:02d}")
        md_filename = f"{prefix}-{chapter_num:02d}-{base_slug}.md"
        md_path = os.path.join(outdir, md_filename)
        md = converter.handle(html)
        with open(md_path, "w", encoding="utf-8") as f:
            if not re.search(r"^#\s", md.lstrip(), flags=re.M):
                f.write(f"# {title}\n\n")
            f.write(md)
        index_lines.append(f"- [{title}]({md_filename})")
        chapter_num += 1
    book_title_meta = book.get_metadata("DC", "title")
    book_title = (
        book_title_meta[0][0]
        if book_title_meta
        else os.path.splitext(os.path.basename(epub_path))[0]
    )
    index_path = os.path.join(outdir, "index.md")
    with open(index_path, "w", encoding="utf-8") as idx:
        idx.write(f"# {book_title}\n\n")
        if cover_banner and image_map:
            cover_rel = None
            for rel in image_map.values():
                if os.path.basename(rel).lower().startswith("cover."):
                    cover_rel = rel
                    break
            if cover_rel:
                idx.write(f"![]({cover_rel})\n\n")
        idx.write("\n".join(index_lines) + "\n")
    return index_path, chapter_num - 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Convert an EPUB to Markdown. "
            "Supports single file or chapter split outputs, image "
            "extraction, and cover detection."
        )
    )
    parser.add_argument("input", help="EPUB file to convert")
    parser.add_argument(
        "output",
        nargs="?",
        help="Output Markdown file (single output mode). If omitted in single mode, a name based on the input file is used.",
    )
    parser.add_argument(
        "--split",
        action="store_true",
        help="Split output into chapter files and generate an index",
    )
    parser.add_argument(
        "--outdir",
        default="md_chapitres",
        help="Output directory when using --split (default: md_chapitres)",
    )
    parser.add_argument(
        "--prefix",
        default="chapitre",
        help="Prefix for chapter files when using --split (default: chapitre)",
    )
    parser.add_argument(
        "--imgdir",
        default="images",
        help="Subdirectory name for exported images (default: images)",
    )
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="Disable image extraction and path rewriting",
    )
    parser.add_argument(
        "--no-cover-banner",
        action="store_true",
        help="Do not insert the cover image at the top of the Markdown or index",
    )
    args = parser.parse_args()
    if not os.path.exists(args.input):
        print(f"Erreur : fichier introuvable : {args.input}", file=sys.stderr)
        sys.exit(1)
    extract_images = not args.no_images
    cover_banner = not args.no_cover_banner
    if args.split:
        index_path, count = convert_epub_to_split_md(
            epub_path=args.input,
            outdir=args.outdir,
            prefix=args.prefix,
            imgdir=args.imgdir,
            extract_images=extract_images,
            cover_banner=cover_banner,
        )
        print(f"✅ {count} chapitres générés dans '{args.outdir}'.")
        if extract_images:
            print(f"🖼️  Images exportées dans : {os.path.join(args.outdir, args.imgdir)}")
        print(f"📑 Sommaire : {index_path}")
    else:
        output_path = args.output
        if not output_path:
            base = os.path.splitext(os.path.basename(args.input))[0]
            output_path = base + ".md"
        convert_epub_to_single_md(
            epub_path=args.input,
            md_path=output_path,
            imgdir=args.imgdir,
            extract_images=extract_images,
            cover_banner=cover_banner,
        )
        print(f"✅ Conversion terminée : {output_path}")
        if extract_images:
            outdir = os.path.dirname(os.path.abspath(output_path)) or "."
            print(f"🖼️  Images exportées dans : {os.path.join(outdir, args.imgdir)}")


if __name__ == "__main__":
    main()