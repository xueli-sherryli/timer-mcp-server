# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy the dependency definition files
COPY pyproject.toml ./

# Create a virtual environment
RUN uv venv

# Install dependencies using uv from pyproject.toml
# Using --no-cache to reduce image size
RUN uv pip sync --no-cache pyproject.toml

# Copy the rest of the application's code
COPY main.py .

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Run main.py with uvicorn when the container launches
# The host is set to 0.0.0.0 to be accessible from outside the container
CMD ["uv", "run",  "./main.py"]
