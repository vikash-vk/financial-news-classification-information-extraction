# Financial News Classification and Information Extraction

## Project Overview
This project uses Python to collect financial news articles, classify corporate events, extract important information, and construct a company relationship tree.

## Objectives
- Collect financial news from the CNBC Business RSS feed.
- Extract article text and metadata.
- Classify corporate events such as acquisitions, mergers, takeovers, and management changes.
- Extract company names, people, dates, and monetary amounts using NLP.
- Identify parent–subsidiary relationships and construct a company tree.

## Technologies Used
- Python
- Requests
- Beautiful Soup
- Regular Expressions
- spaCy
- CSV and JSON

## Project Workflow
1. Collect financial news articles.
2. Extract readable article text.
3. Classify corporate events using rule-based techniques.
4. Extract entities using Named Entity Recognition (NER).
5. Identify company relationships and generate a hierarchical tree.
6. Save the outputs in CSV and JSON formats.

Run the Python scripts in the order described in the project workflow.

## Outputs
The project generates CSV files containing collected articles, classification results, extracted information, and candidate company relationships. A JSON file represents the identified company hierarchy.
