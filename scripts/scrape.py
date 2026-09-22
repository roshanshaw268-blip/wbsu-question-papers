import json
import re
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


START_URL = "https://dinabandhumahavidyalaya.org/question-paper/"
OUTPUT_FILE = "data/papers.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; WBSU-Paper-Indexer/1.0)"
}

MAX_PAGES = 300
DELAY = 0.5

session = requests.Session()
session.headers.update(HEADERS)

visited = set()
papers = []


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def get_page(url):
    try:
        r = session.get(url, timeout=20)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print("ERROR:", url, e)
        return None


def extract_code(text):
    patterns = [
        r"\b[A-Z]{3,8}(?:DSC|MIN|MAJ|SEC|VAC|AEC|IDC|MDC|GE|CC|DSE|DSE?)[A-Z0-9]*\b",
        r"\b[A-Z]{3,10}\d{3}[A-Z]\b",
        r"\b[A-Z]{3,10}\d{3,4}[A-Z]{0,3}\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text.upper())
        if match:
            return match.group(0)

    return ""


def detect_year(text):
    match = re.search(r"\b(20\d{2})\b", text)
    return match.group(1) if match else ""


def detect_semester(text):
    t = text.lower()

    if re.search(r"\bsemester[\s_-]*i\b|\bsem[\s_-]*i\b", t):
        return "Semester I"

    if re.search(r"\bsemester[\s_-]*ii\b|\bsem[\s_-]*ii\b", t):
        return "Semester II"

    if re.search(r"\bsemester[\s_-]*iii\b|\bsem[\s_-]*iii\b", t):
        return "Semester III"

    if re.search(r"\bsemester[\s_-]*iv\b|\bsem[\s_-]*iv\b", t):
        return "Semester IV"

    if re.search(r"\bsemester[\s_-]*v\b|\bsem[\s_-]*v\b", t):
        return "Semester V"

    if re.search(r"\bsemester[\s_-]*vi\b|\bsem[\s_-]*vi\b", t):
        return "Semester VI"

    return ""


def detect_type(text):
    t = text.lower()

    for name in [
        "Major",
        "Minor",
        "DSC",
        "SEC",
        "AEC",
        "VAC",
        "IDC",
        "MDC",
        "GE",
        "DSE",
        "CC",
    ]:
        if re.search(r"\b" + re.escape(name.lower()) + r"\b", t):
            return name

    return ""


def detect_subject(text):
    t = text.lower()

    subjects = [
        "Hindi",
        "English",
        "Bengali",
        "Philosophy",
        "History",
        "Political Science",
        "Education",
        "Sociology",
        "Geography",
        "Economics",
        "Mathematics",
        "Physics",
        "Chemistry",
        "Botany",
        "Zoology",
        "Computer Science",
        "Commerce",
        "Psychology",
        "Sanskrit",
        "Urdu",
        "Physical Education",
    ]

    for subject in subjects:
        if subject.lower() in t:
            return subject

    return ""


def add_paper(url, text):
    text = clean(text)

    if not text:
        return

    code = extract_code(text)
    year = detect_year(text)
    semester = detect_semester(text)
    paper_type = detect_type(text)
    subject = detect_subject(text)

    # Only keep likely question-paper links.
    lower = text.lower() + " " + url.lower()

    if not (
        ".pdf" in url.lower()
        or "question" in lower
        or "paper" in lower
        or code
    ):
        return

    paper = {
        "year": year,
        "subject": subject,
        "semester": semester,
        "type": paper_type,
        "code": code,
        "title": text[:180],
        "url": url,
    }

    if paper not in papers:
        papers.append(paper)


def crawl(url):
    if url in visited:
        return

    if len(visited) >= MAX_PAGES:
        return

    parsed = urlparse(url)

    if parsed.netloc != urlparse(START_URL).netloc:
        return

    visited.add(url)

    print("Scanning:", url)

    html = get_page(url)

    if not html:
        return

    soup = BeautifulSoup(html, "html.parser")

    # PDF links
    for a in soup.find_all("a", href=True):
        href = urljoin(url, a["href"])
        text = clean(a.get_text(" ", strip=True))

        if ".pdf" in href.lower():
            add_paper(href, text)

    # Crawl internal pages
    links = []

    for a in soup.find_all("a", href=True):
        href = urljoin(url, a["href"])
        parsed_link = urlparse(href)

        if parsed_link.netloc != parsed.netloc:
            continue

        if href.startswith("mailto:"):
            continue

        if href.startswith("javascript:"):
            continue

        if href in visited:
            continue

        links.append(href)

    for link in links:
        crawl(link)
        time.sleep(DELAY)


def main():
    print("Starting question-paper scan...")
    crawl(START_URL)

    # Remove duplicates by URL
    unique = {}

    for paper in papers:
        unique[paper["url"]] = paper

    final_papers = list(unique.values())

    final_papers.sort(
        key=lambda x: (
            x.get("year", ""),
            x.get("semester", ""),
            x.get("subject", ""),
            x.get("code", ""),
        ),
        reverse=True,
    )

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_papers, f, ensure_ascii=False, indent=2)

    print()
    print("Finished!")
    print("Pages scanned:", len(visited))
    print("Papers found:", len(final_papers))
    print("Saved to:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
