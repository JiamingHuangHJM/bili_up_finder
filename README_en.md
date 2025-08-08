# Bili Up Finder

[中文版本](README.md) | English

## Description

Bili Up Finder is a tool designed to help users search for and analyze Bilibili content creators (Up主). It provides features such as keyword expansion, relevance determination, and report generation using AI-powered assistants.

## Configuration

1. Ensure Python 3.12 or higher is installed.
2. Install dependencies using `pip`:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure API keys for OpenAI in your environment variables:
   ```bash
   export OPENAI_API_KEY="your_api_key_here"
   ```

## Usage

Run the main script to generate reports:
```bash
python -m bili_up_finder.web_builder
```

## Example

To generate a report for a search query:
```bash
python -m bili_up_finder.web_builder --query "example_keyword"
```

## Features

- **Keyword Expansion**: Automatically expand search queries with related terms.
- **Relevance Determination**: Judge whether videos or user spaces are relevant to the search query.
- **Report Generation**: Create HTML reports summarizing the findings.

## License

This project is licensed under the MIT License.