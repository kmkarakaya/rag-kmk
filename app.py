import streamlit as st
import os

def build_knowledge_base(path):
    try:
        # Your existing code to build the knowledge base.  Example:
        # with open(os.path.join(path, "my_file.txt"), "r") as f:
        #     data = f.read()
        # return data # Replace with your actual knowledge base building logic
        st.write(f"Building knowledge base from: {path}") #Example output
        return {"path":path} #Example return value
    except FileNotFoundError:
        st.error(f"Error: Directory '{path}' not found.")
        return None
    except PermissionError:
        st.error(f"Error: Permission denied accessing '{path}'.")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return None

with st.sidebar:
    st.title("File Location")
    files_location = st.text_input("Enter the file location:", value=r".\files")
    if not os.path.exists(files_location):
        st.error("Invalid directory. Please select a valid directory.")
    else:
        files_location = os.path.abspath(files_location)

if files_location:
    knowledge_base = build_knowledge_base(files_location)
    if knowledge_base:
        st.write("Knowledge base built successfully!")
        #Further processing of knowledge_base
        st.write(knowledge_base)
