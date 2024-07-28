FROM python:3.10

# Install Chrome and chromedriver
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update && apt-get install -y \
    google-chrome-stable \
    && wget -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE)/chromedriver_linux64.zip \
    && unzip /tmp/chromedriver.zip chromedriver -d /usr/local/bin/ \
    && rm /tmp/chromedriver.zip

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Ensure the data directory exists
RUN mkdir -p /app/data

# Copy FAISS index and id_to_text files
COPY ./data/faiss_index.index /app/data/
COPY ./data/id_to_text.pkl /app/data/

# Debug: List contents of the data directory
RUN ls -la /app/data

# Copy the rest of your code
COPY . .

# Command to run the application
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "main:app"]
