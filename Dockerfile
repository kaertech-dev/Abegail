# Use an official Python runtime as the base image
FROM python:3.13.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

COPY run-gunicorn.service /etc/systemd/system

RUN sudo systemctl enable run-gunicorn

# Update package index
RUN apt-get upgrade && apt-get update

# Download packages
RUN apt-get install -y sudo curl zstd nano vim git ffmpeg libsm6 libxext6 net-tools iputils-ping

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install ollama
RUN curl -fsSL https://ollama.ai/install.sh | sh

# Download Deepseek model
RUN ollama serve & sleep 10 && ollama pull deepseek-r1:8b

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Define environment variable
ENV ACTIVITY_API_URL=http://192.168.20.200/activity/api/operator_today
ENV PRODUCTIVITY_API=http://192.168.20.200/productivity/api/operator_today

RUN mkdir ./csv_files/ ./voices_trained/ ./speechlogs/ ./webcam ./known_faces

RUN touch face_detection_logs.txt knowledge_base.json speechRecogLogs.txt

# Run gunicorn when the container launches
CMD ["sudo","systemctl","start","run-gunicorn"]