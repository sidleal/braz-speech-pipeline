# Use an official Python runtime with CUDA support as a parent image
FROM nvidia/cuda:11.0-base-ubuntu20.04

# Set the working directory in the container to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN apt-get update && apt-get install -y \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip3 install poetry

# Install dependencies using Poetry
RUN poetry config virtualenvs.create false \
  && poetry install

# Make port 80 available to the world outside this container
EXPOSE 80

# Run app.py when the container launches
CMD ["python3", "main.py"]