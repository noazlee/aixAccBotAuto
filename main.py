import os
import logging
import pandas as pd
import numpy as np
import openai
import asyncio
import nest_asyncio
import requests
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from questions import answer_question
import pickle
import faiss

# Initialize Flask app
app = Flask(__name__)
CORS(app)

with open('/workspace/openai_key.txt', 'r') as f:
    os.environ['OPENAI_API_KEY'] = f.read().strip()
openai.api_key = os.environ['OPENAI_API_KEY']

# Get id_to_text and index
index = faiss.read_index('/app/data/faiss_index.index')
with open('/app/data/id_to_text.pkl', 'rb') as f:
    id_to_text = pickle.load(f)

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
    "content":"You are a helpful assistant that answers questions - especially about AIX academy and AI in general. Follow the examples provided and give appropriate responses."
}]
messages.extend(examples)

logging.basicConfig(
    format='%(asctime)s - %(name)s - $(levelname)s - %(message)s',
    level=logging.INFO
)

def get_answer(question):
    return answer_question(question=question, debug=True)

def is_related_to_aix(message):
    # keywords = [
    #     "AIX Academy", "AIX", "AI Academy", "Artificial Intelligence", "Machine Learning",
    #     "Course", "Training", "Certification", "Education", "Programs",
    #     "beginner course", "intermediate course", "advanced course", "track",
    #     "curriculum", "syllabus", "material", "Learning path", "Online course",
    #     "Course modules", "Neural networks", "Deep learning", "Natural language processing",
    #     "Computer vision", "Data science", "algorithms", "Model training", "AI frameworks",
    #     "TensorFlow", "PyTorch", "Keras", "Jupyter Notebook", "Google Colab",
    #     "job", "career", "industry", "AI applications", "AI in business",
    #     "AI trends", "AI future", "AIX Academy team", "AIX Academy instructors",
    #     "AIX Academy partners", "AIX Academy community", "projects", "research",
    #     "case studies", "resources", "tutorials", "workshops", "webinars",
    #     "events"
    # ]
    # for keyword in keywords:
    #     if keyword.lower() in message.lower():
    #         return True
    return True

@app.route('/', methods=['GET'])
def hello():
    return jsonify({"message":"Hello world!"})

@app.route('/chat', methods=['POST'])
def chat():
    incoming_msg = request.json.get('message')
    print("incoming message: ***")
    print(incoming_msg)
    if not incoming_msg:
        return jsonify({"error": "No message provided"}), 400
    
    if incoming_msg == 'GREETING':
        return jsonify({"response": "Hello! I am AIX Bot, how can I assist you today?"}), 200
    
    if is_related_to_aix(incoming_msg):
        retrieval_answer = get_answer(incoming_msg)
        messages.append({"role": "user", "content": incoming_msg})
        messages.append({"role": "system", "content": f"Context: {retrieval_answer}"})
        initial_response = openai.chat.completions.create(model="gpt-4o-mini",
                                                        messages=messages)
        print("initial response: ***")
        print(initial_response.choices[0].message.content)
        initial_response_message = initial_response.choices[0].message.content
        messages.append({"role": "assistant", "content": initial_response_message})
    # else:
    #     messages.append({"role": "user", "content": incoming_msg})
    #     initial_response = openai.chat.completions.create(model="gpt-4o-mini",
    #                                                     messages=messages)
    #     print("initial response: ***")
    #     print(initial_response.choices[0].message.content)
    #     initial_response_message = initial_response.choices[0].message.content
    #     messages.append({"role": "assistant", "content": initial_response_message})

    return jsonify({"response": initial_response_message}), 200

if __name__ == '__main__':
    nest_asyncio.apply()
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
