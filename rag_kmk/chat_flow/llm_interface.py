import google.generativeai as genai
from rag_kmk.vector_db import retrieve_chunks
import os


def build_chatBot(system_instruction):
  # Retrieve GOOGLE_API_KEY from system environment variables
  print("Retrieving Google Gemini API Key as GEMINI_API_KEY from system environment variables...")
  GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
  # Check if GOOGLE_API_KEY is not found in the environment variables
  if GEMINI_API_KEY is not None:
    print("Google Gemini API Key found in system environment variables.")
  else:
    print("Google Gemini API Key not found in system environment variables.")
    GEMINI_API_KEY = input("Please enter your Google Gemini API Key: ")
  

  
  genai.configure(api_key=GEMINI_API_KEY)  
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
      print("------- retreived documents -------\n")
      for i, doc in enumerate(retrieved_documents):
        print(f"Document {i+1}:")
        print(f"\tDocument Text: {doc}")
      print("------- RAG answer -------\n")
    output = generate_LLM_answer(prompt, context, RAG_LLM)

    print('\nModel: ',output)
    
    return output

def run_rag_pipeline(RAG_LLM,chroma_collection):
    RAG_LLM.history.clear()
    print("-------"*10, "\n")
    print("Welcome to the RAG pipeline. Please enter your question or type 'bye' to exit.")
    while True:
        question = input("\nUser: ")
        if question == "bye":
            print("Thank you for using the service. Goodbye!")
            print("-------"*10, "\n")
            break
        else:
            generateAnswer(RAG_LLM, chroma_collection, question)
