from pinecone import Pinecone
import time
import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from google.cloud import storage

# Step 1: Load environment variables
load_dotenv()
pinecone_api_key = os.getenv("PINECONE_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")
index_name = os.getenv("PINECONE_INDEX_NAME")

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


# Step 4: Function to read data from Google Cloud Storage
def read_text_from_gcs(bucket_name, file_path):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_path)
    text_data = blob.download_as_text(encoding='utf-8')
    return text_data.splitlines()


def main():
    # File path in Google Cloud Storage
    gcs_file_path = "vector_database_resources/textual_representations/neo4j_textual_representations.txt"

    # Read lines from GCS
    lines = read_text_from_gcs(BUCKET_NAME, gcs_file_path)

    # Step 5: Generate embeddings and import into Pinecone
    for idx, line in enumerate(lines):
        print(f"Processing line {idx + 1}/{len(lines)}")

        # Generate embedding using OpenAIEmbeddings
        embedding = embed_model.embed_query(line.strip())

        # Prepare data for insertion into Pinecone
        vector_id = str(idx)  # Using line index as a unique identifier
        data = [(vector_id, embedding.tolist())]  # Convert numpy array to list for Pinecone

        # Insert the data into Pinecone
        index.upsert(vectors=data)
        print(f"Inserted line {idx + 1} into Pinecone index.")

    print("All lines processed and inserted into Pinecone.")
    pc.close()  # Close Pinecone connection


if __name__ == "__main__":
    main()
