#!/usr/bin/env python3
"""
Statsig Blog Scraper & Analyzer
Scrapes blog posts, categorizes them, and generates summaries in Markdown format
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from collections import defaultdict
from urllib.parse import urljoin
import time

class StatsigBlogScraper:
    def __init__(self, base_url="https://statsig.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
    def fetch_all_posts(self):
        """Fetch all blog post links from the main blog page"""
        print("Fetching blog post list...")
        url = f"{self.base_url}/blog/all"
        response = self.session.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all blog post links
        posts = []
        links = soup.find_all('a', href=re.compile(r'^/blog/[^/]+$'))
        
        seen_urls = set()
        for link in links:
            href = link.get('href')
            if href and href != '/blog/all' and href not in seen_urls:
                full_url = urljoin(self.base_url, href)
                title = link.get_text(strip=True)
                if title and len(title) > 5:  # Filter out empty or very short titles
                    posts.append({'url': full_url, 'slug': href, 'title': title})
                    seen_urls.add(href)
        
        print(f"Found {len(posts)} blog posts")
        return posts
    
    def fetch_post_content(self, post_url):
        """Fetch individual blog post content"""
        try:
            response = self.session.get(post_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract post content
            content = {}
            
            # Try to extract from JSON-LD first
            script_tag = soup.find('script', type='application/ld+json')
            if script_tag:
                try:
                    json_data = json.loads(script_tag.string)
                    if json_data.get('@type') == 'BlogPosting':
                        content['title'] = json_data.get('headline', '')
                        content['date'] = json_data.get('datePublished', '')
                        if 'author' in json_data and isinstance(json_data['author'], dict):
                            content['author'] = json_data['author'].get('name', '')
                except:
                    pass
            
            # Fallback title extraction
            if 'title' not in content or not content['title']:
                title_tag = soup.find('h1') or soup.find('title')
                content['title'] = title_tag.get_text(strip=True) if title_tag else "Untitled"
            
            # Fallback date extraction
            if 'date' not in content or not content['date']:
                date_tag = soup.find(class_=re.compile(r'date|Date|published|Published')) or soup.find('time')
                content['date'] = date_tag.get_text(strip=True) if date_tag else ""
            
            # Fallback author extraction
            if 'author' not in content or not content['author']:
                author_tag = soup.find(class_=re.compile(r'author|Author')) or soup.find('meta', {'name': 'author'})
                if author_tag:
                    content['author'] = author_tag.get('content') if author_tag.name == 'meta' else author_tag.get_text(strip=True)
                else:
                    content['author'] = ""
            
            # Extract main content - try multiple selectors
            article = None
            
            # Try to find main content area
            for selector in ['article', '[class*="blogContent"]', '[class*="blog-content"]', 
                           '[class*="post-content"]', '[class*="postContent"]', 'main']:
                article = soup.select_one(selector)
                if article:
                    break
            
            # If still not found, look for container with h1 and subsequent content
            if not article:
                h1_tag = soup.find('h1')
                if h1_tag and h1_tag.parent:
                    article = h1_tag.parent.parent  # Go up to likely container
            
            if article:
                # Extract all text content with lightweight structure hints
                elements = article.find_all(['p', 'h2', 'h3', 'h4', 'li'])
                lines = []
                for el in elements:
                    txt = el.get_text(strip=True)
                    if not txt:
                        continue
                    if el.name == 'h2':
                        lines.append(f"## {txt}")
                    elif el.name == 'h3':
                        lines.append(f"### {txt}")
                    elif el.name == 'h4':
                        lines.append(f"#### {txt}")
                    elif el.name == 'li':
                        lines.append(f"- {txt}")
                    else:  # paragraph
                        lines.append(txt)
                content['text'] = '\n'.join(lines)
            else:
                # Last resort: get all paragraphs from body
                paragraphs = soup.find_all('p')
                content['text'] = '\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True) and len(p.get_text(strip=True)) > 30])
            
            # Extract images/examples
            images = soup.find_all('img')
            content['has_images'] = len(images) > 0
            
            # Code blocks
            code_blocks = soup.find_all(['code', 'pre'])
            content['has_code'] = len(code_blocks) > 0
            
            return content
        except Exception as e:
            print(f"Error fetching {post_url}: {e}")
            return None
    
    def categorize_post(self, post_data):
        """Categorize post based on title and content"""
        text = (post_data.get('title', '') + ' ' + post_data.get('text', '')).lower()
        
        categories = []
        
        # Define category keywords
        category_keywords = {
            'Engineering & Infrastructure': ['infrastructure', 'performance', 'optimization', 'memory', 'server', 'architecture', 'scaling', 'compute', 'gke', 'cloud', 'kubernetes'],
            'A/B Testing & Experimentation': ['experiment', 'a/b test', 'testing', 'hypothesis', 'control', 'variant', 'statistical', 'p-value', 'multiple comparison'],
            'AI & Machine Learning': ['ai', 'machine learning', 'llm', 'gpt', 'openai', 'artificial intelligence', 'model', 'ai-generated'],
            'Product Analytics': ['analytics', 'metrics', 'measurement', 'tracking', 'data', 'insights', 'count distinct'],
            'Feature Management': ['feature flag', 'feature gate', 'rollout', 'deployment', 'release'],
            'Company Updates': ['announcement', 'acquisition', 'partnership', 'funding', 'team'],
            'Case Studies & Success Stories': ['case study', 'customer', 'how we', 'lessons learned', 'story behind'],
            'Product Development': ['product', 'development', 'building', 'design', 'user experience'],
            'Data Engineering': ['warehouse', 'data pipeline', 'etl', 'data platform', 'fabric', 'microsoft'],
            'Best Practices & Guides': ['guide', 'best practice', 'how to', 'tutorial', 'tips']
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in text for keyword in keywords):
                categories.append(category)
        
        return categories if categories else ['General']
    
    def summarize_post(self, post_data):
        """Generate a richer summary that preserves main points and concrete examples"""
        text = post_data.get('text', '') or ''
        title = post_data.get('title', '') or ''

        # Normalize whitespace
        text = re.sub(r'\u00A0', ' ', text)
        text = re.sub(r'\s+\n', '\n', text)

        # Split into sentences (keep punctuation)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 0]

        # Identify section headers from structured hints we inject (##, ###)
        lines = [ln.strip() for ln in text.split('\n') if ln.strip()]
        headers = [ln for ln in lines if ln.startswith('## ') or ln.startswith('### ') or ln.startswith('#### ')]

        # Heuristics to find example/evidence sentences
        example_re = re.compile(r'\b(for example|e\.g\.|example|case (study|in point))\b', re.IGNORECASE)
        metric_re = re.compile(r'(\b\d+%\b|\b\d+\s*(ms|s|sec|seconds|minutes|hrs|hours|days)\b|\b\d+[,.]?\d*\s*(users|events|requests|experiments|variants)\b|\bimprov|increase|decreas|reduce|faster|slower\b)', re.IGNORECASE)

        intro = next((s for s in sentences if not s.startswith('##') and len(s) > 40), '')
        second = next((s for s in sentences[1:] if not s.startswith('##') and len(s) > 40), '')
        example = next((s for s in sentences if example_re.search(s)), '')
        metric = next((s for s in sentences if metric_re.search(s)), '')

        # Build summary ensuring inclusion of examples/evidence when available
        parts = []
        if intro:
            parts.append(intro)
        if second and second != intro:
            parts.append(second)
        if example and example not in parts:
            parts.append(f"Example: {example}")
        if metric and metric not in parts:
            parts.append(metric)

        summary = ' '.join(parts)
        if not summary:
            summary = f"Article about {title}".strip()
        summary = summary[:1000]

        # Key points: prefer explicit bullets, then headers, then concise sentences
        key_points = []
        # 1) Bulleted or numbered list items anywhere in the article
        for ln in lines:
            if re.match(r'^(?:[\-\*•]|\d+\.)\s+', ln):
                point = re.sub(r'^(?:[\-\*•]|\d+\.)\s+', '', ln)
                if 25 <= len(point) <= 180:
                    key_points.append(point)
            if len(key_points) >= 8:
                break
        # 2) Section headers as thematic points
        if len(key_points) < 8:
            for h in headers:
                point = re.sub(r'^#+\s*', '', h)
                if 15 <= len(point) <= 120 and point not in key_points:
                    key_points.append(point)
                if len(key_points) >= 8:
                    break
        # 3) Evidence/example sentences if still short
        if len(key_points) < 8 and example:
            ex_point = re.sub(r'^(Example:|example:)?\s*', '', example)
            key_points.append(f"Example: {ex_point}")
        if len(key_points) < 8 and metric and metric not in key_points:
            key_points.append(metric)

        # Trim and de-dup
        seen = set()
        deduped = []
        for p in key_points:
            p = p.strip()
            if p and p not in seen:
                deduped.append(p)
                seen.add(p)
        key_points = deduped[:10]

        return {
            'summary': summary,
            'key_points': key_points
        }
    
    def generate_markdown(self, categorized_posts):
        """Generate markdown output for ChatGPT/Claude"""
        md = ["# Statsig Blog Posts - Categorized & Summarized\n"]
        md.append(f"*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
        md.append(f"*Total Posts: {sum(len(posts) for posts in categorized_posts.values())}*\n")
        md.append("---\n")
        
        # Table of contents
        md.append("## Table of Contents\n")
        for category in sorted(categorized_posts.keys()):
            md.append(f"- [{category}](#{category.lower().replace(' ', '-').replace('&', '')})")
        md.append("\n---\n")
        
        # Posts by category
        for category in sorted(categorized_posts.keys()):
            posts = categorized_posts[category]
            md.append(f"\n## {category}\n")
            md.append(f"*{len(posts)} posts*\n")
            
            for i, post in enumerate(posts, 1):
                md.append(f"\n### {i}. {post['title']}\n")
                if post.get('date'):
                    md.append(f"**Date:** {post['date']}  ")
                if post.get('author'):
                    md.append(f"**Author:** {post['author']}  ")
                md.append(f"**URL:** {post['url']}\n")
                
                md.append(f"\n**Summary:**  \n{post['summary']}\n")
                
                if post.get('key_points'):
                    md.append("\n**Key Points:**\n")
                    for point in post['key_points']:
                        md.append(f"- {point}\n")
                
                md.append("\n---\n")
        
        # Add instructions section
        md.append("\n## Instructions for AI Assistant\n")
        md.append("""
