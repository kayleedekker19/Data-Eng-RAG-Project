"""
This function takes the data after NER and RE is completed.
And it writes the data into the neo4j graph database.
There are a number of careful and complex data transformations performed.
"""

# Import libraries
import json
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase, basic_auth
from google.cloud import storage
import argparse

# Load environment variables
load_dotenv()

# Neo set up
DATABASE_URI = os.getenv("DATABASE_URI")
NEO_USERNAME = os.getenv("NEO_USERNAME")
NEO_PASSWORD = os.getenv("NEO_PASSWORD")

# Connect to Neo4j
driver = GraphDatabase.driver(DATABASE_URI, auth=basic_auth(NEO_USERNAME, NEO_PASSWORD))

# Google Cloud Storage Configurations
PROJECT_ID = os.getenv("PROJECT_ID")
BUCKET_NAME = os.getenv("BUCKET_NAME")

# Initialize Google Cloud Storage Client
storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)

def clear_database():
    query = "MATCH (n) DETACH DELETE n"
    with driver.session() as session:
        session.run(query)
    print("Database cleared.")

def read_json_from_gcs(file_path):
    blob = bucket.blob(file_path)
    data = blob.download_as_text(encoding='utf-8')
    return json.loads(data)

def filter_banned_entities(data):
    """
    Filters out relationships that include any of the banned entities
    either as a Supplier or a Buyer.
    """
    banned_entities = ["Restaurants", "Customers", "Michelin Guide"]
    filtered_data = []
    for item in data:
        new_relationships = [r for r in item['relationships']
                             if r['supplier'] not in banned_entities
                             and r['buyer'] not in banned_entities]
        if new_relationships:
            item['relationships'] = new_relationships
            filtered_data.append(item)
    return filtered_data


def preprocess_data(data):
    """
    Preprocess the data to identify and update second-order relationships.
    Changes 'supplier' to 'T2_supplier' and 'buyer' to 'supplier' where applicable.
    """
    # Identify entities that are both suppliers and buyers
    data = filter_banned_entities(data)
    suppliers = set()
    buyers = set()
    for item in data:
        for relationship in item['relationships']:
            suppliers.add(relationship['supplier'])
            buyers.add(relationship['buyer'])
    second_order_entities = suppliers.intersection(buyers)
    print(second_order_entities)

    # Update the relationships accordingly
    for item in data:
        for relationship in item['relationships']:
            if relationship['buyer'] in second_order_entities:
                relationship['T2_supplier'] = relationship.pop('supplier')
                relationship['supplier'] = relationship.pop('buyer')
    return data

def create_and_execute_schema_queries():
    queries = [
        "CREATE CONSTRAINT supplier_id_uniqueness IF NOT EXISTS FOR (s:Supplier) REQUIRE s.id IS UNIQUE;",
        "CREATE CONSTRAINT buyer_id_uniqueness IF NOT EXISTS FOR (r:Restaurant) REQUIRE r.id IS UNIQUE;",
        "CREATE CONSTRAINT t2_supplier_id_uniqueness IF NOT EXISTS FOR (t:T2_Supplier) REQUIRE t.id IS UNIQUE;"
    ]
    with driver.session() as session:
        for query in queries:
            session.run(query)

def remove_apostrophes(value):
    """Removes apostrophes from a string."""
    return value.replace("'", "")


def create_cypher_queries(data):
    # Track existing entities to avoid duplicate IDs
    existing_entities = {'Supplier': {}, 'Restaurant': {}, 'T2_Supplier': {}}   # Restaurant // Buyer

    queries = []
    for item in data:
        for relationship in item['relationships']:
            # Determine entity types and handle missing 'buyer' key by checking for 'T2_supplier'
            entities = {}
            if 'supplier' in relationship:
                entities['supplier'] = 'Supplier'
            if 'buyer' in relationship:
                entities['buyer'] = 'Restaurant'    # Restaurant // Buyer
            if 'T2_supplier' in relationship:
                entities['T2_supplier'] = 'T2_Supplier'

            # Prepare the data, removing apostrophes
            for role, entity in entities.items():
                name_key = role  # 'supplier', 'buyer', or 'T2_supplier'
                name = remove_apostrophes(relationship[name_key])
                if name not in existing_entities[entity]:
                    entity_id = f"{name_key[:3].lower()}_{len(existing_entities[entity]) + 1}"
                    existing_entities[entity][name] = entity_id
                    query_entity = f"MERGE (e:{entity} {{id: '{entity_id}', name: '{name}'}})"
                    queries.append(query_entity)

            # Adjust relationship query based on available entities
            if 'T2_supplier' in entities and 'supplier' in entities:
                supplier_id = existing_entities['T2_Supplier'][remove_apostrophes(relationship['T2_supplier'])]
                buyer_id = existing_entities['Supplier'][remove_apostrophes(relationship['supplier'])]
                rel_type = 'SUPPLIES'
            elif 'supplier' in entities and 'buyer' in entities:
                supplier_id = existing_entities['Supplier'][remove_apostrophes(relationship['supplier'])]
                buyer_id = existing_entities['Restaurant'][remove_apostrophes(relationship['buyer'])]  # Restaurant // Buyer
                rel_type = 'SUPPLIES'
            else:
                continue  # Skip if the required entities for a relationship are not present

            product = remove_apostrophes(relationship.get('product', ''))
            location = remove_apostrophes(relationship.get('location', ''))
            query_rel = (
                f"MATCH (s {{id: '{supplier_id}'}}), "
                f"(b {{id: '{buyer_id}'}}) "
                f"MERGE (s)-[:{rel_type} {{product: '{product}', location: '{location}'}}]->(b)"
            )
            queries.append(query_rel)

    return queries

def execute_queries(queries):
    with driver.session() as session:
        for query in queries:
            session.run(query)

def main(file_path):
    # Clear database while testing to reset
    # clear_database()

    # Load data
    data = read_json_from_gcs(file_path)

    # Preprocess data here
    data = preprocess_data(data)

    # Create schema in Neo4j first
    create_and_execute_schema_queries()

    # Process data to generate Cypher queries
    queries = create_cypher_queries(data)

    # Execute Cypher queries to populate the Neo4j database
    execute_queries(queries)

    print("All data successfully imported into Neo4j.")

    # Close the Neo4j driver connection
    driver.close()


if __name__ == "__main__":
    # Create the parser
    parser = argparse.ArgumentParser(description='Process a file from Google Cloud Storage.')
    # Add an argument
    parser.add_argument('file_path', type=str, help='The GCS file path to process')
    # Parse the argument
    args = parser.parse_args()
    # Now use this file_path in the main function
    main(args.file_path)

# To run this script now - where we can change the inputted file path
# python transform_and_write_to_neo4j.py "processed_output/restaurant_supply_chain_relationships.json"

