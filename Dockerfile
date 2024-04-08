# Use an official Python runtime as a parent image
#FROM python:3.8-slim

# Use Google Cloud SDK official Docker image as a parent image
FROM gcr.io/google.com/cloudsdktool/cloud-sdk:latest

# Set the working directory in the container
WORKDIR /app

# add for gpc
ENV HOST 0.0.0.0

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements_2.txt
RUN pip install --no-cache-dir -r requirements_2.txt

# Make port 80 available to the world outside this container
#EXPOSE 80
# add for gpc
EXPOSE 8080

# Ensure run_pipeline.sh is executable
RUN chmod +x run_pipeline.sh

# Run kfp_pipeline.py when the container launches
CMD ["/bin/bash", "run_pipeline.sh", "http://*:8080"]
