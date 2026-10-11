"""Token-budget chunks retaining source slices, section labels and page provenance."""

import re


def window_chunks(fragments, tokenizer, is_table=False):
    text, boundaries = "", []
    for page, fragment in fragments:
        start = len(text)
        text += fragment + "\n"
        boundaries.append((start, len(text), page))
    encoded = tokenizer(text, add_special_tokens=False, return_offsets_mapping=True)
    offsets = encoded["offset_mapping"]
    result = []
    start = 0
    header = "\n".join(text.splitlines()[:2]) + "\n" if is_table else ""
    header_tokens = len(tokenizer(header, add_special_tokens=False)["input_ids"]) if header else 0
    if header_tokens > 300:
        # A wide table header can itself exceed the fragment budget. Keep the
        # original header in its first chunk instead of repeating an oversize prefix.
        header, header_tokens = "", 0
    while start < len(offsets):
        prefix = header if start and is_table else ""
        maximum = max(100, 800 - (header_tokens if prefix else 0))
        stop = min(start + min(700, maximum), len(offsets))
        if stop < len(offsets):
            # Prefer a source paragraph/row boundary after 500 tokens, below 800.
            ceiling = min(start + maximum, len(offsets))
            choices = [
                i
                for i in range(start + 500, min(ceiling, len(offsets) - 1))
                if "\n" in text[offsets[i][1] : offsets[i + 1][0]]
            ]
            if choices:
                stop = min(choices, key=lambda i: abs(i - (start + 650))) + 1
        first_char, last_char = offsets[start][0], offsets[stop - 1][1]
        piece = prefix + text[first_char:last_char]
        pages = [
            page for first, last, page in boundaries if first < last_char and last > first_char
        ]
        result.append(
            {
                "text": piece,
                "page_start": min(pages),
                "page_end": max(pages),
                "token_count": stop - start + (header_tokens if prefix else 0),
                "is_table": is_table,
            }
        )
        if stop == len(offsets):
            break
        start = max(start + 1, stop - 100)
    return result


def chunk_pages(pages, tokenizer):
    chunks = []
    title, fragments = None, []

    def flush():
        for chunk in window_chunks(fragments, tokenizer):
            chunks.append({**chunk, "section_title": title or ""})

    for page in pages:
        for section in page.sections:
            if title is not None and section["title"] != title:
                flush()
                fragments = []
            title = section["title"]
            fragments.append((page.number, section["text"]))
    if fragments:
        flush()
    for page in pages:
        for table in page.tables:
            for chunk in window_chunks([(page.number, table["text"])], tokenizer, is_table=True):
                chunks.append({**chunk, "section_title": table["title"]})
    logical = bool(pages and pages[0].is_logical)
    return [
        {**chunk, "chunk_index": index, "is_logical_page": logical}
        for index, chunk in enumerate(chunks)
    ]


def mentions(text, cities, pollutants):
    folded = text.casefold()
    city_matches = [
        slug
        for slug, name in cities
        if re.search(r"\b" + re.escape(name.casefold()) + r"\b", folded)
        or re.search(r"\b" + re.escape(slug) + r"\b", folded)
    ]
    aliases = {
        "pm25": [r"pm\s*[_₂]?\s*2[.·]?5", r"pm₂\.₅", "fine particulate"],
        "pm10": [r"pm\s*[_₁]?\s*10", "coarse particulate"],
        "no2": [r"no₂", r"no2", "nitrogen dioxide"],
        "so2": [r"so₂", r"so2", "sulphur dioxide", "sulfur dioxide"],
        "co": [r"\bco\b", "carbon monoxide"],
        "o3": [r"o₃", r"\bo3\b", "ozone"],
        "nh3": [r"nh₃", r"nh3", "ammonia"],
    }
    pollutant_matches = [
        code
        for code in pollutants
        if any(re.search(pattern, folded) for pattern in aliases.get(code, [code]))
    ]
    return {"cities": city_matches, "pollutants": pollutant_matches}
