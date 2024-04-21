"""
Here we extract clusters from the graph database with 4 or more nodes.
Then, concise statements are generated from it and saved to GCS.
These textual representations of the clusters are what will be inserted into Pinecone.
"""

from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
from collections import defaultdict
from google.cloud import storage
import json
import argparse

# Load environment variables
load_dotenv()

DATABASE_URI = os.getenv("DATABASE_URI")
NEO_USERNAME = os.getenv("NEO_USERNAME")
NEO_PASSWORD = os.getenv("NEO_PASSWORD")

driver = GraphDatabase.driver(DATABASE_URI, auth=(NEO_USERNAME, NEO_PASSWORD))

# Google Cloud Storage Configurations
PROJECT_ID = os.getenv("PROJECT_ID")
BUCKET_NAME = os.getenv("BUCKET_NAME")

# Initialize Google Cloud Storage Client
storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)

def fetch_nodes_and_relationships():
    query = """
    MATCH (n)-[r:SUPPLIES]->(m)
    RETURN id(n) AS startNodeId, id(m) AS endNodeId
    """
    with driver.session() as session:
        result = session.run(query)
        return result.data()


def find_clusters(data):
    connections = defaultdict(set)
    for item in data:
        startNodeId, endNodeId = item['startNodeId'], item['endNodeId']
        connections[startNodeId].add(endNodeId)
        connections[endNodeId].add(startNodeId)

    clusters = []
    visited = set()

    for node, neighbours in connections.items():
        if node not in visited:
            cluster = set()
            queue = [node]
            while queue:
                current = queue.pop(0)
                if current not in visited:
                    visited.add(current)
                    cluster.add(current)
                    queue.extend(connections[current] - visited)
            if len(cluster) >= 4:
                clusters.append(cluster)
    return clusters


def generate_textual_representation(cluster_nodes):
    query = """
    MATCH path = (n)-[r:SUPPLIES]->(m)
    WHERE id(n) IN $clusterNodes OR id(m) IN $clusterNodes
    RETURN labels(n) AS StartNodeType, n.name AS StartNodeName, 
           r.product AS Product, r.location AS Location,
           labels(m) AS EndNodeType, m.name AS EndNodeName
    """
    textual_representations = []
    with driver.session() as session:
        result = session.run(query, clusterNodes=list(cluster_nodes))
        for record in result:
            text = (f"A {record['StartNodeType'][0]} named {record['StartNodeName']} "
                    f"supplies {record['Product']} in the location {record['Location']} "
                    f"to a {record['EndNodeType'][0]} named {record['EndNodeName']}.")
            textual_representations.append(text)
    return textual_representations


def generate_complete_supply_chain_text():
    query = """
    MATCH (t2:T2_Supplier)-[r1:SUPPLIES]->(s:Supplier)-[r2:SUPPLIES]->(rest:Restaurant)
    RETURN t2.name AS T2SupplierName, r1.product AS T2Product, r1.location AS T2Location, 
           s.name AS SupplierName, r2.product AS Product, r2.location AS Location, 
           rest.name AS RestaurantName
    """
    chain_representations = []
    with driver.session() as session:
        result = session.run(query)
        for record in result:
            text = (
                f"A T2_Supplier named {record['T2SupplierName']} supplies {record['T2Product']} in the location {record['T2Location']} "
                f"to a Supplier named {record['SupplierName']}, this Supplier named {record['SupplierName']} then supplies "
                f"{record['Product']} in the location {record['Location']} to a Restaurant named {record['RestaurantName']}.")
            chain_representations.append(text)

    return chain_representations

def save_text_to_cloud_storage(text_data, file_name):
    blob = bucket.blob(f"vector_database_resources/textual_representations/{file_name}")
    blob.upload_from_string(text_data, content_type='text/plain')
    print(f"Text data saved to {BUCKET_NAME}/vector_database_resources/textual_representations/{file_name}")

# Main execution flow
def main(output_file_name):  # Accept the output_file_name parameter
    data = fetch_nodes_and_relationships()
    clusters = find_clusters(data)
    # all_cluster_nodes = set().union(*clusters)

    all_texts = ""

    for cluster_nodes in clusters:
        textual_representations = generate_textual_representation(cluster_nodes)
        for text in textual_representations:
            all_texts += text + "\n"

    chain_representations = generate_complete_supply_chain_text()
    for text in chain_representations:
        all_texts += text + "\n"

    # Use the output_file_name for saving the text data
    save_text_to_cloud_storage(all_texts, output_file_name)

    driver.close()

if __name__ == "__main__":
    # Setup argparse
    parser = argparse.ArgumentParser(description='Generate textual representations from Neo4j and save to GCS.')
    parser.add_argument('output_file_name', type=str, help='The name of the output file to save data to')
    args = parser.parse_args()

    # Call main with the output file name
    main(args.output_file_name)



