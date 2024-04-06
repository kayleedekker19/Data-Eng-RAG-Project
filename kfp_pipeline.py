# Vertex AI and ML Pipelines

# Import necessary libraries
import subprocess
import os
from datetime import datetime
from google.cloud import aiplatform
from kfp.v2 import compiler
from kfp.v2.dsl import component, InputPath, OutputPath, pipeline
import kfp.dsl as dsl
import json

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Fetch API keys from environment variables
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Setup project details
PROJECT_ID = os.getenv("PROJECT_ID")
REGION = os.getenv("REGION")
BUCKET = os.getenv("BUCKET_NAME")
DATANAME = 'api-news-data'
NOTEBOOK = 'supply_chain_pipeline_notebook'
TIMESTAMP = datetime.now().strftime("%Y%m%d%H%M%S")
URI = f"gs://{BUCKET}/{DATANAME}/models/{NOTEBOOK}"
DIR = f"temp/{NOTEBOOK}"

# Ensure the directory exists
os.makedirs(DIR, exist_ok=True)

aiplatform.init(project=PROJECT_ID, location=REGION)


## Pipeline (KFP) Creation
@component(
    base_image="python:3.8",
    packages_to_install=[
        "requests",
        "google-cloud-storage",
        "kfp==2.7.0",
        "click<9,>=8.0.0",
        "docstring-parser<1,>=0.7.3",
        "kfp-pipeline-spec==0.3.0",
        "kfp-server-api<2.1.0,>=2.0.0",
        "kubernetes<27,>=8.0.0",
        "PyYAML<7,>=5.3",
        "requests-toolbelt<1,>=0.8.0",
        "tabulate<1,>=0.8.6",
        "urllib3<2.0.0",
    ]
)
def fetch_and_store_articles(
    news_api_key: str,
    project_id: str,
    bucket_name: str,
    restaurants_csv_path: str,
    output_file_path: OutputPath("json")
):
    # Import libraries
    import csv
    import json
    import requests
    from google.cloud import storage
    from io import StringIO
    storage_client = storage.Client(project=project_id)
    bucket = storage_client.bucket(bucket_name)

    def read_restaurant_names_gcs(bucket_name, restaurants_csv_path):
        blob = bucket.blob(restaurants_csv_path)
        data = blob.download_as_text()
        f = StringIO(data)
        reader = csv.reader(f)
        # next(reader, None)  # Skip the header
        return [row[0] for row in reader]


    restaurant_names = read_restaurant_names_gcs(bucket_name, restaurants_csv_path)
    all_articles_data = []

    for name in restaurant_names:
        url = "http://eventregistry.org/api/v1/article/getArticles"
        payload = {
            "keyword": [name, "suppliers", "restaurant"],
            "keywordOper": "and",
            "articlesPage": 1,
            "articlesCount": 100,
            "articlesSortBy": "date",
            "articlesSortByAsc": False,
            "resultType": "articles",
            "dataType": ["news"],
            "apiKey": news_api_key,
            "includeArticleTitle": True,
            "includeArticleBody": True
        }
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            articles = response.json().get('articles', {}).get('results', [])
            for article in articles:
                article_data = {
                    "url": article["url"],
                    "text": article["body"],
                    "relationships": []
                }
                all_articles_data.append(article_data)

    with open(output_file_path, 'w') as f:
        json.dump(all_articles_data, f, indent=2)

