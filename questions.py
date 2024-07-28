import numpy as np
import pandas as pd
from openai import OpenAI
import openai
from typing import List
from scipy import spatial
import os
import faiss
import pickle
import tiktoken
from google.cloud import secretmanager

# Get id_to_text and index
index = faiss.read_index('/app/data/faiss_index.index')
with open('/app/data/id_to_text.pkl', 'rb') as f:
    id_to_text = pickle.load(f)

tokenizer = tiktoken.get_encoding("cl100k_base")
# Function to get the secret from Google Cloud Secret Manager
def get_secret(secret_name):
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/aix-academy-chatbot/secrets/{secret_name}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

# Load OpenAI API key
try:
    os.environ['OPENAI_API_KEY'] = get_secret('openai_api_key')
    openai.api_key = os.environ['OPENAI_API_KEY']
except Exception as e:
    raise

def distances_from_embeddings(
    query_embedding: List[float],
    embeddings: List[List[float]],
    distance_metric="cosine",
    ) -> List[List]:
    """Return the distances between a query embedding and a list of embeddings.""" 
    distance_metrics = {
        "cosine": spatial.distance.cosine,
        "L1": spatial.distance.cityblock,
        "L2": spatial.distance.euclidean,
        "Linf": spatial.distance.chebyshev,
    } 

    distances = [
        distance_metrics[distance_metric](query_embedding, embedding)
        for embedding in embeddings
    ]

    return distances

def create_context(question, max_len = 1000): 
    """ 
    Create a context for a question by finding the most similar context from the dataframe 
    """ 
    # Get the embeddings for the question 
    q_embeddings = openai.embeddings.create( 
      input=question, model='text-embedding-ada-002').data[0].embedding
    q_embeddings = np.array(q_embeddings).reshape(1, -1)
    
    # Search the index
    k = 2  # Number of nearest neighbors
    distances, indices = index.search(q_embeddings, k)

    # Retrieve the corresponding text for the nearest neighbors
    context=""
    total_tokens = 0
    results = [(id_to_text[idx], distances[0][i]) for i, idx in enumerate(indices[0])]
    for i, idx in enumerate(indices[0]):
        text = id_to_text[idx]
        text_tokens = tokenizer.encode(text)
        if total_tokens + len(text_tokens) > max_len:
            break
        context += f'{text}\n'
        total_tokens += len(text_tokens)
        print(f'Text: {text}, Distance: {distances[0][i]}, Tokens: {len(text_tokens)}')
      
    # Return the context 
    return f"\n\n###\n\n{context}"


def answer_question( 
                model="gpt-4o-mini",
                question="What is the meaning of life?",
                max_len=800,
                debug=False,
                max_tokens=150,
                stop_sequence=None): 
    """ 
    Answer a question based on the most similar context from the dataframe texts 
    """ 
    context = create_context( 
      question,
      max_len=max_len,
    ) 
    
    # If debug, print the raw model response 
    if debug: 
        print("Context:\n" + context)
        print("\n\n")
    
    try: 
        # Create a completions using the question and context 
        response = openai.chat.completions.create(
            model=model,
            messages=[{
                "role":
                "user",
                "content":
                f"Answer the question based on the context below, and if the question can't be answered based on the context, say \"I don't know.\" Try to site sources to the links in the context when possible.\n\nContext: {context}\n\n---\n\nQuestion: {question}\nSource:\nAnswer:", 
            }],
            temperature=0,
            max_tokens=max_tokens,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            stop=stop_sequence,
        ) 
        return response.choices[0].message.content
    except Exception as e:
        print(e) 
        return "" 
