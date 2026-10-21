import csv
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

INPUT_FILE = "financial_news_articles.csv"
OUTPUT_FILE = "financial_news_articles_with_text.csv"

# Start with 5 articles to test the extraction.
# Change to None later to process all articles.
MAX_ARTICLES = None

HEADERS = {
    "User-Agent": "StudentFinancialNewsProject/1.0 (contact: vikashanand1505@gmail.com)"
}


def extract_article_text(url):
    """Download an accessible CNBC page and extract its article paragraphs."""

    domain = urlparse(url).hostname or ""

    # Restrict requests to CNBC-hosted article URLs.
    if domain != "cnbc.com" and not domain.endswith(".cnbc.com"):
        return "", "skipped_non_cnbc_url"

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20
        )

        if response.status_code in (403, 429):
            return "", f"access_restricted_{response.status_code}"

        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # CNBC article pages may use different body containers.
        selectors = [
            "div.ArticleBody-articleBody",
            "div.FeaturedContent-articleBody",
            "div.LiveBlogBody-articleBody"
        ]

        article_body = None

        for selector in selectors:
            article_body = soup.select_one(selector)
            if article_body is not None:
                break

        if article_body is None:
            return "", "article_body_not_found"

        # Extract readable paragraphs.
        paragraphs = [
            p.get_text(" ", strip=True)
            for p in article_body.find_all("p")
        ]

        # Ignore empty paragraphs.
        paragraphs = [p for p in paragraphs if p]

        article_text = "\n".join(paragraphs)

        if not article_text:
            return "", "no_paragraphs_found"

        return article_text, "success"

    except requests.RequestException as error:
        return "", f"request_error: {type(error).__name__}"


# Read the collected news dataset.
try:
    with open(INPUT_FILE, "r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

except (OSError, csv.Error) as error:
    print("Could not read input CSV:", error)
    raise SystemExit(1)

if not rows:
    print("The input CSV contains no articles.")
    raise SystemExit(1)

# Add a status column to track extraction results.
if "extraction_status" not in fieldnames:
    fieldnames.append("extraction_status")

attempted = 0
successful = 0

for index, row in enumerate(rows):
    # Leave remaining records untouched during the pilot test.
    if MAX_ARTICLES is not None and index >= MAX_ARTICLES:
        row["extraction_status"] = "not_attempted"
        continue

    attempted += 1

    # Reuse existing text if a record already has it.
    if row.get("article_text", "").strip():
        row["extraction_status"] = "already_available"
        successful += 1
        continue

    url = row.get("url", "").strip()

    if not url:
        row["extraction_status"] = "missing_url"
        continue

    text, status = extract_article_text(url)

    row["article_text"] = text
    row["extraction_status"] = status

    if status == "success":
        successful += 1
        print(f"{row.get('article_id', index + 1)}: Text extracted")
    else:
        print(f"{row.get('article_id', index + 1)}: {status}")

    # Be considerate of the publisher's servers.
    time.sleep(2)

# Save all original records, including unsuccessful attempts.
try:
    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

except (OSError, csv.Error) as error:
    print("Could not save output CSV:", error)
    raise SystemExit(1)

print("\nArticle extraction report")
print("Total records:", len(rows))
print("Records processed:", attempted)
print("Records with text:", successful)
print("Output file:", OUTPUT_FILE)
