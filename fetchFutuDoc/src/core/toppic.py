import requests
from bs4 import BeautifulSoup
import json
import os

def scrape_article(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        soup = BeautifulSoup(response.text, 'html.parser')

        title_tag = soup.find('h1', class_='article-title')
        title = title_tag.get_text(strip=True) if title_tag else 'No Title'

        # The main content is in a div with class 'article-detail'.
        # Inside this, the actual article content is in a div with class 'content'.
        article_detail_div = soup.find('div', class_='article-detail')
        content = 'No Content'

        if article_detail_div:
            # Remove all script and style elements
            for script_or_style in article_detail_div(['script', 'style']):
                script_or_style.decompose()

            # Decompose known irrelevant sections by their more specific selectors
            for unwanted_selector in [
                '.feedback-module',
                '.hot-market-opportunities',
                '.news-module',
                'footer',
                '.hk-cs-footer-container',
                '.article-feedback',
                '.market-opportunities-container',
                '.news-container',
                '.bottom-banner-container',
                '.right-side-bar',
                '.left-side-bar'
            ]:
                for element in soup.select(unwanted_selector):
                    element.decompose()

            # After cleaning, get the text from the 'content' div if it exists
            content_div = article_detail_div.find('div', class_='content')
            if content_div:
                content = content_div.get_text(separator='\n', strip=True)
            else:
                # Fallback to the text of the whole article-detail div if 'content' div is not found
                content = article_detail_div.get_text(separator='\n', strip=True)

        return {'title': title, 'url': url, 'content': content}
    except requests.exceptions.RequestException as e:
        print(f"Error scraping {url}: {e}")
        return None

def main():
    with open('futu_help_docs_links.txt', 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    output_dir = 'futu_help_docs'
    os.makedirs(output_dir, exist_ok=True)

    scraped_data = []
    for url in urls:
        if "/topic" not in url:
            print(f"Skipping non-article URL: {url}")
            continue

        article_data = scrape_article(url)
        if article_data:
            scraped_data.append(article_data)
            safe_title = article_data['title'].replace("/", "_").replace(":", "_").replace("\\", "_").replace("|", "_").replace("<", "_").replace(">", "_").replace("\"", "_").replace("*", "_").replace("?", "_")
            filename = os.path.join(output_dir, f"{safe_title}.json")
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(article_data, f, ensure_ascii=False, indent=4)
            print(f"Scraped and saved: {article_data['title']}")

    with open(os.path.join(output_dir, 'all_futu_help_docs.json'), 'w', encoding='utf-8') as f:
        json.dump(scraped_data, f, ensure_ascii=False, indent=4)
    print("All scraped data saved to all_futu_help_docs.json")

if __name__ == '__main__':
    main() 
