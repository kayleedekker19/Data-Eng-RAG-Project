# Import libraries
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pinecone import Pinecone
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.chains import create_retrieval_chain, create_history_aware_retriever
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

# Load environment variables
load_dotenv()
pinecone_api_key = os.getenv("PINECONE_KEY")
index_name = os.getenv("PINECONE_INDEX_NAME")
openai_api_key = os.getenv("OPENAI_API_KEY")

# Initialize global variables
chat_history = []


def initialize_services():
    pc = Pinecone(api_key=pinecone_api_key)
    index = pc.Index(index_name)
    llm = ChatOpenAI(model_name="gpt-4", openai_api_key=openai_api_key)
    embed_model = OpenAIEmbeddings(model="text-embedding-ada-002", openai_api_key=openai_api_key)
    vectorstore = PineconeVectorStore(index, embed_model, "text")
    return llm, vectorstore


def setup_chains(llm, vectorstore):
    document_prompt = ChatPromptTemplate.from_messages([
        ("system", "Answer the user's questions based on the below context:\n\n{context}"),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}")
    ])
    document_chain = create_stuff_documents_chain(llm, document_prompt)

    retriever = vectorstore.as_retriever(search_kwargs={"k": 10})
    retrieval_chain = create_retrieval_chain(retriever, document_chain)

    retriever_prompt = ChatPromptTemplate.from_messages([
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}"),
        ("user", "Given the above conversation, generate a search query to look up in order to get information relevant to the conversation")
    ])
    retriever_chain = create_history_aware_retriever(llm, retriever, retriever_prompt)
    conversational_retrieval_chain = create_retrieval_chain(retriever_chain, document_chain)

    return conversational_retrieval_chain


def ask_question(conversational_retrieval_chain, input_question):
    global chat_history

    response = conversational_retrieval_chain.invoke({
        'chat_history': chat_history,
        "input": input_question
    })

    answer = response['answer']
    contexts = response['context']
    print(f"AI: {answer}")

    chat_history.append(HumanMessage(content=input_question))
    chat_history.append(AIMessage(content=answer))

    # Save the Q&A to a file
    with open('conversation_log.txt', 'a', encoding='utf-8') as f:
        f.write(f"Q: {input_question}\nA: {answer}\n\n")

    # Save contexts to a separate file
    with open('contexts_log.txt', 'a', encoding='utf-8') as f:
        f.write(f"Q: {input_question}\nContexts:\n{contexts}\n\n")

def main():
    llm, vectorstore = initialize_services()
    conversational_retrieval_chain = setup_chains(llm, vectorstore)

    while True:
        user_input = input("Ask a question: ")
        if user_input.lower() == "quit":
            print("Exiting.")
            break
        ask_question(conversational_retrieval_chain, user_input)


if __name__ == "__main__":
    main()

# questions = [
#         "What restaurants are supplied by Hg Walter?",
#         "Who are the tier 2 suppliers of The Chiltern Firehouse?",
#         "What is the entire supply chain for the restaurant Notto?",
#         "What are some suppliers of Meat?",
#         "Which suppliers of Meat are based in London?"
#     ]