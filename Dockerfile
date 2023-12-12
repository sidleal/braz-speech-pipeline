# Use a pre-built PyTorch environment with CUDA support from Nivida
FROM nvcr.io/nvidia/pytorch:23.10-py3

# Set the working directory in the container to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install Poetry
RUN pip3 install --upgrade pip \
  && pip3 install poetry

# Install dependencies using Poetry
RUN poetry config virtualenvs.create false \
  && poetry install

# Run main.py when the container launches
CMD ["python3", "main.py"]
