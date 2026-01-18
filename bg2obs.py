#!/usr/bin/env python3
import argparse
import html
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser


BOOK_CHAPTERS = [
    50, 40, 27, 36, 34, 24, 21, 4, 31, 24, 22, 25, 29, 36, 10, 13, 10, 42,
    150, 31, 12, 8, 66, 52, 5, 48, 12, 14, 3, 9, 1, 4, 7, 3, 3, 3, 2, 14,
    4, 28, 16, 24, 21, 28, 16, 16, 13, 6, 6, 4, 4, 5, 3, 6, 4, 3, 1, 13,
    5, 5, 3, 5, 1, 1, 1, 22,
]

PASSAGE_CLASSES = {"passage-text"}
FOOTNOTE_CONTAINER_CLASSES = {"footnotes"}
FOOTNOTE_CONTAINER_IDS = {"footnotes"}
IGNORE_CLASSES = {
    "crossreference",
    "crossref",
    "crossrefs",
    "crossref-block",
    "crossref-list",
    "footnotes",
    "footnote-text",
    "footnote-ref",
    "translation-note",
    "publisher-info-bottom",
    "passage-other-trans",
    "passage-parallel",
    "passage-related",
    "passage-display",
}
SKIP_TAGS = {"script", "style", "noscript"}
BSB_VERSION = "BSB"


def show_help():
    print("Usage: bg2obs.py [-sbeaicyh] [-v version] [-l language] [--book BOOK] [--chapter N] [--list-versions] [--footnotes] [--abbr]")
    print("  -v version   Specify the Bible version to download (default = WEB)")
    print("  -s           If available, use shorter book abbreviations")
    print("  -b           Set words of Jesus in bold")
    print("  -e           Include editorial headers")
    print("  -a           Create an alias in the YAML front matter for each chapter title")
    print("  -i           Show download information (i.e. verbose mode)")
    print("  -c           Include inline navigation for the breadcrumbs plugin (e.g. 'up', 'next','previous')")
    print("  -y           Print navigation for the breadcrumbs plugin in the frontmatter (YAML)")
    print("  -l           Which language to use for file names, links, and titles")
    print("  --book       Limit download to a single book (use locale spelling or abbreviation)")
    print("  --chapter    Limit download to a single chapter (requires --book)")
    print("  --list-versions  List available version abbreviations from BibleGateway")
    print("  --footnotes  Include footnotes in the text and footer")
    print("  --abbr       Use medium-length abbreviations for filenames (booksAbbr.txt)")
    print("  -h           Display help")


