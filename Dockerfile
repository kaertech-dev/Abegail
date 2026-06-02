# Use an official Python runtime as the base image
FROM python:3.13.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

RUN apt-get update

RUN apt-get install sudo curl ffmpeg libsm6 libxext6 net-tools iputils-ping ca-certificates gnupg2 -y

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# RUN curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

# RUN curl -sL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
#     sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
#     sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# RUN apt-get update

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Define environment variable
ENV ACTIVITY_API_URL=http://192.168.20.200/activity/api/operator_today
ENV PRODUCTIVITY_API=http://192.168.20.200/productivity/api/operator_today

# Run gunicorn when the container launches
CMD ["gunicorn","-b","0.0.0.0:8080","app:app"]