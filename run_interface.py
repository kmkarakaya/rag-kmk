#pip install -U rag-kmk
#pip install -U streamlit
#streamlit run run_interface.py
# Ensure that you have a directory ./files with some documents in it.

from rag_kmk.knowledge_base import build_knowledge_base  
from rag_kmk.vector_db import summarize_collection 
from rag_kmk.chat_flow import RAG_LLM, generateAnswer
import streamlit as st
import os

def main_interface():
    st.title("🦜 RAG KMK")
    st.sidebar.title("CONFIG") # Add sidebar title
    
    # Load knowledge base - moved outside the main loop
    if "knowledge_base" not in st.session_state :
        with st.status("Wait: Loading knowledge base...") as status:
            files_location = None
            while files_location is None: #Loop until a valid path is provided
                files_location = st.sidebar.text_input("Files Location:", help="Enter the path to your files directory.") 
                if files_location: # Check if a path has been entered
                    try:
                        if not os.path.isdir(files_location):
                            #Improved error message
                            st.sidebar.error(f"Invalid directory path: '{files_location}'. Please enter a valid directory path.  The path must point to a directory containing your files.")
                            status.update(label=f"Error: Invalid directory path.", state="error")
                            files_location = None #Reset files_location to continue the loop
                            continue #Skip the rest of the loop if the path is invalid
                        
                        #Check if the directory is empty
                        if not os.listdir(files_location):
                            st.sidebar.error(f"The directory '{files_location}' is empty. Please select a directory containing files.")
                            status.update(label=f"Error: Empty directory.", state="error")
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
                            except AttributeError:
                                with st.sidebar.expander("Knowledge Base Summary"):
                                    st.markdown("Summary not available in the expected format.")
                            st.session_state.knowledge_base = knowledge_base
                            status.update(label="Knowledge Base is ready!", state="complete")
                        else:
                            status.update(label="No documents loaded or an error occurred during loading.", state="error")
                            st.sidebar.error("No documents found in the specified directory or an error occurred during loading.")
                            files_location = None #Reset files_location to continue the loop
                    except (ValueError, OSError, Exception) as e:
                        st.sidebar.error(f"An error occurred while loading the knowledge base: {e}")
                        status.update(label=f"Error loading knowledge base: {e}", state="error")
                        files_location = None #Reset files_location to continue the loop
                    except Exception as e:
                        st.sidebar.error(f"An unexpected error occurred: {e}")
                        status.update(label=f"An unexpected error occurred: {e}", state="error")

    else:
        summary = summarize_collection(st.session_state.knowledge_base)
        try:
            filenames = summary.strip().splitlines()
            formatted_summary = "\n".join([f"- {filename}" for filename in filenames])
            with st.sidebar.expander("Knowledge Base Summary"):
                st.markdown(formatted_summary)
        except AttributeError:
            with st.sidebar.expander("Knowledge Base Summary"):
                st.markdown("Summary not available in the expected format.")


    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # React to user input
    if prompt := st.chat_input("Write your query here..."):
        # Display user message in chat message container
        st.chat_message("user").markdown(prompt)
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        response = generateAnswer(RAG_LLM, st.session_state.knowledge_base, prompt)

        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            st.markdown(response)
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    main_interface()
