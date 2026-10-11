"""Physical PDF pages and real source headings; unpaginated sources stay explicit."""

import re
import statistics
from dataclasses import dataclass, field
from pathlib import Path

PARSER_VERSION = 3


@dataclass
class Page:
    number: int
    text: str
    sections: list = field(default_factory=list)
    tables: list = field(default_factory=list)
    is_ocr: bool = False
    is_logical: bool = False


def table_markdown(rows):
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    clean = []
    for row in rows:
        cells = [re.sub(r"\s+", " ", str(cell or "")).replace("|", r"\|").strip() for cell in row]
        clean.append("| " + " | ".join(cells + [""] * (width - len(cells))) + " |")
    return "\n".join([clean[0], "| " + " | ".join(["---"] * width) + " |", *clean[1:]])


def parse_pdf(path):
    import pdfplumber
    import pymupdf as fitz

    result = []
    current_title = ""
    with fitz.open(path) as pdf, pdfplumber.open(path) as tables_pdf:
        for number, source in enumerate(pdf, 1):
            plain = source.get_text("text", sort=True)
            ocr = len(re.sub(r"[^A-Za-z0-9]", "", plain)) < 40
            if ocr:
                textpage = source.get_textpage_ocr(
                    language="eng",
                    dpi=180,
                    full=True,
                    tessdata="/usr/share/tesseract-ocr/5/tessdata",
                )
                plain = source.get_text("text", textpage=textpage, sort=True)
                blocks = source.get_text("dict", textpage=textpage, sort=True)["blocks"]
            else:
                blocks = source.get_text("dict", sort=True)["blocks"]
            extracted, table_boxes = [], []
            if not ocr:
                for table in tables_pdf.pages[number - 1].find_tables():
                    rows = table.extract()
                    # Underlined prose can look like a one-column grid. Its
                    # text/subscripts must remain in natural prose order.
                    if not rows or max(len(row) for row in rows) < 2:
                        continue
                    markdown = table_markdown(rows)
                    if markdown:
                        extracted.append({"title": current_title, "text": markdown})
                        table_boxes.append(table.bbox)
            lines = [line for block in blocks if "lines" in block for line in block["lines"]]
            # Table cells are separate evidence; their bold/numeric labels must
            # not be mistaken for hundreds of new prose section headings.
            prose = []
            for line in lines:
                x0, y0, x1, y1 = line["bbox"]
                x, y = (x0 + x1) / 2, (y0 + y1) / 2
                if not any(a <= x <= c and b <= y <= d for a, b, c, d in table_boxes):
                    prose.append(line)
            lines = prose
            sizes = [
                span["size"]
                for line in lines
                for span in line["spans"]
                for _ in range(min(100, len(span["text"].strip())))
            ]
            body_size = statistics.median(sizes) if sizes else 10
            sections = []
            collected = []
            for line in lines:
                text = "".join(span["text"] for span in line["spans"]).strip()
                if not text:
                    continue
                size = max(span["size"] for span in line["spans"])
                bold = all(span.get("flags", 0) & 16 for span in line["spans"])
                numbered = bool(re.match(r"^\d+(?:\.\d+)*[.]?\s+[A-Z][A-Za-z]", text))
                short = len(text.split()) <= 12 and len(text) <= 120
                ends_sentence = text.endswith((".", ";", ","))
                typography = not ocr and (size > body_size * 1.2 or bold)
                ocr_heading = ocr and text.isupper() and len(re.sub("[^A-Z]", "", text)) >= 5
                heading = (
                    short
                    and not text.isdigit()
                    and not ends_sentence
                    and (typography or numbered or ocr_heading)
                )
                if heading:
                    if collected:
                        sections.append({"title": current_title, "text": "\n".join(collected)})
                    current_title, collected = text, [text]
                else:
                    collected.append(text)
            if collected:
                sections.append({"title": current_title, "text": "\n".join(collected)})
            if not sections and plain.strip():
                sections = [{"title": current_title, "text": plain}]
            for table in extracted:
                table["title"] = current_title
            result.append(Page(number, plain, sections, extracted, ocr))
            # pdfplumber otherwise retains every page's character/graphics cache
            # for the entire 560-page report, unnecessarily exhausting host RAM.
            tables_pdf.pages[number - 1].close()
    return result


def parse_html(path):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(Path(path).read_text(encoding="utf-8", errors="replace"), "html.parser")
    for element in soup.select("script,style,nav,footer,header,noscript,form"):
        element.decompose()
    article = (
        soup.find("article")
        or soup.find("main")
        or soup.find(id="main-content")
        or soup.body
        or soup
    )
    plain = article.get_text("\n", strip=True)
    sections, tables, collected = [], [], []
    title = ""
    for element in article.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "table"]):
        if element.find_parent("table") or (element.name == "li" and element.find("p")):
            continue
        text = element.get_text(" ", strip=True)
        if element.name.startswith("h"):
            if collected:
                sections.append({"title": title, "text": "\n".join(collected)})
            title, collected = text, [text]
        elif element.name == "table":
            rows = [
                [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
                for row in element.find_all("tr")
            ]
            markdown = table_markdown(rows)
            if markdown:
                tables.append({"title": title, "text": markdown})
        elif text:
            collected.append(text)
    if collected:
        sections.append({"title": title, "text": "\n".join(collected)})
    if not sections and plain:
        sections = [{"title": "", "text": plain}]
    return [Page(1, plain, sections, tables, is_logical=True)]


def parse_markdown(path):
    from markdown_it import MarkdownIt

    source = Path(path).read_text(encoding="utf-8")
    tokens = MarkdownIt("commonmark").enable("table").parse(source)
    sections, tables, collected = [], [], []
    title = ""
    lines = source.splitlines()
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.type == "heading_open":
            if collected:
                sections.append({"title": title, "text": "\n".join(collected)})
            title = tokens[index + 1].content
            collected = [title]
        elif token.type == "table_open":
            first, last = token.map
            tables.append({"title": title, "text": "\n".join(lines[first:last])})
            while index < len(tokens) and tokens[index].type != "table_close":
                index += 1
        elif token.type in {"inline", "fence", "code_block"}:
            if index == 0 or tokens[index - 1].type != "heading_open":
                collected.append(token.content)
        index += 1
    if collected:
        sections.append({"title": title, "text": "\n".join(collected)})
    return [Page(1, source, sections, tables, is_logical=True)]


def parse_source(path, source_format):
    parsers = {"pdf": parse_pdf, "html": parse_html, "markdown": parse_markdown}
    if source_format not in parsers:
        raise ValueError("Unsupported document format")
    return parsers[source_format](path)
