import csv
import json
import re
import spacy

INPUT_FILE = "financial_news_classified.csv"
OUTPUT_FILE = "financial_news_extracted.csv"

# Load spaCy's English NLP model.
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("English model not found.")
    print("Run: python -m spacy download en_core_web_sm")
    raise SystemExit(1)


def unique_entities(entities):
    """Keep entities in their original order and remove duplicates."""
    result = []
    seen = set()

    for entity in entities:
        value = entity.strip()
        key = value.casefold()

        if value and key not in seen:
            seen.add(key)
            result.append(value)

    return result


def get_entities(doc, entity_label):
    """Return entities of a particular type from a spaCy document."""
    return unique_entities(
        ent.text
        for ent in doc.ents
        if ent.label_ == entity_label
    )


def find_event_context(doc, keyword):
    """Find the sentence containing the classification keyword."""
    if not keyword:
        return ""

    pattern = re.compile(re.escape(keyword), re.IGNORECASE)

    for sentence in doc.sents:
        if pattern.search(sentence.text):
            return sentence.text.strip()

    return ""


def extract_information(row):
    """Extract candidate entities and event context from one article."""

    title = row.get("title", "").strip()
    summary = row.get("summary", "").strip()
    article_text = row.get("article_text", "").strip()

    # Put the title first to help identify the main subject.
    full_text = "\n".join(
        part for part in [title, summary, article_text] if part
    )

    # Limit text length to keep processing manageable.
    full_text = full_text[:20000]

    # Process the text with spaCy.
    doc = nlp(full_text)
    title_doc = nlp(title) if title else None

    # ORG = organizations, DATE = date expressions,
    # MONEY = monetary amounts.
    all_companies = get_entities(doc, "ORG")
    date_mentions = get_entities(doc, "DATE")
    money_mentions = get_entities(doc, "MONEY")
    people_mentioned = get_entities(doc, "PERSON")

    # Prefer a company recognized in the headline.
    title_companies = (
        get_entities(title_doc, "ORG")
        if title_doc is not None
        else []
    )

    primary_company = (
        title_companies[0]
        if title_companies
        else (all_companies[0] if all_companies else "")
    )

    # Use the classifier's matched keyword for context.
    keyword = row.get("matched_keyword", "").strip()
    event_context = find_event_context(doc, keyword)

    # Find a sentence that mentions an M&A-related action
    # and at least two organizations.
    mna_pattern = re.compile(
        r"\b(?:acquire[sd]?|acquiring|buy|buys|bought|"
        r"purchase[sd]?|merger|merge[sd]?|merging|"
        r"takeover|buyout|sell|sells|sold|selling|"
        r"divestiture|divested)\b",
        re.IGNORECASE
    )

    possible_parties = []
    party_context = ""

    for sentence in doc.sents:
        organizations = unique_entities(
            ent.text
            for ent in sentence.ents
            if ent.label_ == "ORG"
        )

        if mna_pattern.search(sentence.text) and len(organizations) >= 2:
            possible_parties = organizations
            party_context = sentence.text.strip()
            break

    # Save the M&A sentence if it provides better event context.
    if party_context:
        event_context = party_context

    # Require verification when information may be uncertain.
    needs_review = (
        row.get("review_required", "").strip().lower() == "yes"
        or not all_companies
        or row.get("event_type", "").startswith("M&A")
        or row.get("event_type", "").startswith("Potential")
    )

    return {
        "primary_company_candidate": primary_company,
        "companies_mentioned": json.dumps(
            all_companies, ensure_ascii=False
        ),
        "people_mentioned": json.dumps(
            people_mentioned, ensure_ascii=False
        ),
        "date_mentions": json.dumps(
            date_mentions, ensure_ascii=False
        ),
        "money_mentions": json.dumps(
            money_mentions, ensure_ascii=False
        ),
        "possible_mna_parties": json.dumps(
            possible_parties, ensure_ascii=False
        ),
        "event_context": event_context,
        "information_extraction_review": (
            "Yes" if needs_review else "Check"
        )
    }


# Read the classified articles.
try:
    with open(
        INPUT_FILE, "r", newline="", encoding="utf-8-sig"
    ) as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        original_columns = reader.fieldnames or []

except (OSError, csv.Error) as error:
    print("Could not read the input file:", error)
    raise SystemExit(1)

if not rows:
    print("No articles found in the input CSV.")
    raise SystemExit(1)

# Extract information article by article.
output_rows = []

for index, row in enumerate(rows, start=1):
    extracted = extract_information(row)
    output_rows.append({**row, **extracted})

    print(
        f"Processed {index}/{len(rows)}: "
        f"{row.get('article_id', index)}"
    )

# Keep the original columns and append new fields.
extra_columns = [
    "primary_company_candidate",
    "companies_mentioned",
    "people_mentioned",
    "date_mentions",
    "money_mentions",
    "possible_mna_parties",
    "event_context",
    "information_extraction_review"
]

fieldnames = list(original_columns)

for column in extra_columns:
    if column not in fieldnames:
        fieldnames.append(column)

# Write the structured output.
try:
    with open(
        OUTPUT_FILE, "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

except (OSError, csv.Error) as error:
    print("Could not save the output file:", error)
    raise SystemExit(1)

print("\nInformation extraction completed.")
print("Total articles processed:", len(output_rows))
print("Output file:", OUTPUT_FILE)