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
    
    def extract_data_points(self, text):
        """Extract quantitative metrics and data points from text"""
        data_points = []
        
        # Patterns for metrics
        patterns = [
            r'\b(\d+)%\s+(increase|decrease|improvement|reduction|faster|slower|more|less)',
            r'\b(\d+[,.]?\d*)\s*(million|billion|thousand|k|m|b)\s+(users|events|requests|experiments)',
            r'\breduced?\s+by\s+(\d+)%',
            r'\bimproved?\s+by\s+(\d+)%',
            r'\b(\d+[,.]?\d*)\s*(ms|seconds?|minutes?|hours?)\s+(faster|slower|latency|response time)',
            r'\bfrom\s+(\d+)\s+to\s+(\d+)',
        ]
        
        sentences = re.split(r'(?<=[.!?])\s+', text)
        for sentence in sentences:
            for pattern in patterns:
                if re.search(pattern, sentence, re.IGNORECASE):
                    if len(sentence) < 200 and sentence not in data_points:
                        data_points.append(sentence.strip())
                        break
            if len(data_points) >= 5:
                break
        
        return data_points
    
    def extract_examples(self, text):
        """Extract concrete examples and use cases"""
        examples = []
        lines = text.split('\n')
        
        # Look for example indicators
        example_patterns = [
            r'for example[,:]?',
            r'for instance[,:]?',
            r'such as[,:]?',
            r'e\.g\.',
            r'example:',
            r'use case:',
            r'case study:',
        ]
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Check if line contains example indicator
            for pattern in example_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Get context: current line + next 1-2 lines if they're related
                    context = [line]
                    for j in range(i+1, min(i+3, len(lines))):
                        next_line = lines[j].strip()
                        if next_line and not next_line.startswith('##'):
                            context.append(next_line)
                        else:
                            break
                    
                    example_text = ' '.join(context)
                    if 50 <= len(example_text) <= 300:
                        examples.append(example_text)
                        break
            
            if len(examples) >= 3:
                break
        
        return examples
    
    def extract_key_takeaways(self, text, title):
        """Extract actionable takeaways and insights"""
        takeaways = []
        lines = [ln.strip() for ln in text.split('\n') if ln.strip()]
        
        # Look for conclusion/takeaway sections
        conclusion_keywords = ['conclusion', 'takeaway', 'summary', 'key insight', 'lesson learned', 'in summary']
        in_conclusion_section = False
        
        for i, line in enumerate(lines):
            # Detect conclusion sections
            if any(keyword in line.lower() for keyword in conclusion_keywords):
                in_conclusion_section = True
                continue
            
            # Extract from conclusion sections
            if in_conclusion_section:
                if line.startswith('## ') or line.startswith('### '):
                    in_conclusion_section = False
                    continue
                if re.match(r'^(?:[\-\*•]|\d+\.)\s+', line):
                    point = re.sub(r'^(?:[\-\*•]|\d+\.)\s+', '', line)
                    if 30 <= len(point) <= 200:
                        takeaways.append(point)
            
            if len(takeaways) >= 5:
                break
        
        # If no explicit takeaways found, extract actionable sentences
        if len(takeaways) < 3:
            action_patterns = [
                r'\bshould\b',
                r'\bmust\b',
                r'\brecommend\b',
                r'\bbest practice\b',
                r'\bimportant to\b',
                r'\bkey is to\b',
                r'\bmake sure\b',
            ]
            
            sentences = re.split(r'(?<=[.!?])\s+', text)
            for sentence in sentences:
                if any(re.search(pattern, sentence, re.IGNORECASE) for pattern in action_patterns):
                    if 40 <= len(sentence) <= 200 and sentence not in takeaways:
                        takeaways.append(sentence.strip())
                        if len(takeaways) >= 5:
                            break
        
        return takeaways[:5]

    def summarize_post(self, post_data):
        """Generate a comprehensive summary with examples, data points, and takeaways"""
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

        # Build comprehensive summary
        intro = next((s for s in sentences if not s.startswith('##') and len(s) > 40), '')
        second = next((s for s in sentences[1:] if not s.startswith('##') and len(s) > 40), '')
        
        summary_parts = []
        if intro:
            summary_parts.append(intro)
        if second and second != intro:
            summary_parts.append(second)
        
        summary = ' '.join(summary_parts)[:800]
        if not summary:
            summary = f"Article about {title}".strip()

        # Key points: prefer explicit bullets, then headers
        key_points = []
        for ln in lines:
            if re.match(r'^(?:[\-\*•]|\d+\.)\s+', ln):
                point = re.sub(r'^(?:[\-\*•]|\d+\.)\s+', '', ln)
                if 25 <= len(point) <= 180:
                    key_points.append(point)
            if len(key_points) >= 8:
                break
        
        if len(key_points) < 8:
            for h in headers:
                point = re.sub(r'^#+\s*', '', h)
                if 15 <= len(point) <= 120 and point not in key_points:
                    key_points.append(point)
                if len(key_points) >= 8:
                    break

        # Deduplicate key points
        seen = set()
        deduped = []
        for p in key_points:
            p = p.strip()
            if p and p.lower() not in seen:
                deduped.append(p)
                seen.add(p.lower())
        key_points = deduped[:8]
        
        # Extract additional rich content
        data_points = self.extract_data_points(text)
        examples = self.extract_examples(text)
        takeaways = self.extract_key_takeaways(text, title)

        return {
            'summary': summary,
            'key_points': key_points,
            'data_points': data_points,
            'examples': examples,
            'takeaways': takeaways
        }
    
    def get_category_prompts(self):
        """Return customized prompt suggestions for each category"""
        return {
            'A/B Testing & Experimentation': [
                "What are the best practices for designing experiments with multiple variants?",
                "How should I handle statistical significance and p-values in A/B tests?",
                "What are common pitfalls in experimentation and how can I avoid them?",
                "How do I design experiments to avoid multiple comparison problems?",
            ],
            'AI & Machine Learning': [
                "What are best practices for implementing AI features with experimentation?",
                "How can I measure and validate AI model performance in production?",
                "What are considerations for A/B testing AI-generated content?",
            ],
            'Product Analytics': [
                "What metrics should I track for [feature/product]?",
                "How do I set up analytics to measure user engagement?",
                "What are best practices for event tracking and data collection?",
            ],
            'Feature Management': [
                "How should I implement feature flags for gradual rollouts?",
                "What are best practices for feature flag lifecycle management?",
                "How do I use feature gates to minimize deployment risk?",
            ],
            'Engineering & Infrastructure': [
                "What are the performance optimization techniques used at scale?",
                "How can I improve infrastructure efficiency and reduce costs?",
                "What architecture patterns work best for high-traffic services?",
            ],
            'Case Studies & Success Stories': [
                "What lessons from [company] case study apply to my situation?",
                "How have other teams solved [specific challenge]?",
                "What outcomes can I expect from implementing [approach]?",
            ],
            'Best Practices & Guides': [
                "What is the recommended approach for [specific task]?",
                "What are the key considerations when implementing [feature]?",
                "How do I get started with [topic]?",
            ],
        }
    
    def generate_markdown(self, categorized_posts):
        """Generate comprehensive markdown output optimized for AI assistants"""
        md = ["# Statsig Blog Knowledge Base\n"]
        md.append("## Comprehensive Guide for AI-Assisted Development\n")
        md.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
        md.append(f"*Total Articles: {sum(len(posts) for posts in categorized_posts.values())}*\n")
        md.append(f"*Categories: {len(categorized_posts)}*\n")
        md.append("\n---\n")
        
        # Overview section
        md.append("\n## 📋 Overview\n")
        md.append("""
This knowledge base contains deep insights from Statsig's engineering blog, organized for maximum utility in AI-assisted development workflows. Each article includes:

- **Comprehensive summaries** with context and background
- **Concrete examples** and real-world use cases  
- **Quantitative data points** and performance metrics
- **Actionable takeaways** you can apply immediately
- **Direct source links** for deeper exploration

Use this resource to inform technical decisions, learn best practices, and understand proven patterns in experimentation, feature management, and product analytics.
""")
        
        # Table of contents with stats
        md.append("\n## 📚 Table of Contents\n")
        for category in sorted(categorized_posts.keys()):
            count = len(categorized_posts[category])
            anchor = category.lower().replace(' ', '-').replace('&', '').replace('--', '-')
            md.append(f"- [{category}](#{anchor}) — {count} article{'s' if count != 1 else ''}\n")
        
        md.append("\n---\n")
        
        # Category-specific prompts
        category_prompts = self.get_category_prompts()
        
        # Posts by category with rich formatting
        for category in sorted(categorized_posts.keys()):
            posts = categorized_posts[category]
            anchor = category.lower().replace(' ', '-').replace('&', '').replace('--', '-')
            
            md.append(f"\n## {category}\n")
            md.append(f"*{len(posts)} article{'s' if len(posts) != 1 else ''}*\n")
            
            # Add category-specific prompts
            if category in category_prompts:
                md.append("\n### 💡 Suggested Questions for This Category\n")
                for prompt in category_prompts[category]:
                    md.append(f"- {prompt}\n")
                md.append("\n")
            
            for i, post in enumerate(posts, 1):
                md.append(f"\n### {i}. {post['title']}\n")
                
                # Metadata line
                metadata = []
                if post.get('date'):
                    metadata.append(f"📅 {post['date']}")
                if post.get('author'):
                    metadata.append(f"✍️ {post['author']}")
                if metadata:
                    md.append(' | '.join(metadata) + '\n')
                
                md.append(f"\n🔗 **Source:** {post['url']}\n")
                
                # Summary
                md.append(f"\n**📖 Summary**\n\n{post['summary']}\n")
                
                # Key Points
                if post.get('key_points'):
                    md.append("\n**🎯 Key Points**\n")
                    for point in post['key_points']:
                        md.append(f"- {point}\n")
                
                # Data Points & Metrics
                if post.get('data_points'):
                    md.append("\n**📊 Data Points & Metrics**\n")
                    for dp in post['data_points']:
                        md.append(f"- {dp}\n")
                
                # Examples
                if post.get('examples'):
                    md.append("\n**💼 Examples & Use Cases**\n")
                    for example in post['examples']:
                        md.append(f"- {example}\n")
                
                # Takeaways
                if post.get('takeaways'):
                    md.append("\n**✅ Key Takeaways**\n")
                    for takeaway in post['takeaways']:
                        md.append(f"- {takeaway}\n")
                
                md.append("\n---\n")
        
        # Enhanced instructions for AI assistants
        md.append("\n## 🤖 AI Assistant Usage Guide\n")
        md.append("""
### How to Leverage This Knowledge Base

**For Users (Prompting Strategies):**

1. **Be Specific with Context**
   - ❌ "Tell me about A/B testing"
   - ✅ "Based on Statsig's A/B testing articles, what are best practices for handling multiple variants with traffic imbalance?"

2. **Reference Examples and Data**
   - ❌ "How do I optimize performance?"
   - ✅ "What performance optimization techniques does Statsig use? Include specific metrics from the engineering articles."

3. **Ask for Comparisons**
   - "Compare feature flag strategies vs. experimentation approaches mentioned in the articles"
   - "What are the tradeoffs between approaches mentioned in [Article X] vs [Article Y]?"

4. **Request Actionable Guidance**
   - "Based on the case studies, give me a step-by-step plan to implement [feature]"
   - "What are the top 5 takeaways from the product analytics category that apply to [my scenario]?"

**For AI Assistants (How to Use This Context):**

1. **Cite Sources**
   - Always reference specific articles when drawing insights
   - Include URLs so users can read full details
   - Quote data points and metrics accurately

2. **Synthesize Across Articles**
   - Combine insights from multiple articles in the same category
   - Identify patterns and common themes
   - Note when articles present different perspectives

3. **Prioritize Concrete Information**
   - Lead with examples and data points
   - Highlight actionable takeaways
   - Explain technical concepts using examples from the articles

4. **Acknowledge Limitations**
   - Note when information is dated (check article dates)
   - Indicate when a topic isn't covered in the knowledge base
   - Suggest areas where the user should consult current documentation

### Category-Specific Use Cases

""")
        
        for category in sorted(categorized_posts.keys()):
            post_count = len(categorized_posts[category])
            md.append(f"**{category}** ({post_count} article{'s' if post_count != 1 else ''})\n")
            
            if category in category_prompts:
                md.append("Example prompts:\n")
                for prompt in category_prompts[category][:2]:  # Show first 2
                    md.append(f"  - {prompt}\n")
            md.append("\n")
        
        # Quick reference
        md.append("\n### 📌 Quick Reference\n")
        md.append(f"- **Total Knowledge Base Size**: ~{sum(len(posts) for posts in categorized_posts.values())} articles\n")
        md.append(f"- **Coverage Areas**: {', '.join(sorted(categorized_posts.keys()))}\n")
        md.append(f"- **Last Updated**: {datetime.now().strftime('%Y-%m-%d')}\n")
        md.append("\n---\n")
        md.append("\n*End of Knowledge Base*\n")
        
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
