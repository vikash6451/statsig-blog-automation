# Statsig Blog Automation Workflow

## Overview
Automated workflow to scrape, categorize, and summarize Statsig blog posts for use in ChatGPT Projects or Claude Skills.

## Files Created

1. **`statsig_blog_scraper.py`** - Main Python scraper script
2. **`statsig_blog_summary.md`** - Generated output (331 posts, 2.2MB, 10 categories)
3. **`requirements.txt`** - Python dependencies

## Output Statistics

- **Total Posts**: 331 blog posts
- **Categories**: 10 (A/B Testing, AI/ML, Engineering, Analytics, etc.)
- **File Size**: 2.2MB markdown
- **Lines**: 63,298 lines
- **Generated**: 2025-11-05

## Categories Included

1. **A/B Testing & Experimentation** (309 posts)
2. **AI & Machine Learning** (323 posts)
3. **Best Practices & Guides** (185 posts)
4. **Case Studies & Success Stories** (195 posts)
5. **Company Updates** (254 posts)
6. **Data Engineering** (92 posts)
7. **Engineering & Infrastructure** (216 posts)
8. **Feature Management** (162 posts)
9. **Product Analytics** (306 posts)
10. **Product Development** (302 posts)

*Note: Posts can appear in multiple categories*

## Usage

### Running the Scraper

```bash
# Scrape all posts (default output: statsig_blog_summary.md)
python3 statsig_blog_scraper.py

# Custom output file
python3 statsig_blog_scraper.py -o my_summary.md

# Limit number of posts (for testing)
python3 statsig_blog_scraper.py -m 50
```

### Using with ChatGPT Projects

1. **Upload the markdown file**:
   - Go to ChatGPT → Projects → Create New Project
   - Name it "Statsig Knowledge Base"
   - Upload `statsig_blog_summary.md` as a project file

2. **Add custom instructions** (optional):
   ```
   This project contains comprehensive summaries of Statsig blog posts 
   covering experimentation, feature flags, and product analytics. 
   
   When asked about product development, A/B testing, or engineering 
   patterns, reference specific articles from this knowledge base.
   ```

3. **Example prompts**:
   - "Based on the A/B testing articles, what are best practices for reducing false positives?"
   - "Summarize the engineering approaches Statsig uses for performance optimization"
   - "What case studies show successful implementation of feature flags?"

### Using with Claude Projects (Artifacts/Skills)

1. **Create a new Project**:
   - Go to claude.ai → Projects
   - Create "Statsig Blog Reference"
   - Add `statsig_blog_summary.md` to project knowledge

2. **Set project instructions**:
   ```
   You have access to categorized summaries of 331 Statsig blog posts.
   
   When discussing:
   - A/B testing: Reference the experimentation category
   - Performance: Check engineering & infrastructure posts
   - AI/ML topics: Refer to the AI & Machine Learning section
   
   Always cite the specific blog post when providing information.
   ```

3. **Usage in conversations**:
   - Start new chats within this project
   - Claude will have context about all blog posts
   - Ask for comparisons, summaries, or specific recommendations

## Script Features

### What it does:
- ✅ Scrapes all blog posts from statsig.com/blog/all
- ✅ Extracts title, author, date, and content
- ✅ Auto-categorizes posts by topic
- ✅ Generates summaries and key points
- ✅ Creates markdown output with table of contents
- ✅ Includes usage instructions for AI assistants
- ✅ Rate-limits requests (0.5s delay between posts)

### Content Extraction:
- JSON-LD structured data (primary)
- HTML fallback parsing
- Supports multiple content layouts
- Extracts paragraphs, headers, and lists

### Categorization:
Uses keyword matching across 10 categories based on:
- Title content
- Body text
- Topic keywords
- Technical terms

## Updating the Summary

To refresh with new blog posts:

```bash
# Re-run the scraper
python3 statsig_blog_scraper.py

# This will overwrite statsig_blog_summary.md with updated content
```

