import csv
import os
import requests
import io
import json
from google.cloud import storage
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# News API Configurations
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# Google Cloud Storage Configurations
PROJECT_ID = os.getenv("PROJECT_ID")
BUCKET_NAME = os.getenv("BUCKET_NAME")

# Initialize Google Cloud Storage Client
storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)

# Function to read Michelin star restaurant names from CSV
def read_restaurant_names_from_gcs(file_path):
    blob = bucket.blob(file_path)
    data = blob.download_as_text(encoding='utf-8')
    reader = csv.reader(io.StringIO(data))
    return [row[0] for row in reader if row]

class RateLimitException(Exception):
    pass

def fetch_articles(restaurant_name):
    url = "http://eventregistry.org/api/v1/article/getArticles"
    headers = {"Content-Type": "application/json"}
    payload = {
        "action": "getArticles",
        "keyword": [restaurant_name, "suppliers", "restaurant"],
        "keywordOper": "and",
        "articlesPage": 1,
        "articlesCount": 100,
        "articlesSortBy": "date",
        "articlesSortByAsc": False,
        "resultType": "articles",
        "dataType": ["news"],
        "apiKey": NEWS_API_KEY,
        "includeArticleTitle": True,
        "includeArticleBody": True
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json().get('articles', {}).get('results', [])
    elif response.status_code == 401:
        raise RateLimitException("API rate limit reached. Halting process to save progress.")
    else:
        print(f"Failed to retrieve articles for {restaurant_name}. Status code: {response.status_code}")
        return []

# Function to save JSON data to Google Cloud Storage
def save_json_to_cloud_storage(data, file_name):
    data_str = json.dumps(data, indent=2)
    blob = bucket.blob(f"michelin_news_data/{file_name}")
    blob.upload_from_string(data_str, content_type='application/json')
    print(f"JSON data saved to {BUCKET_NAME}/michelin_news_data/{file_name}")


def main():
    try:
        michelin_restaurants_path = "restaurant_names/michelin_restaurants.csv"
        green_michelin_restaurants_path = "restaurant_names/green_michelin_restaurants.csv"

        restaurant_names = read_restaurant_names_from_gcs(michelin_restaurants_path)
        green_restaurant_names = read_restaurant_names_from_gcs(green_michelin_restaurants_path)

        all_articles_data = []

        for idx, name in enumerate(green_restaurant_names, 1):
            print(f"Fetching articles for {name}...")
            articles = fetch_articles(name)
            for article in articles:
                # Extract and store the required information from each article
                article_data = {
                    "url": article["url"],
                    "text": article["body"],
                    "relationships": []
                }
                all_articles_data.append(article_data)

        # Repeat for other file
        for idx, name in enumerate(restaurant_names, 1):
            print(f"Fetching articles for {name}...")
            articles = fetch_articles(name)
            for article in articles:
                article_data = {
                    "url": article["url"],
                    "text": article["body"],
                    "relationships": []
                }
                all_articles_data.append(article_data)

    except RateLimitException as e:
        print(e)
        # Save the progress made so far before halting the process
        save_json_to_cloud_storage(all_articles_data, "supply_chain_news_data_partial.json")
        return  # Stop the process

    # Save the processed data to Google Cloud Storage
    save_json_to_cloud_storage(all_articles_data, "supply_chain_news_data.json")
    print(f"Processed {len(restaurant_names)} restaurant names.")

if __name__ == "__main__":
    main()


