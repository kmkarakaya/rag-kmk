#pip install rag-kmk
#pip install streamlit
#streamlit run test.py
from rag_kmk.knowledge_base import build_knowledge_base  
from rag_kmk.vector_db import summarize_collection 
from rag_kmk.chat_flow import RAG_LLM, generateAnswer
import streamlit as st

def main_interface():
    st.title("🦜 RAG KMK")


    # Load knowledge base
    if "knowledge_base" not in st.session_state :
        with st.status("Wait: Loading knowledge base...") as status:
            knowledge_base= build_knowledge_base(r'.\files') 
            if knowledge_base: 
                summarize_collection(knowledge_base) 
                st.session_state.knowledge_base = knowledge_base
                status.update(label="Knowledge Base is ready!", state="complete")
            else:
                status.update(label="No documents loaded.", state="error")
    

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