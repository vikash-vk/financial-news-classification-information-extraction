import requests
import csv
import xml.etree.ElementTree as ET
import re
import html
from urllib.parse import urlparse

# Step 1: CNBC Business RSS feed
RSS_URL = "https://www.cnbc.com/id/10001147/device/rss/rss.html"

# Step 2: Download the RSS feed
try:
    response = requests.get(
        RSS_URL,
        headers={"User-Agent": "StudentFinancialNewsProject/1.0"},
        timeout=30
    )
    response.raise_for_status()

except requests.RequestException as error:
    print("Could not download the CNBC RSS feed:", error)
    raise SystemExit(1)

# Step 3: Parse the downloaded XML
try:
    root = ET.fromstring(response.content)
except ET.ParseError as error:
    print("Could not parse the RSS feed:", error)
    raise SystemExit(1)

# Step 4: Find all news items
items = root.findall(".//item")

if not items:
    print("No news items found. The feed structure may have changed.")
    raise SystemExit(1)

# Step 5: Extract article details
rows = []
seen_urls = set()

for item in items:
    title = item.findtext("title", default="").strip()
    url = item.findtext("link", default="").strip()
    published_date = item.findtext("pubDate", default="").strip()

    # RSS descriptions usually contain short article summaries
    summary = item.findtext("description", default="")
    summary = html.unescape(summary)
    summary = re.sub(r"<[^>]*>", " ", summary)
    summary = re.sub(r"\s+", " ", summary).strip()

    # Ignore incomplete or duplicate articles
    if not title or not url or url in seen_urls:
        continue

    seen_urls.add(url)

    source = urlparse(url).netloc

    rows.append({
        "article_id": f"NEWS_{len(rows) + 1:03d}",
        "title": title,
        "published_date": published_date,
        "source": source,
        "url": url,
        "summary": summary,
        "article_text": ""
    })

# Step 6: Save the results in a CSV file
columns = [
    "article_id",
    "title",
    "published_date",
    "source",
    "url",
    "summary",
    "article_text"
]

with open(
    "financial_news_articles.csv",
    "w",
    newline="",
    encoding="utf-8-sig"
) as file:
    writer = csv.DictWriter(file, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)

# Step 7: Display a collection report
print("News collection completed successfully.")
print("RSS items found:", len(items))
print("Unique articles saved:", len(rows))
print("Output file: financial_news_articles.csv")

for row in rows[:5]:
    print("-", row["title"])