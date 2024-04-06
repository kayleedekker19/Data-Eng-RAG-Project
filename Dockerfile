# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Install Google Cloud SDK
RUN apt-get update && apt-get install -y curl gnupg && \
    echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && \
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg  add - && \
    apt-get update && apt-get install -y google-cloud-sdk

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements_2.txt
RUN pip install --no-cache-dir -r requirements_2.txt

# Make port 80 available to the world outside this container
EXPOSE 80

# Run kfp_pipeline.py when the container launches
CMD ["python", "kfp_pipeline.py"]
