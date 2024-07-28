import os
import tiktoken
from openai import OpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
import faiss
import numpy as np
import pickle
from google.cloud import storage
import openai
from google.cloud import secretmanager

# Initialize OpenAI client
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

# Initialize Google Cloud Storage client
storage_client = storage.Client()
bucket_name = 'aix-academy-chatbot-bucket'  # Replace with your bucket name
bucket = storage_client.bucket(bucket_name)

def remove_newlines(text): 
    return text.replace('\n', ' ').replace('\\n', ' ').replace('  ', ' ')

# Load the cl100k_base tokenizer which is designed to work with the ada-002 model 
tokenizer = tiktoken.get_encoding("cl100k_base")

try:
    # Create a list to store the text files 
    texts = []

    # Get all the text files from the Cloud Storage bucket
    blobs = bucket.list_blobs(prefix='text/')
    for blob in blobs:
        if blob.name.endswith('.txt'):
            # Download the content of the blob
            content = blob.download_as_text()
            # Extract the filename (URL) from the blob name
            filename = blob.name.replace('text/', '').replace('.txt', '').replace('_', '/')
            if 'users/fxa/login' in filename:
                continue
            texts.append((filename, content))

    # Create a dataframe from the list of texts 
    import pandas as pd
    df = pd.DataFrame(texts, columns=['fname', 'text']) 

    # Set the text column to be the raw text with the newlines removed 
    df['text'] = df.fname + ". " + df['text'].apply(remove_newlines)

    # Tokenize the text and save the number of tokens to a new column 
    df['n_tokens'] = df.text.apply(lambda x: len(tokenizer.encode(x)))

    # Tokenizing the text
    chunk_size = 700  # Max number of tokens 

    text_splitter = RecursiveCharacterTextSplitter(
        length_function = len,
        chunk_size = chunk_size,
        chunk_overlap = 100,
        add_start_index = False,
    ) 

    shortened = [] 

    for row in df.iterrows(): 
        if row[1]['text'] is None: 
            continue 
        if row[1]['n_tokens'] > chunk_size: 
            chunks = text_splitter.create_documents([row[1]['text']]) 
            for chunk in chunks:
                shortened.append(chunk.page_content)
        else: 
            shortened.append(row[1]['text']) 

    df = pd.DataFrame(shortened, columns=['text']) 
    df['n_tokens'] = df.text.apply(lambda x: len(tokenizer.encode(x)))

    # Create embeddings
    df['embeddings'] = df.text.apply(lambda x: openai.Embedding.create(
        input=x, model='text-embedding-ada-002').data[0].embedding)

    # Put into FAISS
    vectors = np.vstack(df['embeddings'].values).astype(np.float32)

    # Create the FAISS index
    d = vectors.shape[1]  # Dimensionality of the vectors
    index = faiss.IndexFlatL2(d)

    # Add vectors to the index
    index.add(vectors)

    id_to_text = {i: text for i, text in enumerate(df['text'])}
    
    # Create the data directory if it doesn't exist
    os.makedirs('/app/data', exist_ok=True)

    # Save FAISS index and id_to_text mapping
    faiss.write_index(index, '/app/data/faiss_index.index')
    with open('/app/data/id_to_text.pkl', 'wb') as f:
        pickle.dump(id_to_text, f)

    print(f"Successfully processed {len(texts)} documents and created FAISS index.")

except Exception as e:
    print(f"An error occurred: {str(e)}")
    raise
