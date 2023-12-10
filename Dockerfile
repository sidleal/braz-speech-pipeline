# Use an official CUDA runtime image
FROM wallies/python-cuda:3.10-cuda11.6-runtime

# Set the working directory in the container to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN apt-get update

# Install Poetry
RUN pip3 install poetry

# Install dependencies using Poetry
RUN poetry config virtualenvs.create false \
  && poetry install

# Make port 80 available to the world outside this container
EXPOSE 80

# Run app.py when the container launches
CMD ["python3", "main.py"]