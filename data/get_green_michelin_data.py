from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import csv
import time
import re

# Create a ChromeOptions object and add the headless argument
chrome_options = Options()
chrome_options.add_argument("--headless")

# Setup WebDriver with headless option
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# List of URLs to scrape
urls = [
    'https://guide.michelin.com/se/en/restaurants/sustainable_gastronomy?q=United+Kingdom',
    'https://guide.michelin.com/se/en/restaurants/sustainable_gastronomy/page/2?q=United+Kingdom'
]

green_restaurants = []

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
            green_restaurants.append(restaurant_name)

driver.quit()

# Save to CSV
with open('green_michelin_restaurants.csv', 'w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(['Green Restaurant Name'])
    for name in green_restaurants:
        writer.writerow([name])

print("Data saved to 'green_michelin_restaurants.csv'")

