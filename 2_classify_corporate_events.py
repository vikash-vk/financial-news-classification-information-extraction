import csv
import re
from collections import Counter

INPUT_FILE = "financial_news_articles_with_text.csv"
OUTPUT_FILE = "financial_news_classified.csv"

# Each category has patterns that may indicate a corporate event.
EVENT_RULES = [
    (
        "Hostile Takeover",
        r"\bhostile (?:takeover|bid)\b"
    ),
    (
        "Acquisition",
        r"\b(?:acquisition|acquire|acquires|acquired|acquiring|"
        r"buying|bought|purchased|agreed to buy|plans to buy|will buy)\b"
    ),
    (
        "Merger",
        r"\b(?:merger|mergers|merge|merged|merging)\b"
    ),
    (
        "Takeover / Buyout",
        r"\b(?:takeover|takeovers|buyout|proxy fight)\b"
    ),
    (
        "Sale / Divestiture",
        r"\b(?:divestiture|divested|divesting|selling|sold|"
        r"sale of|asset sale|spin-off|spin off|offloaded)\b"
    ),
    (
        "Leadership / Management Change",
        r"\b(?:appointed|steps down|resigns?|resignation|"
        r"retires?|retirement|new CEO|hired to run|brought in to run)\b"
    ),
    (
        "Layoffs / Restructuring",
        r"\b(?:layoffs?|lay off|laid off|job cuts?|"
        r"workforce reduction|restructuring|reorganization)\b"
    ),
    (
        "Hiring / Workforce Change",
        r"\bhired\s+[\d,]+\s+(?:contractors|employees|workers)\b"
    ),
    (
        "Partnership / Commercial Agreement",
        r"\b(?:joint venture|partnership|partners with|"
        r"strategic alliance|collaboration|joint membership)\b"
    ),
    (
        "Investment / Capital Allocation",
        r"\b(?:stock buyback|share repurchase|buyback|"
        r"capital allocation|investments?|invested in|invests in)\b"
    ),
    (
        "Regulatory / Legal Event",
        r"\b(?:regulatory penalty|fine|penalty|antitrust|"
        r"lawsuit|settlement|regulatory action against)\b"
    ),
    (
        "Financial Results / Guidance",
        r"\b(?:earnings|revenue miss|tops? estimates|"
        r"beats? expectations|profit outlook|guidance|forecast|"
        r"trading revenue|shares drop|shares fall|quarterly results)\b"
    ),
    (
        "Operational / Strategic Change",
        r"\b(?:overhaul(?:s|ed|ing)?|revamp(?:s|ed|ing)?|"
        r"expand(?:s|ed|ing|sion)?|delay(?:s|ed|ing)?|"
        r"switch(?:es|ed|ing)? to|trimming|trimmed|"
        r"leaning into|doing away with|new benefits|"
        r"new campus|turnaround)\b"
    ),
    (
        "Product / Service Launch",
        r"\b(?:launch(?:es|ed|ing)?|introduc(?:es|ed|ing|tion)|"
        r"unveil(?:s|ed|ing)?|reveals?|debut(?:s|ed|ing)?|"
        r"now on sale|rolls? out)\b"
    )
]

# Look for possible M&A stories that are not confirmed deals.
MNA_PATTERN = (
    r"\b(?:acquisition|acquire|acquired|acquiring|"
    r"takeover|merger|merging|buyout|hostile bid|"
    r"will buy|plans to buy|agreed to buy|offer to buy)\b"
)

DENIAL_PATTERN = (
    r"\b(?:not buying|not acquiring|denies?|denied|"
    r"no plans to (?:buy|acquire))\b"
)

SPECULATION_PATTERN = (
    r"\b(?:speculation|speculative|rumou?rs?|hypothetical|"
    r"potential|would|could|might)\b"
)

# Phrases suggesting that an operational decision is still uncertain.
UNCERTAIN_ACTION_PATTERN = (
    r"\b(?:weighing whether|whether to continue|"
    r"considering whether|not yet decided|under consideration)\b"
)