class BibleGatewayParser(HTMLParser):
    def __init__(self, include_headers, bold_words, include_footnotes):
        super().__init__()
        self.include_headers = include_headers
        self.bold_words = bold_words
        self.include_footnotes = include_footnotes
        self.passage_depth = 0
        self.skip_depth = 0
        self.woj_depth = 0
        self.in_versenum = False
        self.versenum_buf = []
        self.in_chapternum = False
        self.chapternum_buf = []
        self.skip_next_versenum = None
        self.in_heading = False
        self.heading_buf = []
        self.in_footnote_ref = False
        self.footnote_ref_buf = []
        self.footnote_ref_id = None
        self.footnote_ref_map = {}
        self.used_labels = set()
        self.out = []

    def _classes(self, attrs):
        for k, v in attrs:
            if k == "class" and v:
                return set(v.split())
        return set()

    def _start_passage(self, tag, classes):
        if self.passage_depth == 0 and tag == "div" and classes & PASSAGE_CLASSES:
            self.passage_depth = 1
            return True
        return False

    def _append(self, text):
        if text:
            self.out.append(text)

    def handle_starttag(self, tag, attrs):
        classes = self._classes(attrs)
        if self._start_passage(tag, classes):
            return

        if self.passage_depth == 0:
            return

        self.passage_depth += 1

        if self.skip_depth > 0:
            self.skip_depth += 1
            return

        if tag in SKIP_TAGS:
            self.skip_depth = 1
            return

        if classes & IGNORE_CLASSES or any("crossref" in c for c in classes):
            self.skip_depth = 1
            return

        if self.woj_depth > 0:
            self.woj_depth += 1

        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.in_heading = True
            self.heading_buf = []
            return

        if tag in {"sup", "span"} and "versenum" in classes:
            self.in_versenum = True
            self.versenum_buf = []
            return

        if tag in {"sup", "span"} and "chapternum" in classes:
            self.in_chapternum = True
            self.chapternum_buf = []
            return

        if tag == "sup" and "footnote" in classes:
            if not self.include_footnotes:
                self.skip_depth = 1
                return
            self.in_footnote_ref = True
            self.footnote_ref_buf = []
            self.footnote_ref_id = None
            for k, v in attrs:
                if k == "data-fn" and v:
                    self.footnote_ref_id = v.lstrip("#")
                    break
            return

        if self.bold_words and "woj" in classes:
            self.woj_depth = 1
            self._append("**")

        if tag == "br":
            self._append("\n")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self.passage_depth == 0:
            return

        if self.skip_depth > 0:
            self.skip_depth -= 1
            self.passage_depth -= 1
            return

        if self.in_heading and tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.in_heading = False
            if self.include_headers:
                heading = "".join(self.heading_buf).strip()
                if heading:
                    self._append("\n\n##### " + heading + "\n")
            self.passage_depth -= 1
            return

        if self.in_versenum and tag in {"sup", "span"}:
            self.in_versenum = False
            num = "".join(self.versenum_buf).strip()
            if num and self.skip_next_versenum == num:
                self.skip_next_versenum = None
            elif num:
                self._append("\n\n###### " + num + "\n")
            self.passage_depth -= 1
            return

        if self.in_chapternum and tag in {"sup", "span"}:
            self.in_chapternum = False
            num = "1"
            self._append("\n\n###### " + num + "\n")
            self.skip_next_versenum = num
            self.passage_depth -= 1
            return

        if self.in_footnote_ref and tag == "sup":
            self.in_footnote_ref = False
            label = "".join(self.footnote_ref_buf)
            label = re.sub(r"[^A-Za-z0-9]+", "", label).lower()
            label = self._register_label(label)
            if self.footnote_ref_id:
                self.footnote_ref_map[self.footnote_ref_id] = label
            self._append(f"[^{label}]")
            self.footnote_ref_buf = []
            self.footnote_ref_id = None
            self.passage_depth -= 1
            return

        if self.woj_depth > 0:
            self.woj_depth -= 1
            if self.woj_depth == 0 and self.bold_words:
                self._append("**")

        if tag == "p":
            self._append("\n\n")

        self.passage_depth -= 1

    def handle_data(self, data):
        if self.passage_depth == 0 or self.skip_depth > 0:
            return

        if self.in_versenum:
            self.versenum_buf.append(data)
            return

        if self.in_chapternum:
            self.chapternum_buf.append(data)
            return

        if self.in_heading:
            self.heading_buf.append(data)
            return

        if self.in_footnote_ref:
            self.footnote_ref_buf.append(data)
            return

        self._append(data)

    def _register_label(self, label):
        if not label:
            label = str(len(self.used_labels) + 1)
        original = label
        suffix = 1
        while label in self.used_labels:
            suffix += 1
            label = f"{original}{suffix}"
        self.used_labels.add(label)
        return label

class FootnoteParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_container = False
        self.container_depth = 0
        self.in_item = False
        self.item_depth = 0
        self.item_buf = []
        self.footnotes = []
        self.item_id = None
        self.in_anchor = False
        self.ref_buf = []
        self.in_note_text = False
        self.note_buf = []

    def _classes(self, attrs):
        for k, v in attrs:
            if k == "class" and v:
                return set(v.split())
        return set()

    def _has_id(self, attrs, ids):
        for k, v in attrs:
            if k == "id" and v in ids:
                return True
        return False

    def handle_starttag(self, tag, attrs):
        classes = self._classes(attrs)
        if not self.in_container and tag == "div":
            if classes & FOOTNOTE_CONTAINER_CLASSES or self._has_id(attrs, FOOTNOTE_CONTAINER_IDS):
                self.in_container = True
                self.container_depth = 1
                return

        if not self.in_container:
            return

        if tag in SKIP_TAGS:
            return

        self.container_depth += 1

        if self.in_item:
            self.item_depth += 1
            if tag == "a" and not self.ref_buf:
                self.in_anchor = True
            if tag == "span" and "footnote-text" in classes:
                self.in_note_text = True
            return

        if tag == "li" or ("footnote-text" in classes) or (tag == "div" and "footnote" in classes):
            self._start_item(attrs)
            return

        if tag == "a" and self.in_item and not self.ref_buf:
            self.in_anchor = True

    def _start_item(self, attrs):
        if self.in_item:
            return
        self.in_item = True
        self.item_depth = 1
        self.item_buf = []
        self.ref_buf = []
        self.note_buf = []
        self.item_id = None
        for k, v in attrs:
            if k == "id" and v:
                self.item_id = v
                break

    def handle_endtag(self, tag):
        if not self.in_container:
            return

        if self.in_item:
            self.item_depth -= 1
            if tag == "a" and self.in_anchor:
                self.in_anchor = False
            if tag == "span" and self.in_note_text:
                self.in_note_text = False
            if self.item_depth == 0:
                ref = "".join(self.ref_buf).strip()
                note = "".join(self.note_buf).strip() or "".join(self.item_buf).strip()
                if note:
                    self.footnotes.append((self.item_id, ref, note))
                self.in_item = False
                self.item_buf = []
                self.ref_buf = []
                self.note_buf = []
                self.item_id = None
        self.container_depth -= 1
        if self.container_depth == 0:
            self.in_container = False

    def handle_data(self, data):
        if self.in_item:
            self.item_buf.append(data)
            if self.in_anchor:
                self.ref_buf.append(data)
            if self.in_note_text:
                self.note_buf.append(data)


