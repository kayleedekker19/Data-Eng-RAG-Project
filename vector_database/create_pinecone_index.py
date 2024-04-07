from pinecone import Pinecone, ServerlessSpec
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

pinecone_api_key = os.getenv("PINECONE_KEY")
index_name = os.getenv("PINECONE_INDEX_NAME")

# Initialize Pinecone
pc = Pinecone(api_key=pinecone_api_key)

# Ensure API key is correctly recognized before proceeding
if not pinecone_api_key:
    raise ValueError("Pinecone API key is missing. Please check your environment variables.")

try:
    # Step 1: Create a Pinecone instance
    # Check existing indexes
    existing_indexes = pc.list_indexes()
    print(f"Existing indexes: {existing_indexes}")

    # Define index specifications
    index_name = index_name
    dimension = 1536  # Dimension for the model you are using - OpenAI's
    metric = "cosine"  # Chosen for the use case

    # Create the index if it doesn't exist
    if index_name not in existing_indexes:
        pc.create_index(
            name=index_name,
            dimension=dimension,  # Adjust this according to your embeddings' dimensions
            metric=metric,
            spec=ServerlessSpec(
                cloud="aws",
                region="us-west-2"
            )
        )
        print("Successfully created index")
    else:
        print("Index already exists.")
except Exception as e:
    print(f"An error occurred: {e}")
