"""
This script is the second RAG method. It uses prompt chaining and LangChains LLMChain feature.
This creates a sequential flow to the LLM calls, aiming to increase the accuracy and completeness of the answers.
"""

# Import libraries
import os
from dotenv import load_dotenv
from pinecone import Pinecone
import numpy as np
from langchain import PromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.chains import LLMChain

# Load environment variables
load_dotenv()
pinecone_api_key = os.getenv("PINECONE_KEY")
index_name = os.getenv("PINECONE_INDEX_NAME")
openai_api_key = os.getenv("OPENAI_API_KEY")

# Initialize Pinecone
pc = Pinecone(api_key=pinecone_api_key)
index = pc.Index(index_name)

# Initialize OpenAI Embeddings Model
embed_model = OpenAIEmbeddings(model="text-embedding-ada-002", openai_api_key=openai_api_key)

# Initialize the LLM
llm = ChatOpenAI(model_name="gpt-4", openai_api_key=openai_api_key)

# Define the two templates
template_level1 = """"Identify and list all direct suppliers of {entity}, based on the provided supplier information. 
It's important to note that we are specifically looking for direct suppliers only, not Tier 2 Suppliers (also known as T2 Suppliers). 
The output should strictly consist of a comma-separated list of the direct suppliers' names, without any additional text or explanations.

For example, the output should look like this: 'Supplier_1, Supplier_2, ..., Supplier_n'.
Please ensure the list is formatted exactly as shown in the example, with each supplier's name separated by a comma and a space. 

Use the following supplier information to support your answer:
{supplier_info}
"""

template_level2 = """"Please determine and compile a list of all direct suppliers for {entity}, using the detailed supplier information provided. 
Focus exclusively on direct suppliers, which are specifically designated as T2_Suppliers. Direct suppliers are entities that directly provide goods or services to {entity}. 
If no T2_Supplier is found to directly supply {entity}, the response should be left blank.

For clarity, if you are asked to identify direct suppliers of Fresh Direct and you encounter information stating, 'A T2_Supplier named Sun Salads directly supplies Watercress in Dorset, UK, to a Supplier named Fresh Direct,' 
your task is to recognize 'Sun Salads' as the direct supplier to 'Fresh Direct'. Any other information is irrelevant and should not be included in your answer. 

Your response must be formatted as a comma-separated list containing the names of these direct suppliers, without including any additional text or explanations. 

Ensure your output adheres to the following format: 'Supplier_1, Supplier_2, ..., Supplier_n'. Each supplier's name should be clearly delineated, separated by a comma followed by a space. 
Use the following supplier information to support your answer:
{supplier_info}
"""

def generate_augmented_prompt(prompt, top_k=20):
    query_embedding = embed_model.embed_query(prompt)
    res = index.query(vector=query_embedding, top_k=top_k, include_metadata=True)
    contexts = [match["metadata"]["text"] for match in res.get("matches", [])]
    augmented_prompt = "\n\n---\n\n".join(contexts) + "\n\n---\n\n" + prompt
    return augmented_prompt, contexts


def generate_t1_suppliers(top_k, user_input_restaurant):
    rag_template = """List all of the suppliers of {entity}."""
    rag_prompt = PromptTemplate(input_variables=["entity"], template=rag_template)
    formatted_prompt = rag_prompt.format(entity=user_input_restaurant)
    restaurant_suppliers, contexts = generate_augmented_prompt(formatted_prompt, top_k=top_k)
    prompt = PromptTemplate(input_variables=["entity", "supplier_info"], template=template_level1)
    suppliers_output = LLMChain(llm=llm, prompt=prompt, output_key='suppliers')
    t1_output = suppliers_output.run(entity=user_input_restaurant, supplier_info=restaurant_suppliers)
    return t1_output, contexts

def generate_t2_suppliers(top_k, output=None):
    rag_template = """List all of the T2_Suppliers of {entity}."""
    rag_prompt = PromptTemplate(input_variables=["entity"], template=rag_template)
    suppliers_list = output.split(', ')
    t2_supplier_outputs = {}
    for supplier in suppliers_list:
        formatted_prompt = rag_prompt.format(entity=supplier)
        supplier_suppliers, contexts = generate_augmented_prompt(formatted_prompt, top_k=top_k)
        prompt = PromptTemplate(input_variables=["entity", "supplier_info"], template=template_level2)
        suppliers_output = LLMChain(llm=llm, prompt=prompt)
        t2_output = suppliers_output.run(entity=supplier, supplier_info=supplier_suppliers)
        t2_supplier_outputs[supplier] = t2_output
    return t2_supplier_outputs, contexts


def run_full_supplier_chain(user_input_restaurant, top_k=10):
    output, contexts_t1 = generate_t1_suppliers(top_k=top_k, user_input_restaurant=user_input_restaurant)
    t2_supplier_outputs, contexts_t2 = generate_t2_suppliers(top_k=top_k, output=output)
    # Combine now
    combined_outputs = {"Tier 1 Suppliers": output, "Tier 2 Suppliers": t2_supplier_outputs}
    combined_contexts = contexts_t1 + contexts_t2
    return combined_outputs, combined_contexts


if __name__ == "__main__":
    user_input_restaurant = input("Enter the name of the restaurant: ")
    combined_outputs, combined_contexts = run_full_supplier_chain(user_input_restaurant)
    print(f"{user_input_restaurant}'s Suppliers:", combined_outputs)
