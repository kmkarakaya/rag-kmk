#pip install rag-kmk
#pip install streamlit
# To run: streamlit run run_interface.py
# Ensure that you have a directory with some documents in it.

from rag_kmk.knowledge_base import build_knowledge_base  
from rag_kmk.vector_db import summarize_collection 
from rag_kmk.chat_flow import RAG_LLM, generateAnswer
import streamlit as st
import os
import json

def main_interface():
    st.title("🦜 RAG KMK")
    st.sidebar.title("CONFIG") # Add sidebar title

    # Load knowledge base - moved outside the main loop to avoid rebuilding on every interaction
    if "knowledge_base" not in st.session_state :
        knowledge_base = None # Initialize knowledge_base
        with st.status("Wait: Loading knowledge base...") as status:
            files_location = st.sidebar.text_input("Files Location:") 
            
            if files_location:
                
                if not os.path.isdir(files_location):
                    st.sidebar.error("Invalid directory path. Please enter a valid directory.")
                else:
                    knowledge_base = build_knowledge_base(files_location)
            if knowledge_base: 
                summary = summarize_collection(knowledge_base)
                try:
                    summary_data = json.loads(summary)
                    with st.sidebar.expander("Knowledge Base Summary"):
                        st.markdown(f"**Collection Name:** {summary_data['collection_name']}")
                        st.markdown(f"**Document Count:** {summary_data['document_count']}")
                        st.markdown("**Documents:**")
                        for document in summary_data['documents']:
                            st.markdown(f"- {document}")
                except json.JSONDecodeError:
                    with st.sidebar.expander("Knowledge Base Summary"):
                        st.markdown("Error decoding summary JSON.")
                except KeyError as e:
                    with st.sidebar.expander("Knowledge Base Summary"):
                        st.markdown(f"Error: Missing key in summary JSON: {e}")
                st.session_state.knowledge_base = knowledge_base
                status.update(label="Knowledge Base is ready!", state="complete")
            else:
                status.update(label="No documents loaded.", state="error")
    else:
        knowledge_base = st.session_state.knowledge_base
        #If knowledge base already exists, display the summary again.
        summary = summarize_collection(knowledge_base)
        try:
            summary_data = json.loads(summary)
            with st.sidebar.expander("Knowledge Base Summary"):
                st.markdown(f"**Collection Name:** {summary_data['collection_name']}")
                st.markdown(f"**Document Count:** {summary_data['document_count']}")
                st.markdown("**Documents:**")
                for document in summary_data['documents']:
                    st.markdown(f"- {document}")
        except json.JSONDecodeError:
            with st.sidebar.expander("Knowledge Base Summary"):
                st.markdown("Error decoding summary JSON.")
        except KeyError as e:
            with st.sidebar.expander("Knowledge Base Summary"):
                st.markdown(f"Error: Missing key in summary JSON: {e}")


    # Initialize chat history and display chat interface ONLY if knowledge_base exists
    if knowledge_base:
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

            response = generateAnswer(RAG_LLM, knowledge_base, prompt)

            # Display assistant response in chat message container
            with st.chat_message("assistant"):
                st.markdown(response)
            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": response})



if __name__ == "__main__":
    main_interface()
