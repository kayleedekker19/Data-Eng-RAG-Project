"""
This script was also not used in the final project version.
It processes the restaurant names retrieved from Google Places.
"""

import os
import io
import csv
import json
from google.cloud import storage
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Google Cloud Storage Configurations
PROJECT_ID = os.getenv("PROJECT_ID")
BUCKET_NAME = os.getenv("BUCKET_NAME")

# Initialize Google Cloud Storage Client
storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)

PREFIX = "wip_supply_chain_progress/restaurants/restaurants_data_"


def list_unique_restaurant_names():
    # List all files in the specified directory/prefix
    blobs = storage_client.list_blobs(bucket, prefix=PREFIX)
    unique_names = set()

    for blob in blobs:
        # Download the blob to a bytes object
        blob_data = blob.download_as_bytes()
        # Deserialize the bytes object back into Python objects (dicts and lists)
        data = json.loads(blob_data)

        # Extract and process the name of each restaurant
        for restaurant in data:
            name = restaurant.get('name', '')
            unique_names.add(name)

    # Now, unique_names contains all unique base names of restaurants
    # Save these names to a CSV file in GCS
    save_to_cloud_storage_csv(unique_names, 'google_places_api_restaurants.csv')


def save_to_cloud_storage_csv(data, file_name):
    # Using StringIO to create a file-like object in memory
    output = io.StringIO()
    writer = csv.writer(output)

    for name in sorted(data):  # Sorting to have a predictable order
        writer.writerow([name])

    # Move back to the start of the file-like object
    output.seek(0)

    # Create a new blob in GCS and upload the file-like object's content
    blob = bucket.blob(f"restaurant_names/{file_name}")
    blob.upload_from_string(output.getvalue(), content_type='text/csv')
    print(f"Data saved to {BUCKET_NAME}/restaurant_names/{file_name}")


if __name__ == "__main__":
    list_unique_restaurant_names()
