"""
This script extracts the names of Michelin Restaurants using scraping as the data retrieval method.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import csv
import re
import time
import io
import os
from google.cloud import storage
from dotenv import load_dotenv


# Create a ChromeOptions object and add the headless argument
chrome_options = Options()
chrome_options.add_argument("--headless")

# Setup WebDriver with headless option
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# List of URLs to scrape
urls = [
    'https://guide.michelin.com/se/en/greater-london/london/restaurants/all-starred?sort=distance',
    'https://guide.michelin.com/se/en/greater-london/london/restaurants/all-starred/page/2?sort=distance',
    'https://guide.michelin.com/se/en/greater-london/london/restaurants/all-starred/page/3?sort=distance',
    'https://guide.michelin.com/se/en/greater-london/london/restaurants/all-starred/page/4?sort=distance',
]

restaurants = []

for url in urls:
    driver.get(url)
    time.sleep(5)  # Wait for page to load and JavaScript to render the content

    # Click the "Agree and close" button on the cookie consent dialog
    try:
        consent_button = driver.find_element(By.ID, "didomi-notice-agree-button")
        consent_button.click()
        time.sleep(2)  # Wait a bit for the dialog to close and the page to update
    except Exception as e:
        print("Consent dialog handling error:", e)

    # Extract the restaurant names
    restaurant_divs = driver.find_elements(By.CSS_SELECTOR, 'div.col-md-6.col-lg-4.col-xl-3 a.link')
    for div in restaurant_divs:
        href = div.get_attribute('href')
        if href and 'restaurant' in href:
            restaurant_name = href.split('/')[-1].replace('-', ' ').title()
            if restaurant_name.endswith(" S"):
                restaurant_name = restaurant_name[:-2] + "'s"

            restaurant_name = re.sub(r'\d{5,}', '', restaurant_name).strip()
            restaurants.append(restaurant_name)

driver.quit()


# Save that into GCS
# Load environment variables
load_dotenv()
PROJECT_ID = os.getenv("PROJECT_ID")
BUCKET_NAME = os.getenv("BUCKET_NAME")

# Initialize Google Cloud Storage Client
storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)

def save_to_cloud_storage_csv(data, file_name):
    # Using StringIO to create a file-like object in memory
    output = io.StringIO()
    writer = csv.writer(output)

    for name in data:
        writer.writerow([name])

    # Move back to the start of the file-like object
    output.seek(0)

    # Create a new blob in GCS and upload the file-like object's content
    blob = bucket.blob(f"restaurant_names/{file_name}")
    blob.upload_from_string(output.getvalue(), content_type='text/csv')
    print(f"Data saved to {BUCKET_NAME}/restaurant_names/{file_name}")


# Call the function to save your data to GCS
save_to_cloud_storage_csv(restaurants, 'michelin_restaurants.csv')

print("Data saved to 'michelin_restaurants.csv'")

