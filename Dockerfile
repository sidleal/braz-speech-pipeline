# Use the official Python 3.10 image as the base image
FROM python:3.10

# Set the working directory inside the container
WORKDIR /

RUN apt-get -y update
RUN apt-get install -y ffmpeg

# Copy the requirements.txt file and install the dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application directory into the container
COPY . .

# Define the volume mounts
VOLUME ["/data", "/logs"]

# Run the main.py file
CMD ["python", "main.py"]