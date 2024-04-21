"""
This is the first RAG method. It is the most simple and flexible method and employs LangChain's PromptTemplate feature.
It sets up a pipeline to run the RAG. Guardrails are defined in the primer to prevent hallucinations.
"""
# Rag pipeline

# Import libraries
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
import os
from dotenv import load_dotenv

# Step 1: Environment variables
load_dotenv()
pinecone_api_key = os.getenv("PINECONE_KEY")
index_name = os.getenv("PINECONE_INDEX_NAME")
openai_api_key = os.getenv("OPENAI_API_KEY")


def initialize_services():
    """Initializes and returns the Pinecone index, OpenAI embeddings model, and PineconeVectorStore."""
    # Initialize Pinecone
    pc = Pinecone(api_key=pinecone_api_key)
    index = pc.Index(index_name)

    # Initialize OpenAI Embeddings Model
    embed_model = OpenAIEmbeddings(model="text-embedding-ada-002", openai_api_key=openai_api_key)

    vectorstore = PineconeVectorStore(index, embed_model, "text")
    return index, embed_model, vectorstore


def setup_rag_pipeline(vectorstore):
    """Sets up and returns the RAG pipeline components."""
    retriever = vectorstore.as_retriever(search_kwargs={"k": 10})
    llm = ChatOpenAI(model_name="gpt-4", openai_api_key=openai_api_key)

    template = """You are a highly intelligent Q&A bot designed to answer questions about restaurant supply chains.
    Use the following pieces of retrieved context to answer the question.
    If the information cannot be found in the information provided, truthfully say "I don't know".
    Please note that 'T2_Suppliers' refers to Tier 2 Suppliers, indicating they are a restaurant's suppliers' suppliers.
    No pre-amble in the answer.
    
    Question: {question}
    
    Context: {context}
    
    Answer:"""

    prompt = ChatPromptTemplate.from_template(template)

    rag_pipeline = (
            {"context": retriever, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
    )
    return rag_pipeline, retriever


def query_rag_pipeline(query, rag_pipeline, retriever):
    """Executes the RAG pipeline for a given query and returns the answers and contexts."""
    answers = rag_pipeline.invoke(query)
    contexts = [docs.page_content for docs in retriever.get_relevant_documents(query)]
    return answers, contexts


def pipeline_main(query):
    """Main function to run the RAG pipeline with a specified query."""
    _, _, vectorstore = initialize_services()
    rag_pipeline, retriever = setup_rag_pipeline(vectorstore)
    answers, contexts = query_rag_pipeline(query, rag_pipeline, retriever)
    # Instead of printing, return the answers and contexts
    return answers, contexts


if __name__ == "__main__":
    query = "What restaurants are supplied by 'Hg Walter'?"
    pipeline_main(query)
