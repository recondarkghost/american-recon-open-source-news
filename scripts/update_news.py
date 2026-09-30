import json
import time
import re
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
DATA_FOLDER = ROOT / "data"
OUTPUT_FILE = DATA_FOLDER / "news.json"

DATA_FOLDER.mkdir(parents=True, exist_ok=True)

SEARCHES = {
    "United States": [
        '"United States" government policy',
        '"United States" economy jobs inflation',
        '"United States" military security',
        '"United States" border immigration',
        '"United States" infrastructure energy',
    ],
    "War and Security": [
        'war military conflict troops',
        'missile drone attack defense',
        'ceasefire sanctions weapons',
    ],
    "Global Affairs": [
        'international relations foreign policy',
        'government election diplomatic crisis',
        'civil unrest protest political crisis',
    ],
    "Economy": [
        'economy inflation jobs recession',
        'banking debt markets trade tariffs',
        'supply chain manufacturing shortage',
    ],
    "Energy": [
        'oil gas energy electricity pipeline',
        'nuclear power fuel prices',
    ],
    "Cyber and Technology": [
        'cyberattack ransomware data breach',
        'surveillance artificial intelligence security',
    ],
    "Disasters": [
        'earthquake flood wildfire hurricane',
        'disaster evacuation landslide drought',
    ],
    "Health": [
        'outbreak epidemic public health',
        'disease hospital medicine shortage',
    ],
    "Humanitarian": [
        'humanitarian crisis displacement refugees',
        'food shortage aid emergency',
    ],
    "Shipping and Trade": [
        'shipping port maritime cargo',
        'trade route vessel blockade',
    ],
}

BLOCKED_DOMAINS = {
    "cnn.com",
    "foxnews.com",
    "msnbc.com",
    "nbcnews.com",
    "abcnews.go.com",
    "cbsnews.com",
    "nytimes.com",
    "washingtonpost.com",
    "usatoday.com",
    "apnews.com",
    "reuters.com",
    "bbc.com",
    "bbc.co.uk",
}

US_TERMS = {
    "united states", "u.s.", " u.s ", "usa", "american", "america",
    "washington", "congress", "white house", "pentagon", "federal",
    "florida", "texas", "california", "new york", "border patrol",
}

def clean_text(value):
    value = str(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()

def normalize_domain(domain):
    domain = clean_text(domain).lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain

def is_blocked(domain):
    return any(
        domain == blocked or domain.endswith("." + blocked)
        for blocked in BLOCKED_DOMAINS
    )

def looks_english(title):
    if not title:
        return False

    letters = [character for character in title if character.isalpha()]
    if not letters:
        return False

    basic_latin = sum(
        1 for character in letters
        if "a" <= character.lower() <= "z"
    )

    return basic_latin / len(letters) >= 0.82

def is_us_report(title, category, source_country):
    combined = f"{title} {category} {source_country}".lower()

    if category == "United States":
        return True

    return any(term in combined for term in US_TERMS)

def download_search(query, category):
    parameters = {
        "query": f"({query}) sourcelang:english",
        "mode": "ArtList",
        "maxrecords": "250",
        "format": "json",
        "sort": "HybridRel",
        "timespan": "72h",
    }

    url = (
        "https://api.gdeltproject.org/api/v2/doc/doc?"
        + urlencode(parameters)
    )

    request = Request(
        url,
        headers={
            "User-Agent": "American-Recon-Open-Source-News/1.0",
            "Accept": "application/json",
        },
    )

    try:
        with urlopen(request, timeout=45) as response:
            payload = json.loads(response.read().decode("utf-8", "replace"))
    except Exception as error:
        print(f"Search unavailable: {query} | {error}")
        return []

    results = []

    for item in payload.get("articles", []):
        title = clean_text(item.get("title"))
        article_url = clean_text(item.get("url"))
        domain = normalize_domain(item.get("domain"))
        source_country = clean_text(item.get("sourcecountry"))
        seen_date = clean_text(item.get("seendate"))

        if not title or not article_url or not domain:
            continue

        if is_blocked(domain):
            continue

        if not looks_english(title):
            continue

        results.append({
            "title": title,
            "url": article_url,
            "domain": domain,
            "sourceCountry": source_country or "International",
            "seenDate": seen_date,
            "category": category,
            "section": (
                "United States"
                if is_us_report(title, category, source_country)
                else "World"
            ),
            "language": "English",
            "verification": "Original source not independently verified",
        })

    return results

def main():
    collected = []
    seen_urls = set()
    seen_titles = set()

    for category, queries in SEARCHES.items():
        for query in queries:
            print(f"Collecting: {category} | {query}")

            for report in download_search(query, category):
                url_key = report["url"].lower()
                title_key = re.sub(
                    r"[^a-z0-9]+",
                    " ",
                    report["title"].lower(),
                ).strip()

                if url_key in seen_urls or title_key in seen_titles:
                    continue

                seen_urls.add(url_key)
                seen_titles.add(title_key)
                collected.append(report)

            time.sleep(1)

    collected.sort(
        key=lambda report: report.get("seenDate", ""),
        reverse=True,
    )

    us_reports = [
        report for report in collected
        if report["section"] == "United States"
    ][:120]

    world_reports = [
        report for report in collected
        if report["section"] == "World"
    ][:240]

    output = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "language": "English",
        "totalReports": len(us_reports) + len(world_reports),
        "unitedStatesReports": us_reports,
        "worldReports": world_reports,
        "categories": list(SEARCHES.keys()),
    }

    OUTPUT_FILE.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("")
    print("AMERICAN RECON NEWS UPDATE COMPLETE")
    print(f"United States reports: {len(us_reports)}")
    print(f"Worldwide reports: {len(world_reports)}")
    print(f"Saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()