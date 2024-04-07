# Step 1: Imports
import json
import os
from dotenv import load_dotenv
from langchain.chains.graph_qa.cypher_utils import CypherQueryCorrector, Schema
from langchain_openai import ChatOpenAI
from langchain_community.graphs import Neo4jGraph
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel
from langchain_core.runnables import RunnablePassthrough

# Load environment variables
load_dotenv()

DATABASE_URI = os.getenv("DATABASE_URI")
NEO_USERNAME = os.getenv("NEO_USERNAME")
NEO_PASSWORD = os.getenv("NEO_PASSWORD")
openai_api_key = os.getenv("OPENAI_API_KEY")

# Connect to Neo4j
# driver = GraphDatabase.driver(DATABASE_URI, auth=basic_auth(NEO_USERNAME, NEO_PASSWORD))
graph = Neo4jGraph(url=DATABASE_URI, username=NEO_USERNAME, password=NEO_PASSWORD)

corrector_schema = [
    # Assuming 'Supplier' nodes can supply to 'Restaurant' nodes
    Schema("Supplier", "SUPPLIES", "Restaurant"),
    # Assuming 'T2_Supplier' nodes can supply to 'Supplier' nodes
    Schema("T2_Supplier", "SUPPLIES", "Supplier")
]
cypher_validation = CypherQueryCorrector(corrector_schema)

# Step 4: LLMs
cypher_llm = ChatOpenAI(model_name="gpt-4", temperature=0.0, openai_api_key=openai_api_key)
qa_llm = ChatOpenAI(model_name="gpt-4", temperature=0.0, openai_api_key=openai_api_key)


# Step 5: Generate Cypher statement based on natural language input
cypher_template = """
Based on the Neo4j graph schema, which contains nodes representing Restaurants, Suppliers, and T2_Suppliers (Tier 2 Suppliers), 
write a Cypher query to answer the user's question. The relationships between these nodes are characterized by properties such as "product" and "location". 
A "Supplier" node represents a direct supplier to a restaurant, while a "T2_Supplier" node stands for a Tier 2 Supplier, indicating they are a supplier's supplier within the restaurant supply chains.

For the entire supply chain of a restaurant, consider both Tier 1 and Tier 2 Suppliers. Tier 1 Suppliers directly supply to the restaurant, 
and Tier 2 Suppliers supply to Tier 1 Suppliers. This chain showcases how products (e.g., ingredients) are supplied from the ground level up to the restaurant serving the final dish.

Please consider the following schema details for generating the query:
{schema}

Question: {question}
Cypher query:
"""

cypher_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Given an input question, convert it to a Cypher query. No pre-amble.",
        ),
        ("human", cypher_template),
    ]
)

cypher_response = (
    RunnablePassthrough.assign(
        schema=lambda _: graph.get_schema,
    )
    | cypher_prompt
    | cypher_llm.bind(stop=["\nCypherResult:"])
    | StrOutputParser()
)

# Step 6: Generate natural language response based on database results
response_template = """Based on the the question, Cypher query, and Cypher response, write a natural language response:
Question: {question}
Cypher query: {query}
Cypher Response: {response}"""  # noqa: E501

response_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Given an input question and Cypher response, convert it to a "
            "natural language answer. No pre-amble.",
        ),
        ("human", response_template),
    ]
)

# Step 7: Execute chain
chain = (
    RunnablePassthrough.assign(query=cypher_response)
    | RunnablePassthrough.assign(
        response=lambda x: graph.query(cypher_validation(x["query"])),
    )
    | response_prompt
    | qa_llm
    | StrOutputParser()
)


# Step 8: Typing for Input
# A Question class is defined to structure the input to this process, ensuring that the input question is properly formatted.
class Question(BaseModel):
    question: str


ground_truths = []  # Initialize empty list to store answers

# Define a list of natural language questions you want to ask
questions = [
    "What restaurants are supplied by 'Hg Walter'?",
    "Who are the tier 2 suppliers of 'The Chiltern Firehouse'?",
    "What is the entire supply chain for the restaurant 'Notto'?",
    "What are some common suppliers of 'Meat'?",
    "Which suppliers of 'Meat' are based in 'London'?"
]

# Iterate through each question and invoke the chain
for question in questions:
    # Assuming chain setup and invocation as previously described

    result = chain.invoke({"question": question})
    print(f"Question: {question}\nResult: {result}\n\n")

    # Append the answer to the ground_truths list
    ground_truths.append([result])

# Save the ground_truths list to a file
with open('ground_truth_answers.json', 'w') as f:
    json.dump(ground_truths, f, indent=4)

print("All answers saved.")