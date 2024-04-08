import json
import re
import pandas as pd
from datasets import Dataset, Features, Value, Sequence
import os
from dotenv import load_dotenv

from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_recall,
    context_precision,
)

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Import the ground truths here
file_path = "../rag_with_neo4j/ground_truth_answers.json"
with open(file_path, "r") as file:
    ground_truths = json.load(file)

questions = [
        "What restaurants are supplied by 'Hg Walter'?",
        "Who are the tier 2 suppliers of 'The Chiltern Firehouse'?",
        "What is the entire supply chain for the restaurant 'Notto'?",
        "What are some common suppliers of 'Meat'?",
        "Which suppliers of 'Meat' are based in 'London'?"
    ]

### METHOD 1.
answers_1 = []
contexts_1 = []

from rag_approaches.three_rag_options.rag_pipeline.rag_pipeline_1 import pipeline_main

for query in questions:
    query_answer, query_context = pipeline_main(query)
    answers_1.append(query_answer)
    contexts_1.append(query_context)

# To dict
data_1 = {
    "question": questions,
    "answer": answers_1,
    "contexts": contexts_1,
    "ground_truths": ground_truths
}

# Convert dict to dataset
dataset_1 = Dataset.from_dict(data_1)

result_1 = evaluate(
    dataset = dataset_1,
    metrics=[
        context_precision,
        context_recall,
        faithfulness,
        answer_relevancy,
    ],
)

df_1 = result_1.to_pandas()

df_1.to_csv('ragas_rag_eval_1.csv', index=False)

print("Completed Method 1")


### METHOD 2.
from rag_approaches.three_rag_options.rag_chain.rag_chain_2 import run_full_supplier_chain

user_input_restaurant_list = [
        " ",
        "The Chiltern Firehouse", # Here we only want tier 2 suppliers
        "Notto",
        " ",
        " "
    ]

# Call the function
answers_2 = []
contexts_2 = []
for user_input_restaurant in user_input_restaurant_list:
    combined_outputs, contexts = run_full_supplier_chain(user_input_restaurant)
    if user_input_restaurant == "The Chiltern Firehouse":
        combined_outputs = combined_outputs["Tier 2 Suppliers"]   # Getting only tier 2 suppliers here

    answers_2.append(combined_outputs)
    contexts_2.append(contexts)

# To dict
data_2 = {
    "question": questions,
    "answer": answers_2,
    "contexts": contexts_2,
    "ground_truth": ground_truths  # Corrected key name here
}

# Convert dict to dataset and specify the schema explicitly
features = Features({
    'question': Value('string'),
    'answer': Value('string'),
    'contexts': Sequence(Value('string')),
    'ground_truth': Value('string'),  # Ensure this matches the expected type
})
dataset_2 = Dataset.from_dict(data_2, features=features)

result_2 = evaluate(
    dataset = dataset_2,
    metrics=[
        context_precision,
        context_recall,
        faithfulness,
        answer_relevancy,
    ],
)

df_2 = result_2.to_pandas()

df_2.to_csv('ragas_rag_eval_2.csv', index=False)

print("Completed Method 2")



### METHOD 3. Rag Memory
def extract_answers_from_log(file_path):
    answers = []  # Initialize an empty list to hold the answers
    current_answer = ""  # Initialize a variable to hold the current answer being processed
    collecting_answer = False  # A flag to track whether we're currently collecting lines for an answer

    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            if line.startswith("Q: "):  # Check if the line is the start of a new question
                if current_answer:  # If there's an answer being built, add it to the list
                    answers.append(current_answer.strip())
                    current_answer = ""  # Reset for the next answer
                collecting_answer = False  # Reset the flag as we're now at a question
            elif line.startswith("A: "):  # If the line starts with "A: ", it's the start of an answer
                collecting_answer = True  # Set the flag to start collecting answer lines
                current_answer += line[3:]  # Append the answer text, excluding "A: "
            elif collecting_answer:  # If we're in the middle of collecting an answer
                current_answer += line  # Append the line to the current answer

        # After the loop, check if there's an answer that hasn't been added to the list yet
        if current_answer:
            answers.append(current_answer.strip())

    return answers

def extract_grouped_contexts_from_file(input_file_path):
    with open(input_file_path, 'r', encoding='utf-8') as file:
        file_content = file.read()

    # This regex matches 'Q: ...' lines to group questions and their contexts.
    question_pattern = re.compile(r'Q: (.*?)\nContexts:', re.DOTALL)
    questions = question_pattern.findall(file_content)

    # This regex is for finding all 'page_content' within Document objects for each question's context.
    context_pattern = re.compile(r"Document\(page_content='(.*?)'\)", re.DOTALL)

    grouped_contexts = []

    # Split the file content by questions to separate each question's context block
    question_blocks = re.split(r'Q: .*?\nContexts:\n', file_content)[1:]  # Skip the first split part before the first 'Q:'

    for block in question_blocks:
        contexts = context_pattern.findall(block)
        grouped_contexts.append(contexts)

    return grouped_contexts


# Using the function
answers_file_path = '/7.rag_approaches/three_rag_options/conversation_log.txt'
answers_3 = extract_answers_from_log(answers_file_path)

contexts_file_path = '/7.rag_approaches/three_rag_options/contexts_log.txt'
contexts_3 = extract_grouped_contexts_from_file(contexts_file_path)


# To dict
data_3 = {
    "question": questions,
    "answer": answers_3,
    "contexts": contexts_3,
    "ground_truths": ground_truths
}

# Convert dict to dataset
dataset_3 = Dataset.from_dict(data_3)

result_3 = evaluate(
    dataset = dataset_3,
    metrics=[
        context_precision,
        context_recall,
        faithfulness,
        answer_relevancy,
    ],
)

df_3 = result_3.to_pandas()

df_3.to_csv('ragas_rag_eval_3.csv', index=False)

print("Completed Method 3")


### RAGAS evaluation

# Combine data from all methods into one list of dictionaries
# combined_data = []
# for i, question in enumerate(questions):
#     combined_data.append({
#         "method": "Method 1",
#         "question": question,
#         "answer": answers_1[i],
#         "contexts": contexts_1[i],
#         "ground_truth": ground_truths[i]
#     })
#     combined_data.append({
#         "method": "Method 2",
#         "question": question,
#         "answer": answers_2[i],
#         "contexts": contexts_2[i],
#         "ground_truth": ground_truths[i]
#     })
#     combined_data.append({
#         "method": "Method 3",
#         "question": question,
#         "answer": answers_3[i],
#         "contexts": contexts_3[i],
#         "ground_truth": ground_truths[i]
#     })
#
# for item in combined_data:
#     if isinstance(item['answer'], dict):
#         item['answer'] = json.dumps(item['answer'])
#     if not isinstance(item['ground_truth'], str):  # Ensure ground_truth is a string
#         item['ground_truth'] = json.dumps(item['ground_truth'])
#
# # Now proceed to convert to a pandas DataFrame
# df = pd.DataFrame(combined_data)
# df.to_csv('combined_data_for_ragas.csv', index=False)
