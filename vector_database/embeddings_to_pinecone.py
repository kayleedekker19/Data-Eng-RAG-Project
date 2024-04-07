from pinecone import Pinecone
import time
import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from google.cloud import storage
import argparse
from openai import OpenAI

# Step 1: Load environment variables
load_dotenv()
pinecone_api_key = os.getenv("PINECONE_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")
index_name = os.getenv("PINECONE_INDEX_NAME")
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Google Cloud Storage Configurations
PROJECT_ID = os.getenv("PROJECT_ID")
BUCKET_NAME = os.getenv("BUCKET_NAME")

# Initialize Pinecone
pc = Pinecone(api_key=pinecone_api_key)
index = pc.Index(index_name)

# Initialize OpenAI Embeddings Model
embed_model = OpenAIEmbeddings(model="text-embedding-ada-002", openai_api_key=openai_api_key)

# Step 2: Check what exists in the database
time.sleep(1)  # wait a moment for connection
print(index.describe_index_stats())
print("Successfully connected to the index")


# Step 3: Function to read data from Google Cloud Storage
def read_text_from_gcs(bucket_name, file_path):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_path)
    text_data = blob.download_as_text(encoding='utf-8')
    return text_data.splitlines()


def main(gcs_file_path):
    # Read lines from GCS
    lines = read_text_from_gcs(BUCKET_NAME, gcs_file_path)

    MODEL = "text-embedding-ada-002"

    # Step 4: Generate embeddings and import into Pinecone
    for idx, line in enumerate(lines):
        print(f"Processing line {idx + 1}/{len(lines)}")

        # Generate embedding using OpenAI
        response = openai_client.embeddings.create(
            input=[line.strip()],
            model=MODEL
        )

        embeddings = [item.embedding for item in response.data]

        vector_id = str(idx)
        embedding = embeddings[0]

        # Prepare data for insertion into Pinecone
        data = {
            "id": vector_id,
            "values": embedding,
            "metadata": {"text": line.strip()}
        }

        # Insert the data into Pinecone
        index.upsert(vectors=[data])
        print(f"Inserted line {idx + 1} into Pinecone index.")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import data into Pinecone vector database from GCS.")
    parser.add_argument('input_file_name', type=str, help="The GCS path to the input text file")
    args = parser.parse_args()

    # Adjust the path according to where the files are stored within your bucket
    gcs_file_path = f"vector_database_resources/textual_representations/{args.input_file_name}"
    main(gcs_file_path)