def find_event(text):
    """Return the first event category found in the text."""
    for event_type, pattern in EVENT_RULES:
        match = re.search(pattern, text, flags=re.IGNORECASE)

        if match:
            return event_type, match.group(0)

    return None, ""


def classify_article(row):
    """Classify one article using its title and summary."""

    title = row.get("title", "").strip()
    summary = row.get("summary", "").strip()

    short_text = f"{title} {summary}"

    mna_found = re.search(
        MNA_PATTERN, short_text, flags=re.IGNORECASE
    )
    denial_found = re.search(
        DENIAL_PATTERN, short_text, flags=re.IGNORECASE
    )
    speculation_found = re.search(
        SPECULATION_PATTERN, short_text, flags=re.IGNORECASE
    )

    # Case 1: An acquisition or takeover is explicitly denied.
    if mna_found and denial_found:
        return {
            "is_corporate_event": "No - denied",
            "event_type": "M&A Denial",
            "classification_basis": "Title and summary",
            "matched_keyword": denial_found.group(0),
            "review_required": "Yes"
        }

    # Case 2: An M&A story appears speculative or hypothetical.
    if mna_found and speculation_found:
        return {
            "is_corporate_event": "Needs review",
            "event_type": "M&A Speculation / Proposed Deal",
            "classification_basis": "Title and summary",
            "matched_keyword": mna_found.group(0),
            "review_required": "Yes"
        }

    # Case 3: Try the headline first.
    event_type, keyword = find_event(title)

    if event_type:
        if re.search(
            UNCERTAIN_ACTION_PATTERN,
            short_text,
            flags=re.IGNORECASE
        ):
            return {
                "is_corporate_event": "Needs review",
                "event_type": f"Potential - {event_type}",
                "classification_basis": "Headline; uncertainty detected",
                "matched_keyword": keyword,
                "review_required": "Yes"
            }

        return {
            "is_corporate_event": "Yes",
            "event_type": event_type,
            "classification_basis": "Headline",
            "matched_keyword": keyword,
            "review_required": "No"
        }

    # Case 4: Search the summary if the headline did not match.
    event_type, keyword = find_event(summary)

    if event_type:
        return {
            "is_corporate_event": "Needs review",
            "event_type": event_type,
            "classification_basis": "Summary only",
            "matched_keyword": keyword,
            "review_required": "Yes"
        }

    # Case 5: No recognized event pattern was found.
    return {
        "is_corporate_event": "No clear event",
        "event_type": "Unclassified / General Business News",
        "classification_basis": "No matching rule",
        "matched_keyword": "",
        "review_required": "Yes"
    }


# Read the existing dataset.
try:
    with open(
        INPUT_FILE,
        "r",
        newline="",
        encoding="utf-8-sig"
    ) as file:
        reader = csv.DictReader(file)
        rows = list(reader)

        if not reader.fieldnames:
            raise ValueError("Input CSV has no column headers.")

except (OSError, csv.Error, ValueError) as error:
    print("Could not read the input dataset:", error)
    raise SystemExit(1)

if not rows:
    print("The input dataset is empty.")
    raise SystemExit(1)

# Add the classification to each article.
output_rows = []

for row in rows:
    result = classify_article(row)

    output_rows.append({
        **row,
        **result
    })

# Save the classified dataset.
new_columns = [
    "is_corporate_event",
    "event_type",
    "classification_basis",
    "matched_keyword",
    "review_required"
]

fieldnames = list(rows[0].keys())

for column in new_columns:
    if column not in fieldnames:
        fieldnames.append(column)

try:
    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(output_rows)

except (OSError, csv.Error) as error:
    print("Could not save the classified dataset:", error)
    raise SystemExit(1)

# Display a summary of the classification.
counts = Counter(
    row["is_corporate_event"] for row in output_rows
)

print("Classification completed.")
print("Total articles:", len(output_rows))
print("Output file:", OUTPUT_FILE)
print("\nClassification counts:")

for label, count in counts.items():
    print(f"{label}: {count}")

print("\nFirst five classifications:")

for row in output_rows[:5]:
    print(
        row["article_id"],
        "|",
        row["event_type"],
        "|",
        row["is_corporate_event"]
    )