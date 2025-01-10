#pip install -U rag-kmk
#pip install -U streamlit
#streamlit run run_interface.py
# Ensure that you have a directory ./files with some documents in it.

from rag_kmk.knowledge_base import build_knowledge_base  
from rag_kmk.vector_db import summarize_collection 
from rag_kmk.chat_flow import RAG_LLM, generateAnswer
import streamlit as st
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define a unique key for the text_input element
FILES_LOCATION_KEY = "files_location"

def main_interface():
    st.title("🦜 RAG KMK")
    st.sidebar.title("CONFIG") # Add sidebar title
    
    files_location = st.sidebar.text_input("Files Location:", key=FILES_LOCATION_KEY, help="Enter the path to your files directory.") 

    if files_location:
        try:
            if not os.path.isdir(files_location):
                raise ValueError(f"Invalid directory path: '{files_location}'. Please enter a valid directory path.")
            
            if not os.listdir(files_location):
                raise ValueError(f"The directory '{files_location}' is empty. Please select a directory containing files.")

            with st.status("Wait: Loading knowledge base...") as status:
                knowledge_base = build_knowledge_base(files_location)
                if knowledge_base is None:
                    raise ValueError("No documents loaded or an error occurred during loading.")

                summary = summarize_collection(knowledge_base)
                st.session_state.knowledge_base = knowledge_base
                st.session_state.knowledge_base_summary = summary #Store summary in session state

                with st.sidebar.expander("Knowledge Base Summary"):
                    st.markdown(summary) #Use the stored summary

                status.update(label="Knowledge Base is ready!", state="complete")

        except (ValueError, OSError, FileNotFoundError, Exception) as e:
            st.error(f"An error occurred: {e}")
            logging.exception(f"An error occurred while loading the knowledge base: {e}") # Log the full traceback
    else:
        st.info("Please specify a files location in the sidebar.")


    # ... rest of the code ...

