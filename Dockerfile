# Use an official Python runtime as a parent image
#FROM python:3.8-slim

# Use Google Cloud SDK official Docker image as a parent image
FROM gcr.io/google.com/cloudsdktool/cloud-sdk:latest

# Arguments that can be passed at build time
ARG GCP_SA_KEY

# The environment variable for Google Cloud authentication
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/service-account.json

# Set the working directory in the container
WORKDIR /app

# Decode the service account key and save it to a file
RUN echo "$GCP_SA_KEY" | base64 --decode > ${GOOGLE_APPLICATION_CREDENTIALS}

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 8080

# Ensure run_pipeline.sh is executable
RUN chmod +x run_pipeline.sh

# Run kfp_pipeline.py when the container launches
CMD ["/bin/bash", "run_pipeline.sh"]
