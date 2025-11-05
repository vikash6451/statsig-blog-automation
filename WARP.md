# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

**Version 2.0** - Enhanced automated web scraper that extracts, categorizes, and comprehensively summarizes Statsig blog posts into an AI-optimized markdown knowledge base for use with AI assistants (ChatGPT Projects, Claude Skills). 

The scraper processes 300+ blog posts across 10 categories and now extracts:
- Comprehensive summaries with context
- Concrete examples and use cases
- Quantitative metrics and data points
- Actionable takeaways and insights
- Category-specific prompt suggestions

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
4. **Enhanced extraction** (NEW):
   - `extract_data_points()` - Quantitative metrics extraction
   - `extract_examples()` - Concrete examples and use cases
   - `extract_key_takeaways()` - Actionable insights
5. **Summarization** (`summarize_post`) - Comprehensive summary with context + key points
6. **Output generation** (`generate_markdown`) - AI-optimized markdown with emojis, prompts, usage guide

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

### Output Format (v2.0)

Generated markdown contains:
- **Header**: Title, metadata (date, total articles, categories)
- **Overview**: Purpose and content description
- **Table of Contents**: With article counts per category
- **Category sections** (sorted alphabetically):
  - Category-specific prompt suggestions (💡)
  - Individual post entries with:
    - Title, date (📅), author (✍️)
    - Source URL (🔗)
    - Summary (📖)
    - Key Points (🎯)
    - Data Points & Metrics (📊) - NEW
    - Examples & Use Cases (💼) - NEW
    - Key Takeaways (✅) - NEW
- **AI Assistant Usage Guide** (🤖):
  - Prompting strategies for users
  - Instructions for AI assistants
  - Category-specific use cases
  - Quick reference

## Key Implementation Details

### Rate Limiting
`time.sleep(0.5)` between requests in `run()` method. Increase to 1.0 if encountering 429 errors.

### Requests Session
Uses persistent `requests.Session()` with User-Agent header to avoid bot detection.

### Enhanced Content Extraction (v2.0)

**Summary**: 
- First 2 sentences (up to 800 chars)
- Context-rich introduction
- Falls back to "Article about {title}" if extraction fails

**Key Points** (5-8 per article):
- Explicit bullets from content
- Section headers as thematic points
- Case-insensitive deduplication

**Data Points** (up to 5):
- Percentage improvements ("85% reduction")
- Performance metrics ("100ms faster")
- Volume metrics ("1M requests")
- Comparison metrics ("from X to Y")

**Examples** (1-3 per article):
- Detects "for example", "such as", "case study"
- Captures 1-2 lines of context
- Length: 50-300 chars

**Takeaways** (up to 5):
- Explicit conclusion/summary sections
- Actionable sentences ("should", "must", "best practice")
- Length: 40-200 chars

### Category Keywords
Defined in `categorize_post()` dict. To add categories, extend the `category_keywords` dictionary.

## File Structure

```
statsig-blog-automation/
├── statsig_blog_scraper.py    # Main scraper (~560 lines, v2.0)
├── requirements.txt            # Dependencies: requests, beautifulsoup4
├── statsig_blog_summary.md     # Generated AI-optimized knowledge base
├── README.md                   # Comprehensive user documentation
├── CHANGELOG.md                # Version history (NEW)
├── QUICKSTART.md               # Quick start guide (NEW)
├── GITHUB_SETUP.md            # GitHub workflow setup
├── WARP.md                     # This file - dev guidance
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

Edit `summarize_post()` method (around line 286):

```python
# Summary length
summary = ' '.join(summary_parts)[:800]  # Change from 800

# Key points count
key_points = deduped[:8]  # Change from 8

# Data points count (in extract_data_points, line 188)
if len(data_points) >= 5:  # Change from 5

# Examples count (in extract_examples, line 231)
if len(examples) >= 3:  # Change from 3

# Takeaways count (in extract_key_takeaways, line 284)
return takeaways[:5]  # Change from 5
```

### Filtering Posts by Date/Category

Add filtering in `run()` method after enrichment (around line 370):

```python
enriched_posts = [p for p in enriched_posts if <condition>]
```

### Adding Custom Extraction Patterns

To extract different types of data:

**In `extract_data_points()` (line 167)**:
```python
patterns = [
    r'your custom regex pattern',
    # ... existing patterns
]
```

**In `extract_examples()` (line 193)**:
```python
example_patterns = [
    r'your custom pattern',
    # ... existing patterns
]
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
Increase sleep delay in `run()` method (around line 385) or use `-m` flag to limit batch size.

### Missing Enhanced Content Sections
If data points, examples, or takeaways are empty for many posts:
- The extraction patterns may need adjustment
- Blog HTML structure may have changed
- Test with specific posts: `python3 statsig_blog_scraper.py -m 5 -o test.md`
- Check the test output for which sections are populated

## Output Usage

The generated `statsig_blog_summary.md` is an AI-optimized knowledge base:
- **ChatGPT Projects**: Upload as project file with custom instructions
- **Claude Projects**: Add to project knowledge
- **Contains**: 300+ posts, 10 categories, comprehensive metadata
- **Format**: Markdown with emojis, structured for AI consumption
- **Size**: Varies based on content (typically 3-5MB with enhancements)

See:
- **QUICKSTART.md** - Fast setup guide
- **README.md** - Detailed AI assistant integration
- **CHANGELOG.md** - What's new in v2.0

## Version 2.0 Highlights

### New Extraction Methods
1. `extract_data_points(text)` - Lines 167-191
2. `extract_examples(text)` - Lines 193-234
3. `extract_key_takeaways(text, title)` - Lines 236-284
4. `get_category_prompts()` - Lines 358-397

### Enhanced Methods
- `summarize_post()` - Returns 5-field dict (summary, key_points, data_points, examples, takeaways)
- `generate_markdown()` - AI-optimized output with emojis, prompts, usage guide

### Output Enhancements
- Emoji indicators for visual navigation
- Category-specific prompt suggestions
- Comprehensive AI usage guide
- Quick reference section
