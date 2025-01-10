#pip install -U rag-kmk
#pip install -U streamlit
#streamlit run run_interface.py
# Ensure that you have a directory ./files with some documents in it.

from rag_kmk.knowledge_base import build_knowledge_base  
from rag_kmk.vector_db import summarize_collection 
from rag_kmk.chat_flow import RAG_LLM, generateAnswer
import streamlit as st
import os

# Define a unique key for the text_input element
FILES_LOCATION_KEY = "files_location"

def main_interface():
    st.title("🦜 RAG KMK")
    st.sidebar.title("CONFIG") # Add sidebar title
    
    # Load knowledge base - moved outside the main loop
    if "knowledge_base" not in st.session_state :
        with st.status("Wait: Loading knowledge base...") as status:
            files_location = None
            max_attempts = 3 # Maximum number of attempts to get a valid path
            attempts = 0
            while files_location is None and attempts < max_attempts: #Loop until a valid path is provided or max attempts reached
                files_location = st.sidebar.text_input("Files Location:", key=FILES_LOCATION_KEY, help="Enter the path to your files directory.") 
                if files_location: # Check if a path has been entered
                    try:
                        if not os.path.isdir(files_location):
                            #Improved error message
                            st.sidebar.error(f"Invalid directory path: '{files_location}'. Please enter a valid directory path.  The path must point to a directory containing your files.")
                            status.update(label=f"Error: Invalid directory path.", state="error")
                            attempts += 1 #Increment attempts if path is invalid
                            continue #Skip the rest of the loop if the path is invalid
                        
                        #Check if the directory is empty
                        if not os.listdir(files_location):
                            st.sidebar.error(f"The directory '{files_location}' is empty. Please select a directory containing files.")
                            status.update(label=f"Error: Empty directory.", state="error")
                            attempts += 1 #Increment attempts if directory is empty
                            files_location = None #Reset files_location to continue the loop
                            continue
                        knowledge_base = build_knowledge_base(files_location)
                        if knowledge_base is not None:
                            summary = summarize_collection(knowledge_base)
                            try:
                                filenames = summary.strip().splitlines()
                                formatted_summary = "\n".join([f"- {filename}" for filename in filenames])
                                with st.sidebar.expander("Knowledge Base Summary"):
                                    st.markdown(formatted_summary)
                            except AttributeError as e:
                                st.sidebar.error(f"Error summarizing knowledge base: {e}")
                                with st.sidebar.expander("Knowledge Base Summary"):
                                    st.markdown("Summary not available in the expected format.")
                            st.session_state.knowledge_base = knowledge_base
                            status.update(label="Knowledge Base is ready!", state="complete")
                        else:
                            status.update(label="No documents loaded or an error occurred during loading.", state="error")
                            st.sidebar.error("No documents found in the specified directory or an error occurred during loading.")
                            attempts += 1 #Increment attempts if no documents are loaded
                            files_location = None #Reset files_location to continue the loop
                    except (ValueError, OSError, FileNotFoundError, Exception) as e:
                        st.sidebar.error(f"An error occurred while loading the knowledge base: {e}")
                        status.exception(e) # Show the full traceback for debugging
                        status.update(label=f"Error loading knowledge base: {e}", state="error")
                        attempts += 1 #Increment attempts if an error occurs
                        files_location = None #Reset files_location to continue the loop
                    except Exception as e:
                        st.sidebar.error(f"An unexpected error occurred: {e}")
                        status.exception(e) # Show the full traceback for debugging
                        status.update(label=f"An unexpected error occurred: {e}", state="error")
                        attempts += 1 #Increment attempts if an unexpected error occurs
                        files_location = None #Reset files_location to continue the loop
            if attempts >= max_attempts:
                st.error(f"Maximum number of attempts ({max_attempts}) reached. Please check your input and try again.")

    else:
        try:
            summary = summarize_collection(st.session_state.knowledge_base)
            try:
                filenames = summary.strip().splitlines()
                formatted_summary = "\n".join([f"- {filename}" for filename in filenames])
                with st.sidebar.expander("Knowledge Base Summary"):
                    st.markdown(formatted_summary)
            except AttributeError as e:
                st.sidebar.error(f"Error summarizing knowledge base: {e}")
                with st.sidebar.expander("Knowledge Base Summary"):
                    st.markdown("Summary not available in the expected format.")
        except Exception as e:
            st.error(f"An error occurred while processing the knowledge base: {e}")
    # ... rest of the code ...

