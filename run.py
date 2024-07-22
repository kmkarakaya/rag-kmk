from  rag_kmk import CONFIG
from rag_kmk.knowledge_base import build_knowledge_base   


def main():
       
    '''
    Load the documents from the sample_documents folder and print the first 200 characters of each document.        

    '''

    

    # Load the documents
    build_knowledge_base(r'.\tests\sample_documents')     

    print("Documents loaded successfully.")  

    
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