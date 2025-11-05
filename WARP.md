# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

Automated web scraper that extracts, categorizes, and summarizes Statsig blog posts into a structured markdown file for use with AI assistants (ChatGPT Projects, Claude Skills). The scraper processes 300+ blog posts across 10 categories.

## Common Commands

### Running the Scraper

```bash
# Standard scrape (generates statsig_blog_summary.md)
python3 statsig_blog_scraper.py

# Or execute directly (script has shebang)
./statsig_blog_scraper.py

# Custom output file
python3 statsig_blog_scraper.py -o custom_output.md

# Test with limited posts
python3 statsig_blog_scraper.py -m 10
```

### Development Setup

```bash
# Install dependencies
pip3 install -r requirements.txt

# Or using virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
pip install -r requirements.txt
```

### Testing & Validation

```bash
# Test scraper with 5 posts
python3 statsig_blog_scraper.py -m 5 -o test_output.md

# Check output file statistics
wc -l statsig_blog_summary.md
ls -lh statsig_blog_summary.md

# Validate markdown structure
grep "^## " statsig_blog_summary.md | head -20
```

## Architecture

### Core Components

**`StatsigBlogScraper` class** - Single-responsibility scraper with distinct phases:
1. **Discovery** (`fetch_all_posts`) - Scrapes blog index page, extracts post URLs
2. **Content extraction** (`fetch_post_content`) - Multi-strategy parsing (JSON-LD → HTML fallback)
3. **Categorization** (`categorize_post`) - Keyword-based multi-category assignment
4. **Summarization** (`summarize_post`) - Sentence extraction + key points identification
5. **Output generation** (`generate_markdown`) - Hierarchical markdown with ToC

### Data Flow

```
Blog Index → Post URLs → Individual Posts → Content Extraction → 
Categorization → Summarization → Markdown Generation → File Output
```

Each post passes through the pipeline independently with 0.5s delay between requests.

### Content Extraction Strategy

The scraper uses **layered fallback parsing**:
- Primary: JSON-LD structured data (`<script type="application/ld+json">`)
- Secondary: Semantic HTML selectors (article, main, blog-content classes)
- Tertiary: DOM traversal from h1 parent containers
- Last resort: All `<p>` tags with length filtering

This handles varying HTML structures across Statsig's blog evolution.

### Categorization System

Posts can belong to **multiple categories** simultaneously using keyword matching:
- 10 predefined categories (A/B Testing, AI/ML, Engineering, etc.)
- Keywords checked against title + full body text (case-insensitive)
- Defaultdict storage allows posts to appear in multiple category sections

### Output Format

Generated markdown contains:
- Metadata header (generation date, total posts)
- Table of Contents with anchor links
- Category sections (sorted alphabetically)
- Individual post entries with: title, date, author, URL, summary, key points
- AI assistant usage instructions

## Key Implementation Details

### Rate Limiting
`time.sleep(0.5)` between requests in `run()` method. Increase to 1.0 if encountering 429 errors.

### Requests Session
Uses persistent `requests.Session()` with User-Agent header to avoid bot detection.

### Summary Extraction
- Takes first 3 sentences (500 char max)
- Extracts up to 5 key points from first 50 lines using regex pattern matching
- Falls back to "Article about {title}" if extraction fails

### Category Keywords
Defined in `categorize_post()` dict. To add categories, extend the `category_keywords` dictionary.

## File Structure

```
statsig-blog-automation/
├── statsig_blog_scraper.py    # Main scraper (298 lines)
├── requirements.txt            # Dependencies: requests, beautifulsoup4
├── statsig_blog_summary.md     # Generated output (2.2MB, 63K lines)
├── README.md                   # User documentation
├── GITHUB_SETUP.md            # GitHub workflow setup
└── .gitignore                 # Python + IDE exclusions
```

## Python Dependencies

- **requests** - HTTP client for web scraping
- **beautifulsoup4** - HTML parsing and content extraction

No ML libraries or complex dependencies required.

## Extending the Scraper

### Adding New Categories

Edit `categorize_post()` method, line 133:

```python
category_keywords = {
    'Your New Category': ['keyword1', 'keyword2', ...],
    # existing categories...
}
```

### Changing Summary Length

Edit `summarize_post()` method, line 159:

```python
summary = '. '.join([s.strip() for s in sentences[:5]])  # Change from 3
key_points = key_points[:10]  # Change from 5
```

### Filtering Posts by Date/Category

Add filtering in `run()` method after enrichment (line 266):

```python
enriched_posts = [p for p in enriched_posts if <condition>]
```

## Common Issues

### SSL/urllib3 Warnings
Non-blocking warnings about OpenSSL. Scraper functions normally. Fix with:
```bash
pip3 install --upgrade urllib3 requests
```

### Empty/Generic Summaries
Indicates HTML structure changes on statsig.com. Update selectors in `fetch_post_content()` method (lines 92-111).

### 429 Rate Limiting
Increase sleep delay in `run()` method (line 267) or use `-m` flag to limit batch size.

## Output Usage

The generated `statsig_blog_summary.md` is designed for AI assistant knowledge bases:
- ChatGPT Projects: Upload as project file
- Claude Projects: Add to project knowledge
- Contains 300+ posts, 10 categories, ~2.2MB total

See README.md for detailed AI assistant integration instructions.
