from flask import Flask, request, render_template
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

app = Flask(__name__)

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

llm, vectorstore = initialize_services()
conversational_retrieval_chain = setup_chains(llm, vectorstore)

@app.route('/')
def home():
    return render_template('index.html', chat_history=chat_history)

@app.route('/ask', methods=['POST'])
def ask():
    user_input = request.form['user_input']
    ask_question(user_input)
    return render_template('index.html', chat_history=chat_history)

def ask_question(input_question):
    global chat_history

    response = conversational_retrieval_chain.invoke({
        'chat_history': chat_history,
        "input": input_question
    })
    answer = response['answer'].replace('\n', ' ')
    print(f"AI: {answer}")

    chat_history.append(HumanMessage(content=input_question))
    chat_history.append(AIMessage(content=answer))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000, debug=True)
    print("http://localhost:4000/")
