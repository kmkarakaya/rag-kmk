import streamlit as st
import logging
import os
from rag_kmk.knowledge_base import build_knowledge_base
from rag_kmk.vector_db import summarize_collection

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    st.title("Simplified RAG KMK")
    with st.sidebar:
        st.header("Configure")
        files_location = st.text_input("Files Location:", help="Enter the path to your files directory.")

    if files_location:
        try:
            # Convert user input to absolute path
            abs_path = os.path.abspath(files_location)
            with st.spinner("Loading knowledge base from"+abs_path):
                knowledge_base = build_knowledge_base(abs_path)
                if knowledge_base is None:
                    raise ValueError("Failed to build knowledge base from"+ abs_path)
                summary = summarize_collection(knowledge_base)
                with st.sidebar.expander("Knowledge Base Summary"):
                    st.write(f"Knowledge base summary:\n{summary}")
                st.success("Knowledge base built successfully!") #added welcome message
                st.write("Welcome! Ask your questions.") #added welcome message

        except FileNotFoundError:
            st.error(f"An error occurred: Directory not found: {files_location}")
            logging.exception(f"A critical error occurred: Directory not found: {files_location}")
        except Exception as e:
            st.error(f"An error occurred: {e}")
            logging.exception(f"A critical error occurred: {e}")
    else:
        st.info("Please specify a files location.")

if __name__ == "__main__":
    main()
