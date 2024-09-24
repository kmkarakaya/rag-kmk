from  rag_kmk import CONFIG
from rag_kmk.knowledge_base import build_knowledge_base   
from rag_kmk.vector_db import summarize_collection, retrieve_chunks, show_results
from rag_kmk.chat_flow import generateAnswer, generate_LLM_answer, RAG_LLM, run_rag_pipeline  

def main():
       
    '''
    Load the documents from the sample_documents folder and print the first 200 characters of each document.        

    '''

    

    # Load the documents
    knowledge_base= build_knowledge_base(r'.\tests\sample_documents')     

    print("-----------------"*4)  
    # Summarize the collection
    summarize_collection(knowledge_base)

    '''
    print("-----------------"*4)
    query = "What are the main causes of student success considering attandnce and study habits?"
    retrieved_chunks=retrieve_chunks(chroma_collection, query, 3)
    show_results(retrieved_chunks)
    '''
    
    
    '''
    print("-----------------"*4)
    prompt="What is FC?"
    context= """FC lets developers create a description
    of a F in their code, then pass that description to a language
    model in a request.
    The response from the model includes the name of
    a F that matches the description and the arguments to call it with.
    FC lets you use F as tools in generative AI applications,
    and you can define more than one F within a single request."""
    
    response=generate_LLM_answer(prompt, context,RAG_LLM)
    print(response)
    '''

    '''
    query = "What are the main causes of student success considering attandnce and study habits?"
    reply=generateAnswer(RAG_LLM, chroma_collection, query,3, only_response=False)
    print(reply)
    '''

    run_rag_pipeline(RAG_LLM,knowledge_base)





    
    '''
    Leadership and Project Management: Dr. KARAKAYA has overseen eight research projects supported by Atılım University and participated as a researcher in two projects funded by TUBITAK (Scientific and Technical Research Council of Turkey). He has established two research groups, the Natural Computing Interest Group and the Salda Deep Learning Research Group and has collaborated with group members on publishing over 20 papers in the areas of Machine Learning, Deep Learning, and Natural Computing.
    Recognition and Awards: His contributions have not gone unnoticed, 

    from chromadb.utils import embedding_functions
    default_ef = embedding_functions.DefaultEmbeddingFunction()
    val = default_ef([text])
    print(f"val={val}")

    sentence_transformer_model=CONFIG["vector_db"]["embedding_model_multilingual"]
    chunk_overlap=CONFIG["knowledge_base"]["chunk_overlap"]
    tokens_per_chunk=CONFIG["vector_db"]["tokens_per_chunk"]

    print(f"Using SentenceTransformer model: {sentence_transformer_model}" )
    print(f"Chunk overlap: {chunk_overlap}" )
    print(f"Tokens per chunk: {tokens_per_chunk}" )
    token_splitter = SentenceTransformersTokenTextSplitter(
        chunk_overlap=20,
        model_name=sentence_transformer_model,
        tokens_per_chunk=50)
    print(token_splitter.split_text(text) )
    

    '''
if __name__ == "__main__":
    main()