import os
import logging
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from openai import OpenAI
from google.cloud import secretmanager
import faiss
import pickle
from questions import answer_question

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

# Initialize components
def get_secret(secret_name):
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/aix-academy-chatbot/secrets/{secret_name}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

# Initialize OpenAI client
openai_api_key = get_secret('openai_api_key')
os.environ['OPENAI_API_KEY'] = openai_api_key
openai_client = OpenAI()

# Load FAISS index and id_to_text
try:
    faiss_index = faiss.read_index('/app/data/faiss_index.index')
    with open('/app/data/id_to_text.pkl', 'rb') as f:
        id_to_text = pickle.load(f)
    logging.info("FAISS index and id_to_text loaded successfully")
except Exception as e:
    logging.error(f"Failed to load FAISS index or id_to_text: {str(e)}")
    raise

# Initialize Limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["40 per day", "20 per hour"],
    storage_uri="memory://",
)
limiter.request_filter(lambda: request.method == "OPTIONS")

def rate_limit_exceeded_handler(e):
    return jsonify({
        "error": "Rate limit exceeded",
        "message": "You have reached the maximum number of requests. Please try again later."
    }), 429

# Register the custom rate limit exceeded handler
app.register_error_handler(429, rate_limit_exceeded_handler)

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

def is_related_to_aix(message):
    return True

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

@app.route('/', methods=['GET'])
@limiter.exempt
def hello():
    return jsonify({"message":"Hello world!"})

@app.route('/chat', methods=['POST'])
@limiter.limit("8 per minute")
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
            retrieval_answer = answer_question(incoming_msg)
            logging.info(f"Retrieved answer: {retrieval_answer}")
            
            current_messages = messages.copy()
            current_messages.append({"role": "user", "content": incoming_msg})
            current_messages.append({"role": "system", "content": f"Context: {retrieval_answer}"})
            
            logging.info("Sending request to OpenAI")
            try:
                initial_response = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=current_messages
                )
                
                logging.info("Received response from OpenAI")
                initial_response_message = initial_response.choices[0].message.content
                logging.info(f"OpenAI response: {initial_response_message}")
                
                return jsonify({"response": initial_response_message}), 200
            except Exception as e:
                logging.error(f"OpenAI API error: {str(e)}")
                return jsonify({"error": "Error communicating with AI service"}), 503
        else:
            logging.warning("Message not related to AIX")
            return jsonify({"error": "Message not related to AIX"}), 400
    
    except Exception as e:
        logging.error(f"An error occurred in chat function: {str(e)}")
        return jsonify({"error": "An internal server error occurred"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logging.info(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port)