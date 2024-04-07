#!/bin/bash

set -e  # Exit immediately if a command exits with a non-zero status.

source .env2

#### Script 1
echo "Starting data processing and writing to Neo4j..."
GCS_FILE_PATH="processed_output/restaurant_supply_chain_relationships.json"
python /Users/kayleedekker/PycharmProjects/Data-Eng-RAG-Project/graph_database/transform_and_write_to_neo4j.py "$GCS_FILE_PATH"
if [ $? -eq 0 ]; then
    echo "Data processing and writing to Neo4j completed."
else
    echo "Error in processing data for Neo4j. Exiting..."
    exit 1
fi

#### Script 2
echo "Uploading relevant text data from graph database to GCS..."
OUTPUT_FILE_NAME="neo4j_textual_representations_2.txt"
python /Users/kayleedekker/PycharmProjects/Data-Eng-RAG-Project/vector_database/get_relevant_clusters.py "$OUTPUT_FILE_NAME"
if [ $? -eq 0 ]; then
    echo "Relevant text data from graph database uploaded to GCS."
else
    echo "Error uploading data to GCS. Exiting..."
    exit 1
fi

#### Script 3
echo "Importing data into Pinecone..."
python /Users/kayleedekker/PycharmProjects/Data-Eng-RAG-Project/vector_database/embeddings_to_pinecone.py "$OUTPUT_FILE_NAME"
if [ $? -eq 0 ]; then
    echo "Data imported into Pinecone."
else
    echo "Error importing data into Pinecone. Exiting..."
    exit 1
fi

# chmod +x submit_all_scripts.sh
# ./submit_all_scripts.sh