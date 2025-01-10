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
                # the summary should be displayed in the left bar as a collapsable section AI!
                summary = summarize_collection(knowledge_base)
                st.write(f"Knowledge base summary:\n{summary}")
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
