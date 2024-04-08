#!/bin/bash

source .env3

# Echo start of the script
echo "Starting the KFP pipeline process..."

# Setup input and output variables
INPUT_CSV="restaurants_names_entry.csv" # Adjust this to your actual input file name, if needed
OUTPUT_PATH="processed_output" # Adjust this to your desired output path in the bucket

# Running the Python script with input and output arguments
echo "Running the pipeline with input: $INPUT_CSV and output: $OUTPUT_PATH"
python3 /Users/kayleedekker/PycharmProjects/Data-Eng-RAG-Project/vertex_ai/kfp_pipeline.py --input_csv $INPUT_CSV --output_path $OUTPUT_PATH

if [ $? -eq 0 ]; then
    echo "Pipeline completed successfully and data uploaded to: $OUTPUT_PATH"
else
    echo "Pipeline failed. Check the logs for errors."
    exit 1
fi

# chmod +x run_pipeline.sh
# ./run_pipeline.sh