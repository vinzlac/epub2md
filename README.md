# epub2md

`epub2md` is a simple yet powerful command‑line tool for converting
EPUB ebooks into Markdown.  It can generate a single Markdown file or
break the book into multiple chapter files, extract images (including
the cover), and maintain the original reading order defined by the
EPUB spine.

## Features

- **Single or multi‑file output** – produce one `.md` file or split
  the output into per‑chapter files with an automatic table of
  contents (`index.md`).
- **Image extraction** – copy all images from the EPUB into a
  dedicated folder and update references in the Markdown.  The book
  cover is detected automatically and renamed to `cover.ext`.
- **Cover banner** – optionally insert the cover image at the top of
  the generated Markdown or index for quick visual context.
- **Robust spine handling** – respects the EPUB spine to preserve the
  intended reading order; falls back to sensible defaults if the
  spine is missing.
- **Clean Markdown output** – converts HTML to Markdown without
  wrapping lines and preserves links and images.
- **Flexible CLI** – configure output paths, prefixes, image
  directories, and disable features (image extraction, cover banner)
  via command‑line flags.

## Requirements

- Python 3.7 or later
- pip packages: [ebooklib](https://pypi.org/project/ebooklib/),
  [html2text](https://pypi.org/project/html2text/),
  [beautifulsoup4](https://pypi.org/project/beautifulsoup4/)

Install the dependencies with:

```sh
pip install ebooklib html2text beautifulsoup4
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

## Usage

```sh
python epub2md.py input.epub [output.md]

python epub2md.py input.epub --split [--outdir OUTDIR]
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

Split the book into chapters, store everything in `out_md/`, and
prefix files with `part`:

```sh
python epub2md.py alice.epub --split --outdir out_md --prefix part
```

## License

This project is released under the [MIT License](https://opensource.org/licenses/MIT).  See the
`LICENSE` file for details.

---

Feel free to contribute or open issues if you encounter any problems
or have ideas for improvements.  Happy reading! 📚