Recommended: Run monthly or quarterly to capture new posts.

## Customization

### Adding New Categories

Edit the `categorize_post()` method in the script:

```python
category_keywords = {
    'Your New Category': ['keyword1', 'keyword2', 'keyword3'],
    # ... existing categories
}
```

### Adjusting Summary Length

Modify the `summarize_post()` method:

```python
# Change number of sentences in summary
summary = '. '.join([s.strip() for s in sentences[:5]])  # Was 3

# Change number of key points
key_points = key_points[:10]  # Was 5
```

### Filtering Posts

Add filters in the `run()` method:

```python
# Example: Only posts from 2024
posts = [p for p in posts if '2024' in p.get('date', '')]

# Example: Only AI-related posts
enriched_posts = [p for p in enriched_posts if 'AI & Machine Learning' in p['categories']]
```

## Troubleshooting

### SSL Warnings
```
NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+
```
This is a warning, not an error. The script will still work. To fix:
```bash
pip3 install --upgrade urllib3 requests
```

### Empty Summaries
If posts show generic summaries like "Article about [title]":
- The blog's HTML structure may have changed
- Check and update the content extraction selectors
- Test with: `python3 statsig_blog_scraper.py -m 5` and review output

### Rate Limiting / 429 Errors
If you get rate limited:
- Increase delay: Change `time.sleep(0.5)` to `time.sleep(1.0)`
- Run in smaller batches: Use `-m` flag to limit posts

## Advanced Usage

### Export to JSON

Modify the script to also output JSON:

```python
import json

# In the run() method, before generating markdown:
with open('statsig_posts.json', 'w') as f:
    json.dump(enriched_posts, f, indent=2)
```

### Filter by Date Range

```python
from datetime import datetime

# In run() method after enriching posts:
start_date = datetime(2024, 1, 1)
enriched_posts = [
    p for p in enriched_posts 
    if datetime.fromisoformat(p['date'][:10]) >= start_date
]
```

### Integration with LLM APIs

For better summarization, integrate OpenAI or Anthropic APIs:

```python
import openai

def summarize_with_llm(text):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{
            "role": "user",
            "content": f"Summarize this blog post in 3 sentences with 5 key points:\\n\\n{text[:3000]}"
        }]
    )
    return response.choices[0].message.content
```

## Best Practices for AI Brainstorming

### In ChatGPT Projects:
1. **Ask specific questions**: "What do the case studies say about reducing experiment runtime?"
2. **Request comparisons**: "Compare the approaches in the top 3 A/B testing articles"
3. **Deep dives**: "Explain the engineering behind count distinct implementation"

### In Claude Projects:
1. **Use categories**: "Review all AI & Machine Learning posts and identify common themes"
2. **Synthesis**: "Create a best practices guide from the top 10 experimentation posts"
3. **Application**: "How would the patterns from post X apply to [my situation]?"

### For Both:
- Reference specific post titles when discussing details
- Ask for evidence/citations from the knowledge base
- Request cross-category insights
- Use for competitive analysis and trend identification

## Maintenance

### Regular Updates
- Run monthly to capture new posts
- Check for HTML structure changes if errors occur
- Update categories as new topics emerge

### Version Control
Consider tracking changes:
```bash
git add statsig_blog_summary.md
git commit -m "Update: $(date +%Y-%m-%d) - $(grep 'Total Posts' statsig_blog_summary.md)"
```

## License & Attribution

This is an automated scraper for personal/educational use. All blog content copyright belongs to Statsig.

When using insights from these posts:
- Cite the original blog post URL
- Attribute ideas to Statsig
- Link back to statsig.com/blog

## Support

For issues with:
- **The scraper**: Check HTML selectors and BeautifulSoup queries
- **ChatGPT/Claude**: Refer to their respective documentation
- **Statsig blog content**: Visit statsig.com/blog

---

**Created**: 2025-11-05  
**Last Updated**: 2025-11-05  
**Version**: 1.0