def normalize_markdown(text):
    text = html.unescape(text)
    text = text.replace("\u00a0", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def fetch_passage(book, chapter, version):
    search = f"{book}{chapter}"
    params = {
        "search": search,
        "version": version,
        "print": "yes",
    }
    url = "https://www.biblegateway.com/passage/?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "bg2obs.py (https://github.com/selfire1/BibleGateway-to-Obsidian)"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def load_bsb_index(bsb_path):
    index = {}
    with open(bsb_path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("The Holy Bible") or line.startswith("This text"):
                continue
            if line.startswith("Verse\t"):
                continue
            match = re.match(r"^(.+?)\s+(\d+):(\d+)\t(.*)$", line)
            if not match:
                continue
            book, chapter, verse, text = match.groups()
            if book == "Psalm":
                book = "Psalms"
            chapter_num = int(chapter)
            verse_num = int(verse)
            index.setdefault(book, {}).setdefault(chapter_num, {})[verse_num] = text.strip()
    return index


def build_bsb_chapter_content(book, chapter, bsb_index):
    verses = bsb_index.get(book, {}).get(chapter, {})
    if not verses:
        return ""
    lines = []
    for verse_num in sorted(verses.keys()):
        lines.append(f"###### {verse_num}")
        lines.append(verses[verse_num])
        lines.append("")
    return "\n".join(lines).strip()


def parse_passage(html_text, include_headers, bold_words, include_footnotes):
    parser = BibleGatewayParser(
        include_headers=include_headers,
        bold_words=bold_words,
        include_footnotes=include_footnotes,
    )
    parser.feed(html_text)
    parser.close()
    content = normalize_markdown("".join(parser.out))

    footnotes = []
    footnote_map = {}
    if include_footnotes:
        footnote_parser = FootnoteParser()
        footnote_parser.feed(html_text)
        footnote_parser.close()
        for item_id, ref, note in footnote_parser.footnotes:
            cleaned_ref = normalize_markdown(ref)
            cleaned_note = normalize_markdown(note)
            if cleaned_note:
                footnotes.append((item_id, cleaned_ref, cleaned_note))
        footnote_map = parser.footnote_ref_map
    return content, footnotes, footnote_map


def load_lines(path):
    with open(path, "r", encoding="utf-8") as handle:
        return [line.strip() for line in handle if line.strip()]


def show_progress_bar(title, completed, total, start_new_line, title_max):
    percentage = (completed * 100) // total
    bar_width = percentage // 5
    bar = "#" * bar_width
    bar = bar.ljust(20, " ")
    title = title.rjust(title_max, " ")
    completed_str = str(completed).rjust(2, "0")
    total_str = str(total).rjust(2, "0")
    progress_bar = f"{title} -- Chapter {completed_str} of {total_str} -- |{bar}| {percentage}%"
    if start_new_line:
        sys.stdout.write("\n" + progress_bar)
    else:
        sys.stdout.write("\r" + progress_bar)
    sys.stdout.flush()

class VersionParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_option = False
        self.current_value = None
        self.current_text = []
        self.versions = []

    def handle_starttag(self, tag, attrs):
        if tag != "option":
            return
        value = None
        for k, v in attrs:
            if k == "value" and v:
                value = v.strip()
                break
        if value:
            self.in_option = True
            self.current_value = value
            self.current_text = []

    def handle_endtag(self, tag):
        if tag != "option" or not self.in_option:
            return
        label = "".join(self.current_text).strip()
        if self.current_value:
            self.versions.append((self.current_value, label))
        self.in_option = False
        self.current_value = None
        self.current_text = []

    def handle_data(self, data):
        if self.in_option:
            self.current_text.append(data)


def fetch_versions():
    url = "https://www.biblegateway.com/versions/"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "bg2obs.py (https://github.com/selfire1/BibleGateway-to-Obsidian)"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        html_text = resp.read().decode("utf-8", errors="replace")

    parser = VersionParser()
    parser.feed(html_text)
    parser.close()
    versions = parser.versions
    if not versions:
        versions = re.findall(r'value="([A-Z0-9]{2,})"', html_text)
        versions = [(v, "") for v in versions]
    return versions


def print_versions():
    try:
        versions = fetch_versions()
    except Exception as exc:
        print(f"Failed to fetch versions: {exc}")
        return 1

    if not versions:
        print("No versions found.")
        return 1

    seen = set()
    versions = sorted(versions, key=lambda item: item[0].upper())
    for code, name in versions:
        if code in seen:
            continue
        seen.add(code)
        label = f"{code} - {name}" if name else code
        print(label)
    return 0


def normalize_key(value):
    return re.sub(r"[^a-z0-9]", "", value.lower())


def resolve_book_index(book_name, book_array, abbr_array):
    target = normalize_key(book_name)
    for idx, name in enumerate(book_array):
        if normalize_key(name) == target:
            return idx
    for idx, abbr in enumerate(abbr_array):
        if normalize_key(abbr) == target:
            return idx
    return None


def format_footnotes(footnotes, footnote_map, book, chapter, abbreviation):
    if not footnotes:
        return ""
    lines = ["---", "", "##### Footnotes", ""]
    for item_id, ref, note in footnotes:
        label = footnote_map.get(item_id)
        if not label:
            label = re.sub(r"[^A-Za-z0-9]+", "", ref).lower()
            if not label:
                label = str(len(lines))
        ref_match = re.search(r"(\d+)\s*:\s*(\d+)", ref)
        link_text = ref.strip() or f"{book} {chapter}"
        link_target = f"{abbreviation} {chapter}#1"
        if ref_match:
            ref_chapter = ref_match.group(1)
            ref_verse = ref_match.group(2)
            link_target = f"{abbreviation} {ref_chapter}#{ref_verse}"
            if not ref.strip():
                link_text = f"{book} {ref_chapter}:{ref_verse}"
        link = f"[[{link_target}|{link_text}]]"
        lines.append(f"[^{label}]: {link} {note}")
    return "\n\n" + "\n".join(lines)


def remove_crossref_lines(text, book, chapter):
    pattern = re.compile(rf"^{re.escape(book)}\s+{chapter}\s*:\s*\d+\s*:", re.IGNORECASE)
    next_pattern = re.compile(rf"^{re.escape(book)}\s+\d+Next$", re.IGNORECASE)
    noise = re.compile(r"(freestar|Buy Now|Our Price|Retail:|View more titles|dropdown)", re.IGNORECASE)
    kept = []
    for line in text.splitlines():
        normalized = line.replace("\u00a0", " ")
        compact = re.sub(r"\s+", " ", normalized).strip()
        if pattern.match(compact):
            continue
        if next_pattern.match(compact):
            continue
        if noise.search(compact):
            continue
        kept.append(compact)
    return "\n".join(kept).strip()


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-v", dest="version", default="WEB")
    parser.add_argument("-s", dest="abbr_short", action="store_true")
    parser.add_argument("-b", dest="bold_words", action="store_true")
    parser.add_argument("-e", dest="include_headers", action="store_true")
    parser.add_argument("-a", dest="aliases", action="store_true")
    parser.add_argument("-i", dest="verbose", action="store_true")
    parser.add_argument("-c", dest="bc_inline", action="store_true")
    parser.add_argument("-y", dest="bc_yaml", action="store_true")
    parser.add_argument("-l", dest="language", default="en")
    parser.add_argument("-h", dest="help", action="store_true")
    parser.add_argument("--book", dest="book")
    parser.add_argument("--chapter", dest="chapter", type=int)
    parser.add_argument("--list-versions", dest="list_versions", action="store_true")
    parser.add_argument("--footnotes", dest="footnotes", action="store_true")
    parser.add_argument("--abbr", dest="abbr_medium", action="store_true")
    args = parser.parse_args()

    if args.help:
        show_help()
        return 0

    args.version = args.version.upper()

    if args.list_versions:
        return print_versions()

    print(
        f"I confirm that I have checked and understand the copyright/license "
        f"conditions for {args.version} and wish to continue downloading it in its entirety?"
    )
    response = input("Type 'yes' to continue: ").strip().lower()
    if response not in {"yes", "y"}:
        return 1

    translation_folder = os.path.join("locales", args.language)
    bible_name_path = os.path.join(translation_folder, "name.txt")
    if not os.path.exists(bible_name_path):
        print("Language not found!")
        return 1

    bible_name = load_lines(bible_name_path)[0]
    book_array = load_lines(os.path.join(translation_folder, "books.txt"))
    abbr_medium_array = load_lines(os.path.join(translation_folder, "booksAbbr.txt"))
    abbr_short_array = load_lines(os.path.join(translation_folder, "booksAbbrShort.txt"))
    bsb_path = os.path.join(translation_folder, "bsb.txt")

    if len(book_array) != 66 or len(abbr_medium_array) != 66 or len(abbr_short_array) != 66:
        print("Locale files must include 66 books and abbreviations.")
        return 1

    if args.abbr_short:
        abbr_array = abbr_short_array
    elif args.abbr_medium:
        abbr_array = abbr_medium_array
    else:
        abbr_array = book_array

    if args.chapter is not None and not args.book:
        print("--chapter requires --book.")
        return 1

    book_indices = list(range(66))
    if args.book:
        book_index = resolve_book_index(args.book, book_array, abbr_array)
        if book_index is None:
            print(f"Book not found: {args.book}")
            return 1
        book_indices = [book_index]

    title_max = max(len(title) for title in book_array) if args.verbose else 0
    bible_folder = f"{bible_name} ({args.version})"

    with open(f"{bible_name}.md", "w", encoding="utf-8") as main_index:
        main_index.write(f"# {bible_folder}")

    if args.verbose:
        print(f"Starting download of {args.version} Bible.", end="")

    bsb_index = None
    use_bsb = args.version == BSB_VERSION and os.path.exists(bsb_path)
    if use_bsb:
        bsb_index = load_bsb_index(bsb_path)

    for book_index in book_indices:
        book = book_array[book_index]
        last_chapter = BOOK_CHAPTERS[book_index]
        abbreviation = abbr_array[book_index]
        if args.chapter is not None:
            if args.chapter < 1 or args.chapter > last_chapter:
                print(f"Chapter out of range for {book}: {args.chapter}")
                return 1
            chapters_to_download = [args.chapter]
        else:
            chapters_to_download = list(range(1, last_chapter + 1))

        if args.verbose:
            show_progress_bar(book, 0, chapters_to_download[-1], True, title_max)

        with open(f"{bible_name}.md", "a", encoding="utf-8") as main_index:
            main_index.write(f"\n* {book}:")

        for idx, chapter in enumerate(chapters_to_download):
            prev_chapter = chapters_to_download[idx - 1] if idx > 0 else None
            next_chapter = (
                chapters_to_download[idx + 1] if idx + 1 < len(chapters_to_download) else None
            )

            this_file = f"{abbreviation} {chapter}"
            prev_file = f"{abbreviation} {prev_chapter}" if prev_chapter else None
            next_file = f"{abbreviation} {next_chapter}" if next_chapter else None

            with open(f"{bible_name}.md", "a", encoding="utf-8") as main_index:
                main_index.write(f" [[{this_file}|{chapter}]]")

            if use_bsb:
                chapter_content = build_bsb_chapter_content(book, chapter, bsb_index)
                footnotes = []
                footnote_map = {}
            else:
                book_no_spaces = book.replace(" ", "")
                html_text = fetch_passage(book_no_spaces, chapter, args.version)
                chapter_content, footnotes, footnote_map = parse_passage(
                    html_text,
                    include_headers=args.include_headers,
                    bold_words=args.bold_words,
                    include_footnotes=args.footnotes,
                )

            if not chapter_content:
                print(f"\nFailed to download {book} {chapter}.")
                return 1
            if not use_bsb:
                chapter_content = remove_crossref_lines(chapter_content, book, chapter)

            if not args.bc_inline and not args.bc_yaml:
                navigation = f"[[{book}]]"
                if prev_chapter:
                    navigation = f"[[{prev_file}|< {book} {prev_chapter}]] | " + navigation
                if next_chapter:
                    navigation = navigation + f" | [[{next_file}|{book} {next_chapter} >]]"
            else:
                navigation = f"(up:: [[{book}]])"
                if prev_chapter:
                    navigation = f"(previous:: [[{prev_file}|< {book} {prev_chapter}]]) | " + navigation
                if next_chapter:
                    navigation = navigation + f" | (next:: [[{next_file}|{book} {next_chapter} >]])"

            if args.footnotes:
                chapter_content = chapter_content + format_footnotes(
                    footnotes, footnote_map, book, chapter, abbreviation
                )
            title = f"# {book} {chapter}"
            yaml_needed = args.bc_yaml or args.aliases
            if args.bc_yaml:
                chapter_body = f"{title}\n\n***\n{chapter_content}"
            else:
                chapter_body = f"{title}\n\n{navigation}\n\n***\n{chapter_content}"

            if yaml_needed:
                yaml_lines = ["---"]
                if args.aliases:
                    alias_long = f"{book} {chapter}"
                    alias_med = f"{abbr_medium_array[book_index]} {chapter}"
                    alias_short = f"{abbr_short_array[book_index]} {chapter}"
                    aliases = []
                    for alias in (alias_long, alias_med, alias_short):
                        if alias not in aliases:
                            aliases.append(alias)
                    if len(aliases) > 1:
                        yaml_lines.append(f"aliases: [{', '.join(aliases)}]")
                if args.bc_yaml:
                    if prev_chapter:
                        yaml_lines.append(f"previous: ['{prev_file}']")
                    yaml_lines.append(f"up: ['{book}']")
                    if next_chapter:
                        yaml_lines.append(f"next: ['{next_file}']")
                yaml_lines.append("---\n\n")
                chapter_body = "\n".join(yaml_lines) + chapter_body

            out_dir = os.path.join(bible_folder, book)
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, f"{this_file}.md")
            with open(out_path, "w", encoding="utf-8") as handle:
                handle.write(chapter_body)

            if args.verbose:
                show_progress_bar(book, chapter, chapters_to_download[-1], False, title_max)
            time.sleep(0.2)

        first_chapter = chapters_to_download[0]
        overview_file = f"links: [[{bible_name}]]\n# {book}\n\n[[{abbreviation} {first_chapter}|Start Reading >]]"
        overview_path = os.path.join(bible_folder, book, f"{book}.md")
        with open(overview_path, "w", encoding="utf-8") as handle:
            handle.write(overview_file)

    if args.verbose:
        print("\nDownload complete. Markdown files ready for Obsidian import.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