### How to Use This Document

**Context:**
This document contains categorized summaries of Statsig blog posts covering experimentation, feature flags, product analytics, and engineering practices.

**When brainstorming:**
1. **Reference specific categories** when discussing related topics
2. **Cite examples** from case studies and best practices
3. **Apply patterns** from engineering and infrastructure posts
4. **Consider trade-offs** mentioned in the articles
5. **Use the key points** as starting points for deeper discussions

**Suggested prompts:**
- "Based on the A/B testing posts, what are best practices for [specific scenario]?"
- "What engineering patterns does Statsig use for [specific challenge]?"
- "Compare approaches mentioned in the feature management vs. experimentation categories"
- "What lessons from the case studies apply to [your situation]?"

**Topic areas covered:**
""")
        for category in sorted(categorized_posts.keys()):
            md.append(f"- **{category}**: {len(categorized_posts[category])} articles\n")
        
        return '\n'.join(md)
    
    def run(self, output_file='statsig_blog_summary.md', max_posts=None):
        """Main execution function"""
        print("Starting Statsig blog scraper...")
        
        # Fetch all posts
        posts = self.fetch_all_posts()
        
        if max_posts:
            posts = posts[:max_posts]
        
        # Fetch content for each post
        enriched_posts = []
        for i, post in enumerate(posts, 1):
            print(f"Processing {i}/{len(posts)}: {post['title']}")
            content = self.fetch_post_content(post['url'])
            if content:
                post.update(content)
                categories = self.categorize_post(post)
                post['categories'] = categories
                summary_data = self.summarize_post(post)
                post.update(summary_data)
                enriched_posts.append(post)
            time.sleep(0.5)  # Be respectful to the server
        
        # Categorize posts
        categorized = defaultdict(list)
        for post in enriched_posts:
            for category in post['categories']:
                categorized[category].append(post)
        
        # Generate markdown
        markdown = self.generate_markdown(categorized)
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown)
        
        print(f"\n✓ Summary saved to {output_file}")
        print(f"✓ Processed {len(enriched_posts)} posts")
        print(f"✓ Found {len(categorized)} categories")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape and summarize Statsig blog posts')
    parser.add_argument('-o', '--output', default='statsig_blog_summary.md', help='Output markdown file')
    parser.add_argument('-m', '--max-posts', type=int, help='Maximum number of posts to process')
    
    args = parser.parse_args()
    
    scraper = StatsigBlogScraper()
    scraper.run(output_file=args.output, max_posts=args.max_posts)