# This could improve with parallel processing
@component(
    packages_to_install=["google-cloud-storage", "openai", "pydantic", "langchain", "langchain-openai"],
    base_image="python:3.8"
)
def process_articles_component(
    input_json_path: InputPath('json'),
    output_json_path: OutputPath('json'),
    openai_api_key: str,
    bucket_name: str,
    project_id: str,
    output_folder: str
):
    # Import libraries
    from typing import List
    import json
    import logging
    from google.cloud import storage
    from pydantic import BaseModel, Field
    from langchain.prompts import PromptTemplate
    from langchain.output_parsers import PydanticOutputParser
    from langchain_openai import ChatOpenAI

    class Relationship(BaseModel):
        supplier: str = Field(description="Supplier Name")
        buyer: str = Field(description="Buyer Name")
        product: str = Field(description="Products involved in the transaction")
        location: str = Field(description="Supplier Location")

    class RelationshipsData(BaseModel):
        url: str = Field(description="The URL of the article")
        text: str = Field(description="The text of the article")
        relationships: List[Relationship] = Field(description="List of buyer-supplier relationships")

    logging.basicConfig(level=logging.INFO)

    # Initialize OpenAI and LangChain components securely
    try:
        model = ChatOpenAI(api_key=openai_api_key, model="gpt-3.5-turbo", temperature=0)
    except Exception as e:
        logging.error(f"Error initializing ChatOpenAI: {e}")
        raise

    prompt_template = """
    Please help identify all buyer-supplier relationships present in the provided text.
    The primary objective of this project is to pinpoint entities within the restaurant industry for NER purposes, and to delineate supply chains.
    Extract instances where one organization provides goods or services to another, requiring the naming of both parties involved.

    << FORMATTING >>
    {format_instructions}

    << INPUT >>
    {url_text}

    << OUTPUT>>
    Organize your findings into a JSON object following this structure:

    JSON
    {{
        "url": "input URL here",
        "text": "input text here",
        "relationships": [
            {{
                "supplier": "Supplier Name",
                "buyer": "Buyer Name",
                "product": "Products involved",
                "location": "Supplier Location"
            }}
            // Additional entries if multiple relationships are found
        ]
    }}
    """

    parser = PydanticOutputParser(pydantic_object=RelationshipsData)

    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=["url_text"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )

    chain = prompt | model | parser

    try:
        with open(input_json_path, 'r') as f:
            articles = json.load(f)
    except Exception as e:
        logging.error(f"Error reading input JSON from GCS: {e}")
        raise

    processed_texts = []
    for article in articles:
        try:
            processed_text = chain.invoke({"url_text": article["text"]})
            processed_texts.append(processed_text)
        except Exception as e:
            logging.warning(f"Error processing article {article['url']}: {e}")
            continue

    try:
        processed_texts_dicts = [text.dict() for text in processed_texts]
        processed_texts_json = json.dumps(processed_texts_dicts, indent=2)
        with open(output_json_path, 'w') as f:
            f.write(processed_texts_json)
        logging.info("Successfully processed articles and saved output.")
    except Exception as e:
        logging.error(f"Error saving processed texts: {e}")
        raise

@dsl.pipeline(
    name=f'kfp-{NOTEBOOK}-{DATANAME}-{TIMESTAMP}',
    pipeline_root=f'{URI}/{TIMESTAMP}/kfp/'
)
def supply_chain_pipeline(
    news_api_key: str,
    openai_api_key: str,
    project_id: str,
    bucket_name: str,
    restaurants_csv_path: str,
    output_folder: str,
):
    # Component invocation
    fetch_articles_task = fetch_and_store_articles(
        news_api_key=news_api_key,
        project_id=project_id,
        bucket_name=bucket_name,
        restaurants_csv_path=restaurants_csv_path,
    )

    # Use the output from the previous component as input for the next one
    process_articles_task = process_articles_component(
        input_json_path=fetch_articles_task.outputs['output_file_path'],
        openai_api_key=openai_api_key,
        bucket_name=bucket_name,
        project_id=project_id,
        output_folder=output_folder,
    )

## Compile Pipeline
compiler.Compiler().compile(
    pipeline_func=supply_chain_pipeline,
    package_path=f"{DIR}/{NOTEBOOK}.yaml"
)

# Move compiled pipeline files to GCS Bucket
# Use subprocess to execute gsutil command
subprocess.run(["gsutil", "cp", f"{DIR}/{NOTEBOOK}.yaml", f"{URI}/{TIMESTAMP}/kfp/"], check=True)

## Create Vertex AI Pipeline Job
# Setting variable names
PROJECT_ID = PROJECT_ID
REGION = 'us-east1'
PIPELINE_NAME = f'kfp-{NOTEBOOK}-{DATANAME}-{TIMESTAMP}'
TEMPLATE_PATH = f"{URI}/{TIMESTAMP}/kfp/{NOTEBOOK}.yaml"

# Initialize the Vertex AI client
aiplatform.init(project=PROJECT_ID, location=REGION)

# Create the pipeline job
def run_pipeline_job():
    aiplatform.init(project=PROJECT_ID, location=REGION)
    pipeline_job = aiplatform.PipelineJob(
        display_name=f'kfp-{NOTEBOOK}-{DATANAME}-{TIMESTAMP}',
        template_path=f"{URI}/{TIMESTAMP}/kfp/{NOTEBOOK}.yaml",
        parameter_values={
            'news_api_key': NEWS_API_KEY,
            'openai_api_key': OPENAI_API_KEY,
            'project_id': PROJECT_ID,
            'bucket_name': BUCKET,
            'restaurants_csv_path': 'restaurant_names/restaurants_names_entry.csv',
            'output_folder': f'{BUCKET}/processed_output',
        },
        enable_caching=False
    )
    pipeline_job.run()

# Run the pipeline job
if __name__ == "__main__":
    run_pipeline_job()