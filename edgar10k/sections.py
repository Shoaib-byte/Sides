import re
import warnings

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

# Modern 10-Ks are inline XBRL (XHTML), which makes bs4 warn; parsing them as HTML works fine.
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

MIN_SECTION_CHARS = 2000  # anything shorter is almost certainly a TOC line or a cross-reference

# Each section is (start heading, end heading). The patterns include the heading's
# title words, so in-text references like "see Item 8 of this Form 10-K" don't match.
# \W* lets the punctuation between "Item 7" and the title vary: "Item 7.", "ITEM 7 -", "Item 7:".
SECTIONS = {
    "Item 1A Risk Factors": (
        r"item\s*1a\W*risk\s+factors",
        r"item\s*1b\W*unresolved|item\s*1c\W*cybersecurity|item\s*2\W*properties",
    ),
    "Item 7 MD&A": (
        r"item\s*7\W*management",
        r"item\s*7a\W*quantitative|item\s*8\W*financial\s+statements",
    ),
}


BLOCK_TAGS = ["p", "div", "tr", "li", "br", "table", "h1", "h2", "h3", "h4", "h5", "h6"]


def html_to_text(html: str) -> str:
    """Convert the filing to plain text, one line per block element (paragraph, table row...)."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "ix:header"]):  # ix:header is hidden XBRL metadata
        tag.decompose()
    for tag in soup(BLOCK_TAGS):
        tag.insert_after("\n")  # keep block boundaries so headings land at the start of a line
    for tag in soup(["td", "th"]):
        tag.insert_after(" ")  # keep table cells apart: "Item 1A." | "Risk Factors"
    # Join with "" not " ": some filings wrap single letters in <span>s, and a space
    # separator turns "PROPERTIES" into "PR OPERTIES".
    text = soup.get_text("")
    text = text.replace("\xa0", " ")  # 10-Ks are full of non-breaking spaces
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    return re.sub(r" ?\n[\s]*", "\n", text).strip()


def extract_section(text: str, start_pat: str, end_pat: str) -> str:
    """Return the longest stretch of text from a start heading to the next end heading.

    A heading regex matches at least twice: once in the table of contents and once at
    the real heading. The table-of-contents match runs only to the next TOC line, so
    the real section is the longest candidate.
    """
    # A real heading starts its own line; a reference ("see Item 1A, Risk Factors") sits mid-sentence.
    start_re = re.compile(rf"^ ?(?:{start_pat})", re.I | re.M)
    end_re = re.compile(rf"^ ?(?:{end_pat})", re.I | re.M)
    best = ""
    for start in start_re.finditer(text):
        end = end_re.search(text, start.end())
        if end is None:
            continue
        candidate = text[start.start() : end.start()]
        if len(candidate) > len(best):
            best = candidate
    return best.strip()


def split_sections(html: str) -> dict[str, str]:
    text = html_to_text(html)
    sections = {}
    for name, (start, end) in SECTIONS.items():
        body = extract_section(text, start, end)
        if len(body) < MIN_SECTION_CHARS:
            # e.g. banks like JPM: "Item 7" only says the MD&A "appears on pages 46-160"
            print(f"WARNING: {name} is only {len(body)} chars, probably not the real section")
        sections[name] = body
    return sections


if __name__ == "__main__":
    import sys

    with open(sys.argv[1], encoding="utf-8") as f:
        sections = split_sections(f.read())
    for name, body in sections.items():
        print(f"=== {name}: {len(body):,} chars ===")
        print(body[:200], "...")
        print("...", body[-200:], "\n")
