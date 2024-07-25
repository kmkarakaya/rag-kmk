import google.generativeai as genai
from rag_kmk.vector_db import retrieve_chunks
import os


import requests

import requests

def verify_api_key(api_key):
    url = "https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": "Give me five subcategories of jazz?"}
                ]
            }
        ]
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            print("Valid Key")
            return True
        else:
            print("Invalid Key")
            return False
    except requests.RequestException:
        print("Error making the request.")
        return False










def check_environment_variables():
    GEMINI_API_KEY=None    
    # Retrieve GOOGLE_API_KEY from system environment variables
    print("Retrieving Google Gemini API Key as GEMINI_API_KEY or GOOGLE_API_KEY from system environment variables...")
    
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    # Check if GEMINI_API_KEY is not found in the environment variables
    if GEMINI_API_KEY is not None:
        print("Google Gemini API Key found in system environment variables.")
    else:
        GEMINI_API_KEY = os.getenv('GOOGLE_API_KEY')
        # Check if GOOGLE_API_KEY is not found in the environment variables
        if GEMINI_API_KEY is not None:
            print("Google Gemini API Key found in system environment variables.")
        else:
            print("Google Gemini API Key not found in system environment variables.")
    return GEMINI_API_KEY

def check_env_file():
    GEMINI_API_KEY=None
    # Retrieve GOOGLE_API_KEY from .env file
    print("Retrieving Google Gemini API Key from .env file...")
    try:
        with open('.env', 'r') as file:
            for line in file:
                if 'GEMINI_API_KEY' or 'GOOGLE_API_KEY' in line:
                    GEMINI_API_KEY = line.split('=')[1].strip()
                    print("Google Gemini API Key found in .env file.")
                    break
    except FileNotFoundError:
        print(".env file not found.")
    if GEMINI_API_KEY == None:
        print("Google Gemini API Key not found in .env file.")
    return GEMINI_API_KEY


def get_API_key():

    print("-------"*3,"LOOKING FOR GOOGLE GEMINI KEY","-------"*3, "\n")
    
    GEMINI_API_KEY=check_environment_variables()
    if GEMINI_API_KEY is not None:
        if verify_api_key(GEMINI_API_KEY):
            print("API key from environment variables is validated.")
            print("-------"*10, "\n")
            return GEMINI_API_KEY
        else:
            print("API key from environment variables is not valid. Correct it for the next time please!")
            GEMINI_API_KEY=None
    else:
        print("Not found in environment variables. Checking .env file...")

    if GEMINI_API_KEY is None:
        GEMINI_API_KEY = check_env_file()
        if verify_api_key(GEMINI_API_KEY):
            print("API key from .env file is validated.")
            print("-------"*10, "\n")
            return GEMINI_API_KEY
        else:
            print("API key from .env file is not valid. Correct it for the next time please!")
            GEMINI_API_KEY=None
    else:
        print("API key from .env file is not found. Please enter it manually.")
        


    if GEMINI_API_KEY is None:
        GEMINI_API_KEY = input("Please get & enter your Google Gemini API Key: ")
        if verify_api_key(GEMINI_API_KEY):
            print("API key from console is validated.")
            print("-------"*10, "\n")
            return GEMINI_API_KEY
        else:
            print("API key from from console is not valid. Correct it for the next time please!")
            print("Exiting the program.")
            print("-------"*10, "\n")
            exit()
            
     
    

def build_chatBot(system_instruction):
  # Retrieve GOOGLE_API_KEY from system environment variables
  gemini_api_key = get_API_key()
  genai.configure(api_key=gemini_api_key)  
  model = genai.GenerativeModel('gemini-1.5-flash-latest', system_instruction=system_instruction)
  chat = model.start_chat(history=[])
  return chat

def generate_LLM_answer(prompt, context, chat):
  response = chat.send_message( prompt + context)
  return response.text

def generateAnswer(RAG_LLM, chroma_collection,query,n_results=10, only_response=True):
    retrieved_documents= retrieve_chunks(chroma_collection, query, n_results, return_only_docs=True)
    prompt = "QUESTION: "+ query
    context = "\n EXCERPTS: "+ "\n".join(retrieved_documents)
    if not only_response:
      print("------- retrieved documents -------\n")
      for i, doc in enumerate(retrieved_documents):
        print(f"Document {i+1}:")
        print(f"\tDocument Text: {doc}")
      print("------- RAG answer -------\n")
    output = generate_LLM_answer(prompt, context, RAG_LLM)

    print('\nModel>> ',output)
    
    return output

def run_rag_pipeline(RAG_LLM,chroma_collection):
    RAG_LLM.history.clear()
    print("-------"*10, "\n")
    print("Welcome to the RAG pipeline. Please enter your question or type 'bye' to exit.")
    while True:
        question = input("\nUser>> ")
        if question == "bye":
            print("Thank you for using the service. Goodbye!")
            print("-------"*10, "\n")
            break
        else:
            generateAnswer(RAG_LLM, chroma_collection, question)
