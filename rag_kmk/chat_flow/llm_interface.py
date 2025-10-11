from google import genai as genai
from google.api_core import exceptions
from google.genai import types
from rag_kmk.vector_db import retrieve_chunks
import os
import requests
from rag_kmk import CONFIG   

# Module-level singletons to hold the genai client and chat so the underlying
# httpx client stays alive for the lifetime of the process. Creating many
# short-lived genai.Client instances can lead to the "client has been closed"
# RuntimeError coming from httpx when the SDK's internal client gets closed.
_GLOBAL_GENAI_CLIENT = None
_GLOBAL_CHAT = None


def verify_api_key(api_key: str) -> bool:
    """
    Validates a Google Gemini API key using the official SDK.
    Returns True if valid, False if invalid or error occurs.
    """
    try:
        # Initialize client (will fail immediately if key is malformed)
        client = genai.Client(api_key=api_key)
        
        # Make a minimal test request (uses gemini-1.0-pro which is always available)
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents="Give me a random number between 0-9:",)
        
        # If we get any response, the key is valid
        print("👍 API key is valid.",response.text)
        return bool(response.text)
    
    except exceptions.Unauthenticated as e:
        print(f"❌ Invalid API key: {e}")
    except exceptions.PermissionDenied as e:
        print(f"❌ API disabled or project inactive: {e}")
    except exceptions.InvalidArgument as e:
        print(f"❌ Malformed request: {e}")
    except exceptions.ResourceExhausted as e:
        print(f"⚠️ Key valid but quota exceeded: {e}")
        return True  # Key is technically valid
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
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
        print("API key from .env file is not found.")
        print("Exiting the program.")
        print("-------"*10, "\n")
        exit()
        

    '''
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
            
     '''
    

def build_chatBot():
    # Retrieve GOOGLE_API_KEY from system environment variables
    global _GLOBAL_GENAI_CLIENT, _GLOBAL_CHAT
    gemini_api_key = get_API_key()

    # If we've already built a persistent client/chat, return it.
    if _GLOBAL_CHAT is not None:
            return _GLOBAL_CHAT

    # Create a single genai.Client that will live for the process lifetime.
    if _GLOBAL_GENAI_CLIENT is None:
            _GLOBAL_GENAI_CLIENT = genai.Client(api_key=gemini_api_key)

    # Access the system_prompt value
    system_prompt = CONFIG['llm']['settings']['system_prompt']
    model = CONFIG['llm']['model']
    print("Building the chatbot with the model: ", model)
    generate_content_config = types.GenerateContentConfig(
                temperature=0.5,
                response_mime_type="text/plain",
                system_instruction=[
                        types.Part.from_text(text=system_prompt),
                ],
        )

    _GLOBAL_CHAT = _GLOBAL_GENAI_CLIENT.chats.create(model=model,
                                                         config=generate_content_config,)

    return _GLOBAL_CHAT

def generate_LLM_answer(prompt, context, chat):
    try:
        response = chat.send_message( prompt + context)
        return response.text
    except RuntimeError as e:
        # Workaround for httpx "client has been closed" errors coming from
        # google.genai internals: try to recreate the chat client once and retry.
        msg = str(e)
        if 'client has been closed' in msg:
            print("Warning: HTTP client was closed. Recreating chat client and retrying once...")
            try:
                new_chat = build_chatBot()
                response = new_chat.send_message( prompt + context)
                return response.text
            except Exception as e2:
                print("Retry after recreating client failed:", e2)
                raise
        # If it's a different runtime error, re-raise
        raise

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
