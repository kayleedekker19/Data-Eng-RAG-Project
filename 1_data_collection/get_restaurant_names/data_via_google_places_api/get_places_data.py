"""
This script was not used in the final project version. Here restaurant names are retrieved from Google Places.
I switched strategy and decided getting restaurant names from the Michelin guide increases my chances of being able to identify buyer-supplier relationships in news articles.
"""

import time
import os
import requests
import json
from google.cloud import storage
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Google Places API Configurations
PLACES_API_KEY = os.getenv("PLACES_API_KEY")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Google Cloud Storage Configurations
PROJECT_ID = os.getenv("PROJECT_ID")
BUCKET_NAME = os.getenv("BUCKET_NAME")

# Initialize Google Cloud Storage Client
storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)


# Function to search for restaurants using Google Places API
def get_all_restaurants(location, keyword="restaurant"):
    all_restaurants = []
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "key": PLACES_API_KEY,
        "location": location,
        "radius": 2000,
        "type": "restaurant",
        "keyword": keyword
    }

    while True:
        response = requests.get(url, params=params).json()

        filtered_data = []
        for restaurant in response.get("results", []):
            filtered_restaurant = {key: restaurant.get(key) for key in
                                   ["geometry", "name", "place_id", "price_level", "rating", "types",
                                    "user_ratings_total", "vicinity"] if key in restaurant}
            filtered_data.append(filtered_restaurant)

        all_restaurants.extend(filtered_data)

        next_page_token = response.get("next_page_token")
        if not next_page_token:
            break  # Break the loop if there's no next page token

        params['pagetoken'] = next_page_token
        params.pop('radius', None)  # Safely remove 'radius' if it exists, do nothing otherwise
        time.sleep(2)  # Necessary to wait for the token to become valid

    return all_restaurants


# Function to save data to Google Cloud Storage
def save_to_cloud_storage(data, file_name):
    data_str = json.dumps(data, indent=2)
    blob = bucket.blob(f"wip_supply_chain_progress/restaurants/{file_name}")
    blob.upload_from_string(data_str, content_type='application/json')
    print(f"Data saved to {BUCKET_NAME}/wip_supply_chain_progress/restaurants/{file_name}")

locations = [
    ("51.5308,-0.1238", "kings_cross"),
    ("51.5045,0.0183", "canary_wharf"),
    ("51.5095,-0.1960", "notting_hill"),
    ("51.4613,-0.1156", "brixton"),
    ("51.5433,0.0031", "stratford"),
    ("51.4214,-0.2076", "wimbledon"),
    ("51.5450,-0.0553", "hackney"),
    ("51.5074,-0.1103", "south_bank")
]

def main():
    for idx, (location, area_name) in enumerate(locations, start=1):
        print(f"Fetching restaurants for {area_name}...")
        restaurants_data = get_all_restaurants(location)
        file_name = f"restaurants_data_{area_name}.json"
        save_to_cloud_storage(restaurants_data, file_name)
        print(f"Completed {idx} of {len(locations)} areas.")

if __name__ == "__main__":
    main()
