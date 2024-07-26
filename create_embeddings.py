import pandas as pd
import os
import tiktoken
from openai import OpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
import faiss
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 
openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) 

def remove_newlines(series): 
    series = series.str.replace('\n', ' ') 
    series = series.str.replace('\\n', ' ') 
    series = series.str.replace('  ', ' ') 
    series = series.str.replace('  ', ' ') 
    return series

try: 
    # Create a list to store the text files 
    texts=[]

    # Get all the text files in the text directory 
    for file in os.listdir("./text/"): 
        # Open the file and read the text 
        with open("./text/" + file, "r", encoding="UTF-8") as f:
            text = f.read()
            # we replace the last 4 characters to get rid of .txt, and replace _ with / to generate the URLs we scraped 
            filename = file[:-4].replace('_', '/') 
            """ 
            There are a lot of contributor.txt files that got included in the scrape, this weeds them out. There are also a lot of auth required urls that have been scraped to weed out as well 
            """  
        if filename.endswith(".txt") or 'users/fxa/login' in filename: 
            continue

        
        
        # then we replace underscores with / to get the actual links so we can cite contributions 
        texts.append( 
        (filename, text))
        
    # Create a dataframe from the list of texts 
    df = pd.DataFrame(texts, columns=['fname', 'text']) 

    # Set the text column to be the raw text with the newlines removed 
    df['text'] = df.fname + ". " + remove_newlines(df.text) 

    # Load the cl100k_base tokenizer which is designed to work with the ada-002 model 
    tokenizer = tiktoken.get_encoding("cl100k_base")
    df = pd.read_csv('./processed/scraped.csv', index_col=0)
    df.columns = ['title', 'text']

    # Tokenize the text and save the number of tokens to a new column 
    df['n_tokens'] = df.text.apply(lambda x: len(tokenizer.encode(x)))

    # Tokenizing the CSV
    chunk_size = 700  # Max number of tokens 

    text_splitter = RecursiveCharacterTextSplitter( 
        # This could be replaced with a token counting function if needed 
        length_function = len,
        chunk_size = chunk_size,
        chunk_overlap  = 100,  # No overlap between chunks 
        add_start_index = False,  # We don't need start index in this case 
    ) 

    shortened = [] 

    for row in df.iterrows(): 
        # If the text is None, go to the next row 
        if row[1]['text'] is None: 
            continue 

    # If the number of tokens is greater than the max number of tokens, split the text into chunks 
        if row[1]['n_tokens'] > chunk_size: 
            # Split the text using LangChain's text splitter 
            chunks = text_splitter.create_documents([row[1]['text']]) 

            # Append the content of each chunk to the 'shortened' list 
            for chunk in chunks:
                shortened.append(chunk.page_content)

    # Otherwise, add the text to the list of shortened texts 
        else: 
            shortened.append(row[1]['text']) 

    df = pd.DataFrame(shortened, columns=['text']) 
    df['n_tokens'] = df.text.apply(lambda x: len(tokenizer.encode(x)))

    df['embeddings'] = df.text.apply(lambda x: openai.embeddings.create(
        input=x, model='text-embedding-ada-002').data[0].embedding)

    # Put into FAISS
    import numpy as np
    vectors = np.vstack(df['embeddings'].values).astype(np.float32)

    # Create the FAISS index
    d = vectors.shape[1]  # Dimensionality of the vectors
    index = faiss.IndexFlatL2(d)

    # Add vectors to the index
    index.add(vectors)

    id_to_text = {i: text for i, text in enumerate(df['text'])}
    faiss.write_index(index, './data/faiss_index.index')

    import pickle 
    with open('./data/id_to_text.pkl', 'wb') as f:
        pickle.dump(id_to_text, f)
except Exception as e:
    logger.error(f"An error occurred: {str(e)}")
    raise