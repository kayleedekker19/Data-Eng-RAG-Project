# Import libaries
import pandas as pd
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Load your DataFrames
df_1 = pd.read_csv('ragas_rag_eval_1.csv')
df_2 = pd.read_csv('ragas_rag_eval_2.csv')
df_3 = pd.read_csv('ragas_rag_eval_3.csv')

# Add the 'rag_approach' column to each dataframe with the specified values
df_1['rag_approach'] = "Rag Pipeline"
df_2['rag_approach'] = "Rag with Chains"
df_3['rag_approach'] = "Rag with Memory and Chains"

# Combine all dataframes into one
combined_df = pd.concat([df_1, df_2, df_3], ignore_index=True)

# Select only the specified columns to save to CSV
all_df = combined_df[["rag_approach", "question", "context_precision", "context_recall", "faithfulness", "answer_relevancy"]]

# Save the final dataframe to CSV in your directory
all_df.to_csv('combined_ragas_evaluations.csv', index=False)