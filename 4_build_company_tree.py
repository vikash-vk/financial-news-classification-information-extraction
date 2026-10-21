import csv
import json
import re
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "financial_news_extracted.csv"
RELATION_OUTPUT = BASE_DIR / "company_relationship_candidates.csv"
TREE_OUTPUT = BASE_DIR / "company_trees_from_news.json"


def find_company_mentions(sentence, company_names):
    """Find known company/organization names in a sentence."""
    names = sorted(
        {str(name).strip() for name in company_names if str(name).strip()},
        key=len,
        reverse=True,
    )
    if not names:
        return []

    pattern = re.compile(
        r"(?<!\w)(" + "|".join(re.escape(name) for name in names) + r")(?!\w)",
        flags=re.IGNORECASE,
    )
    return [
        (match.start(), match.end(), match.group(1))
        for match in pattern.finditer(sentence)
    ]


def extract_explicit_subsidiary_edges(row):
    """Extract relationships expressed with 'its subsidiary' or 'subsidiary of'."""
    try:
        company_names = json.loads(row.get("companies_mentioned", "[]") or "[]")
        if not isinstance(company_names, list):
            company_names = []
    except (json.JSONDecodeError, TypeError):
        company_names = []

    edges = []
    seen = set()

    # Search full article text first, then summary and title.
    for field in ("article_text", "summary", "title"):
        text = str(row.get(field, "") or "").replace("\n", " ").strip()
        if not text:
            continue

        sentences = re.split(r"(?<=[.!?])\s+", text)
        for sentence in sentences:
            cues = [
                (re.search(r"\bits subsidiary\b", sentence, re.IGNORECASE), "parent_before"),
                (re.search(r"\bsubsidiary of\b", sentence, re.IGNORECASE), "child_before"),
            ]

            for cue, direction in cues:
                if cue is None:
                    continue

                mentions = find_company_mentions(sentence, company_names)
                before = [item for item in mentions if item[1] <= cue.start()]
                after = [item for item in mentions if item[0] >= cue.end()]
                if not before or not after:
                    continue

                if direction == "parent_before":
                    parent, child = before[-1][2], after[0][2]
                else:
                    child, parent = before[-1][2], after[0][2]

                if parent.casefold() == child.casefold():
                    continue

                key = (parent.casefold(), child.casefold(), row.get("article_id", ""))
                if key in seen:
                    continue
                seen.add(key)

                edges.append({
                    "parent_company": parent,
                    "child_company": child,
                    "relationship_type": "subsidiary",
                    "article_id": row.get("article_id", ""),
                    "article_title": row.get("title", ""),
                    "evidence_sentence": sentence.strip(),
                    "source_url": row.get("url", ""),
                    "review_status": "verify before final submission",
                })

    return edges


def build_node(company, children_by_parent, root_name=None, path=None):
    """Recursively create a JSON tree from extracted parent-child relationships."""
    if path is None:
        path = set()

    company_key = company.casefold()
    if company_key in path:
        return {"name": company, "relationship": "cycle_detected", "children": []}

    next_path = path | {company_key}
    children = sorted(set(children_by_parent.get(company, [])), key=str.casefold)
    relationship = "parent_company" if company == root_name else "subsidiary"

    return {
        "name": company,
        "relationship": relationship,
        "children": [
            build_node(child, children_by_parent, root_name=root_name, path=next_path)
            for child in children
        ],
    }


def main():
    print("Starting company-tree construction...")
    print("Reading:", INPUT_FILE)

    try:
        with INPUT_FILE.open("r", newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            rows = list(reader)
            if not reader.fieldnames:
                raise ValueError("Input CSV has no column headers.")
    except (OSError, csv.Error, ValueError) as error:
        print("ERROR: Could not read the input CSV:", error)
        print("Make sure financial_news_extracted.csv is beside this script.")
        return

    print("Articles loaded:", len(rows))
    if not rows:
        print("ERROR: The input CSV has no article rows.")
        return

    required_columns = {"companies_mentioned", "article_text", "summary", "title"}
    missing = required_columns - set(rows[0].keys())
    if missing:
        print("ERROR: CSV is missing required columns:", ", ".join(sorted(missing)))
        print("Available columns:", ", ".join(rows[0].keys()))
        return

    edges = []
    for row in rows:
        edges.extend(extract_explicit_subsidiary_edges(row))

    edge_columns = [
        "parent_company", "child_company", "relationship_type", "article_id",
        "article_title", "evidence_sentence", "source_url", "review_status"
    ]
    try:
        with RELATION_OUTPUT.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=edge_columns)
            writer.writeheader()
            writer.writerows(edges)
    except OSError as error:
        print("ERROR: Could not write relationship CSV:", error)
        return

    children_by_parent = defaultdict(list)
    parents = set()
    children = set()
    for edge in edges:
        parent = edge["parent_company"]
        child = edge["child_company"]
        if child not in children_by_parent[parent]:
            children_by_parent[parent].append(child)
        parents.add(parent)
        children.add(child)

    roots = sorted(parents - children, key=str.casefold)
    trees = [build_node(root, children_by_parent, root_name=root) for root in roots]

    tree_output = {
        "company_trees": trees,
        "relationship_count": len(edges),
        "method": "Rule-based extraction from explicit subsidiary wording in article text, summary, or title.",
        "note": "Partial candidate tree based on collected articles. Review every evidence sentence; this is not a complete ownership database."
    }

    try:
        with TREE_OUTPUT.open("w", encoding="utf-8") as file:
            json.dump(tree_output, file, indent=4, ensure_ascii=False)
    except OSError as error:
        print("ERROR: Could not write JSON tree:", error)
        return

    print("\nExplicit subsidiary relationships found:", len(edges))
    if edges:
        for edge in edges:
            print(f"{edge['parent_company']} -> {edge['child_company']} [{edge['relationship_type']}]")
            print("Evidence:", edge["evidence_sentence"])
    else:
        print("No explicit subsidiary statements were found by the current rules.")
        print("The output files were still created; this does not prove that no subsidiaries exist.")

    print("\nCreated:", RELATION_OUTPUT.name)
    print("Created:", TREE_OUTPUT.name)
    print("Finished.")


if __name__ == "__main__":
    main()