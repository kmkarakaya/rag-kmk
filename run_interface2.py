# streamlit run .\run_interface2.py
from rag_kmk.knowledge_base import build_knowledge_base
from rag_kmk.vector_db import summarize_collection
from rag_kmk.chat_flow import RAG_LLM, generateAnswer
from rag_kmk.vector_db.database import ChromaDBStatus
import streamlit as st
import os
import json

def add_custom_css():
    st.markdown("""
        <style>
        /* Force streamlit elements to respect our layout */
        [data-testid="stVerticalBlock"] {
            gap: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        /* Title styling */
        h1 {
            margin-bottom: 1rem !important;
        }

        /* Chat input container - force to top */
        .stChatInputContainer {
            position: static !important;
            order: -1 !important;
            margin: 0 0 1rem 0 !important;
            padding: 0.5rem !important;
            background: white !important;
            border-bottom: 1px solid #dee2e6 !important;
            z-index: 100 !important;
        }

        /* Chat messages area */
        .stChatMessageContent, .stMarkdown {
            margin: 0 !important;
        }

        .chat-message {
            padding: 0.75rem;
            border-radius: 0.5rem;
            margin-bottom: 0.75rem;
            max-width: 90%;
        }
        
        .chat-message.user {
            background-color: #f7f7f8;
            margin-left: auto;
        }
        
        .chat-message.assistant {
            background-color: white;
            border: 1px solid #dee2e6;
            margin-right: auto;
        }

        /* Column layout adjustments */
        [data-testid="column"] {
            padding: 0.5rem !important;
        }
        </style>
    """, unsafe_allow_html=True)

def initialize_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "knowledge_base" not in st.session_state:
        st.session_state.knowledge_base = None
    if "collection_status" not in st.session_state:
        st.session_state.collection_status = None

def display_knowledge_base_summary():
    if st.session_state.knowledge_base:
        summary = summarize_collection(st.session_state.knowledge_base)
        try:
            summary_data = json.loads(summary)
            with st.expander("Knowledge Base Summary"):
                st.markdown(f"**Collection Name:** {summary_data['collection_name']}")
                st.markdown(f"**Document Count:** {summary_data['document_count']}")
                st.markdown("**Documents:**")
                for document in summary_data['documents']:
                    st.markdown(f"- {document}")
        except (json.JSONDecodeError, KeyError) as e:
            st.error(f"Error displaying summary: {str(e)}")

def left_panel():
    st.title("Configuration")
    
    # Collection type selection
    collection_type = st.selectbox(
        "Choose Collection Type",
        [
            "Select an option",
            "Create a new in memory collection",
            "Load an existing collection",
            "Load an existing collection & add new doc.s"
        ],
        index=0
    )
    
    if collection_type != "Select an option":
        if collection_type == "Create a new in memory collection":
            docs_path = st.text_input("Enter documents directory path:")
            if docs_path and st.button("Create Collection"):
                with st.spinner("Creating in-memory collection..."):
                    knowledge_base, status = build_knowledge_base(
                        document_directory_path=docs_path,
                        chromaDB_path=None
                    )
                    if status == ChromaDBStatus.NEW_MEMORY:
                        st.session_state.knowledge_base = knowledge_base
                        st.session_state.collection_status = status
                        st.success("In-memory collection created successfully!")
                    else:
                        st.error("Failed to create in-memory collection")
                        
        elif collection_type == "Load an existing collection":
            chroma_path = st.text_input("Enter ChromaDB path:")
            if chroma_path and st.button("Load Collection"):
                with st.spinner("Loading existing collection..."):
                    knowledge_base, status = build_knowledge_base(
                        chromaDB_path=chroma_path
                    )
                    if status == ChromaDBStatus.EXISTING_PERMANENT:
                        st.session_state.knowledge_base = knowledge_base
                        st.session_state.collection_status = status
                        st.success("Collection loaded successfully!")
                    else:
                        st.error("Failed to load collection")
                        
        else:  # Load and add new documents
            chroma_path = st.text_input("Enter ChromaDB path:")
            docs_path = st.text_input("Enter new documents directory path:")
            if chroma_path and docs_path and st.button("Load and Update Collection"):
                with st.spinner("Loading and updating collection..."):
                    knowledge_base, status = build_knowledge_base(
                        document_directory_path=docs_path,
                        chromaDB_path=chroma_path
                    )
                    if status in [ChromaDBStatus.EXISTING_PERMANENT, ChromaDBStatus.NEW_PERMANENT]:
                        st.session_state.knowledge_base = knowledge_base
                        st.session_state.collection_status = status
                        st.success("Collection updated successfully!")
                    else:
                        st.error("Failed to update collection")
    
    display_knowledge_base_summary()

def right_panel():
    st.title("Chat Interface")
    
    if st.session_state.knowledge_base is None:
        st.warning("Please configure and load a knowledge base first")
        return

    # First create and render the input box at the top
    prompt = st.chat_input("Ask a question about your documents...", key="chat_input")
    
    # Then create the messages container
    messages_container = st.container()
    
    # Handle new input
    if prompt:
        # Show the user's question immediately at the top
        with messages_container:
            with st.chat_message("user", avatar="🧑‍💻"):
                st.markdown(f'<div class="chat-message user">{prompt}</div>', unsafe_allow_html=True)
        
        # Generate the response
        with st.spinner("Thinking..."):
            response = generateAnswer(RAG_LLM, st.session_state.knowledge_base, prompt)
        
        # Show the response below the question
        with messages_container:
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(f'<div class="chat-message assistant">{response}</div>', unsafe_allow_html=True)
        
        # Add both messages to the session state at the beginning
        st.session_state.messages.insert(0, {"role": "assistant", "content": response})
        st.session_state.messages.insert(0, {"role": "user", "content": prompt})
    
    # Display existing chat history below
    with messages_container:
        # Skip the first two messages if they were just added (to avoid duplication)
        start_idx = 2 if prompt else 0
        for message in st.session_state.messages[start_idx:]:
            with st.chat_message(message["role"], avatar="🧑‍💻" if message["role"] == "user" else "🤖"):
                st.markdown(f'<div class="chat-message {message["role"]}">{message["content"]}</div>', 
                          unsafe_allow_html=True)

def main():
    add_custom_css()
    initialize_session_state()
    
    # Create two columns for the layout with adjusted ratios
    left_col, right_col = st.columns([1, 3])
    
    with left_col:
        left_panel()
    
    with right_col:
        right_panel()

if __name__ == "__main__":
    main()