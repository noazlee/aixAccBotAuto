import os
import logging
import pandas as pd
import numpy as np
import openai
from openai import OpenAI
import asyncio
import nest_asyncio
import requests
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from google.cloud import secretmanager
from questions import answer_question
import pickle
import faiss
import sys

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logging.info("Application starting...")

# Global variables
index = None
id_to_text = None

# Function to get the secret from Google Cloud Secret Manager
def get_secret(secret_name):
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/aix-academy-chatbot/secrets/{secret_name}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

# Load OpenAI API key
try:
    openai_api_key = get_secret('openai_api_key')
    os.environ['OPENAI_API_KEY'] = openai_api_key  # Set the environment variable
    client = OpenAI()  # This will now use the environment variable
except Exception as e:
    print(f"Error accessing secret: {str(e)}")
    raise

# Load FAISS index and id_to_text
try:
    index = faiss.read_index('/app/data/faiss_index.index')
    with open('/app/data/id_to_text.pkl', 'rb') as f:
        id_to_text = pickle.load(f)
    logging.info("FAISS index and id_to_text loaded successfully")
except Exception as e:
    logging.error(f"Failed to load FAISS index or id_to_text: {str(e)}")
    raise

examples = [
    {"role": "user", "content": "What is AIX?"},
    {"role": "assistant", "content": "AIX is a series of courses and training programs focused on artificial intelligence and machine learning, provided by AIX Academy under its parent company GradientX."},
    {"role": "user", "content": "Can you tell me about the beginner course?"},
    {"role": "assistant", "content": "The beginner course at AIX Academy covers the basics of artificial intelligence, including fundamental concepts, algorithms, and practical applications."},
    {"role": "user", "content": "What is AI?"},
    {"role": "assistant", "content": "Artificial Intelligence (AI) refers to the simulation of human intelligence in machines that are programmed to think and learn like humans. These machines can perform tasks that typically require human intelligence, such as visual perception, speech recognition, decision-making, and language translation. To learn more about AI and AI Engineering to make chatbots like me, consider looking into AIX!"},
    {"role": "user", "content": "What are LLMS?"},
    {"role": "assistant", "content": "Large language models (LLMs) are a category of foundation models trained on immense amounts of data making them capable of understanding and generating natural language and other types of content to perform a wide range of tasks. Learn more about LLMs and how to further utilize them with AIX."}
]

messages = [{
    "role":"system",
    "content":"You are a helpful assistant that answers questions - especially about AIX academy and AI in general. Follow the examples provided and give appropriate responses. Try to limit responses to 80 words."
}]
messages.extend(examples)

logging.basicConfig(
    format='%(asctime)s - %(name)s - $(levelname)s - %(message)s',
    level=logging.INFO
)

def get_answer(question):
    return answer_question(question=question, debug=True)

def is_related_to_aix(message):
    return True

@app.route('/', methods=['GET'])
def hello():
    return jsonify({"message":"Hello world!"})

@app.route('/chat', methods=['POST'])
def chat():
    try:
        logging.info("Received chat request")
        incoming_msg = request.json.get('message')
        logging.info(f"Incoming message: {incoming_msg}")
        
        if not incoming_msg:
            logging.warning("No message provided")
            return jsonify({"error": "No message provided"}), 400
        
        if incoming_msg == 'GREETING':
            logging.info("Responding with greeting")
            return jsonify({"response": "Hello! I am AIX Bot, how can I assist you today?"}), 200
        
        if is_related_to_aix(incoming_msg):
            logging.info("Message is related to AIX, generating answer")
            retrieval_answer = get_answer(incoming_msg)
            logging.info(f"Retrieved answer: {retrieval_answer}")
            
            current_messages = messages.copy()
            current_messages.append({"role": "user", "content": incoming_msg})
            current_messages.append({"role": "system", "content": f"Context: {retrieval_answer}"})
            
            logging.info("Sending request to OpenAI")
            try:
                initial_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=current_messages
                )
                
                logging.info("Received response from OpenAI")
                initial_response_message = initial_response.choices[0].message.content
                logging.info(f"OpenAI response: {initial_response_message}")
                
                return jsonify({"response": initial_response_message}), 200
            except openai.APIError as e:
                logging.error(f"OpenAI API error: {str(e)}")
                return jsonify({"error": "Error communicating with AI service"}), 503
            except Exception as e:
                logging.error(f"Unexpected error in OpenAI request: {str(e)}")
                return jsonify({"error": "An unexpected error occurred"}), 500
        else:
            logging.warning("Message not related to AIX")
            return jsonify({"error": "Message not related to AIX"}), 400
    
    except Exception as e:
        logging.error(f"An error occurred in chat function: {str(e)}")
        return jsonify({"error": "An internal server error occurred"}), 500
if __name__ == '__main__':
    nest_asyncio.apply()
    port = int(os.environ.get('PORT', 8080))
    logging.info(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port)
