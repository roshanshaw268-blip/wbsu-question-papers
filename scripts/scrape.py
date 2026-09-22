import json
import re
import time
from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse, unquote

import requests
from bs4 import BeautifulSoup


START_URL = "https://dinabandhumahavidyalaya.org/question-paper/"
OUTPUT_FILE = "data/papers.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 WBSU-Question-Paper-Indexer"
}

MAX_PAGES = 5000
DELAY = 0.2

session = requests.Session()
session.headers.update(HEADERS)

visited = set()
papers = {}
queue = [START_URL]


SUBJECTS = [
    "Bengali",
    "English",
    "Hindi",
    "Sanskrit",
    "Urdu",
    "Philosophy",
    "History",
    "Political Science",
    "Education",
    "Sociology",
    "Geography",
    "Economics",
    "Psychology",
    "Mathematics",
    "Physics",
    "Chemistry",
    "Botany",
    "Zoology",
    "Computer Science",
    "Commerce",
    "Physical Education",
    "Environmental Science",
]


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def get_html(url):
    try:
        response = session.get(url, timeout=25)

        if response.status_code != 200:
            print("HTTP", response.status_code, url)
            return None

        return response.text

    except Exception as e:
        print("ERROR:", url, e)
        return None


def get_year(path):
    match = re.search(r"/(20\d{2})(?:/|$)", path)

    if match:
        return match.group(1)

    match = re.search(r"\b(20\d{2})\b", path)

    return match.group(1) if match else ""


def get_subject(path):
    decoded = unquote(path)

    # First try known subjects
    for subject in SUBJECTS:
        if re.search(
            r"(?i)(?:^|/)" + re.escape(subject) + r"(?:/|$)",
            decoded
        ):
            return subject

    # Fallback: inspect path parts
    parts = [
        p.replace("-", " ").strip()
        for p in PurePosixPath(
            urlparse(decoded).path
        ).parts
    ]

    for part in parts:
        for subject in SUBJECTS:
            if part.lower() == subject.lower():
                return subject

    return ""


def get_semester(filename):
    text = unquote(filename).lower()

    patterns = [
        (r"sem[\s._-]*i\b", "Semester I"),
        (r"sem[\s._-]*ii\b", "Semester II"),
        (r"sem[\s._-]*iii\b", "Semester III"),
        (r"sem[\s._-]*iv\b", "Semester IV"),
        (r"sem[\s._-]*v\b", "Semester V"),
        (r"sem[\s._-]*vi\b", "Semester VI"),
    ]

    for pattern, result in patterns:
        if re.search(pattern, text):
            return result

    return ""


def get_code(text):
    text = unquote(text).upper()

    # Examples:
    # HISDSC202T
    # HISMIN202T
    # BNGACOR08T
    # ENGADSE04T
    # PHIMIN202T

    patterns = [
        r"\b[A-Z]{3,8}(?:DSC|MIN|COR|DSE|SEC|AEC|VAC|IDC|MDC|GE)[A-Z0-9]{2,8}\b",
        r"\b[A-Z]{3,10}(?:DSC|MIN|COR|DSE|SEC|AEC|VAC|IDC|MDC|GE)\d{2,4}T?\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            return match.group(0)

    return ""


def get_type(path, filename, code):
    text = unquote(
        path + " " + filename + " " + code
    ).lower()

    if "minor" in text or "min" in code.lower():
        return "Minor"

    if "major" in text or "dsc" in code.lower():
        return "Major"

    if "honours" in text:
        return "Honours"

    if "general" in text:
        return "General"

    if "aec" in code.lower():
        return "AEC"

    if "sec" in code.lower():
        return "SEC"

    if "vac" in code.lower():
        return "VAC"

    if "ge" in code.lower():
        return "GE"

    if "dse" in code.lower():
        return "DSE"

    return ""


def get_title(filename):
    name = unquote(filename)

    if name.lower().endswith(".pdf"):
        name = name[:-4]

    name = name.replace("_", " ")

    return clean(name)


def add_pdf(pdf_url, link_text):
    parsed = urlparse(pdf_url)

    path = unquote(parsed.path)

    filename = path.rstrip("/").split("/")[-1]

    if not filename.lower().endswith(".pdf"):
        return

    year = get_year(path)

    subject = get_subject(path)

    semester = get_semester(filename)

    code = get_code(filename)

    if not code:
        code = get_code(path)

    paper_type = get_type(path, filename, code)

    title = clean(link_text)

    if not title or title.lower() in ["pdf", "download"]:
        title = get_title(filename)

    paper = {
        "year": year,
        "subject": subject,
        "semester": semester,
        "type": paper_type,
        "code": code,
        "title": title,
        "url": pdf_url
    }

    # URL is unique ID
    papers[pdf_url] = paper

    print(
        "PDF:",
        year,
        "|",
        subject,
        "|",
        semester,
        "|",
        code,
        "|",
        filename
    )


def crawl():
    count = 0

    while queue and count < MAX_PAGES:

        url = queue.pop(0)

        if url in visited:
            continue

        parsed = urlparse(url)

        # Only crawl the question-paper area
        if parsed.netloc != urlparse(START_URL).netloc:
            continue

        if not parsed.path.startswith("/question-paper/"):
            continue

        visited.add(url)

        count += 1

        print(
            f"[{count}] Scanning:",
            url
        )

        html = get_html(url)

        if not html:
            continue

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        for a in soup.find_all(
            "a",
            href=True
        ):

            href = urljoin(
                url,
                a["href"]
            )

            href = href.split("#")[0]

            link_text = clean(
                a.get_text(
                    " ",
                    strip=True
                )
            )

            parsed_link = urlparse(href)

            if (
                parsed_link.netloc
                != parsed.netloc
            ):
                continue

            if not parsed_link.path.startswith(
                "/question-paper/"
            ):
                continue

            # PDF
            if parsed_link.path.lower().endswith(
                ".pdf"
            ):
                add_pdf(
                    href,
                    link_text
                )
                continue

            # Directory / HTML page
            if href not in visited:
                if href not in queue:
                    queue.append(href)

        time.sleep(DELAY)


def main():

    print("=" * 60)
    print("WBSU QUESTION PAPER SCRAPER")
    print("=" * 60)

    crawl()

    result = list(
        papers.values()
    )

    # Sort newest first
    result.sort(
        key=lambda x: (
            x.get("year", ""),
            x.get("subject", ""),
            x.get("semester", ""),
            x.get("code", ""),
            x.get("title", "")
        ),
        reverse=True
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 60)
    print("SCRAPING COMPLETE")
    print("=" * 60)
    print("Pages scanned:", len(visited))
    print("PDF papers found:", len(result))
    print("Saved:", OUTPUT_FILE)
    print("=" * 60)


if __name__ == "__main__":
    main()
