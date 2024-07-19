import rag_kmk
from  rag_kmk import CONFIG
from rag_kmk.knowledge_base.document_loader import load_documents   

def main():
       
    '''
    Load the documents from the sample_documents folder and print the first 200 characters of each document.        

    '''
    # Load the documents
    documents=load_documents(r'rag-kmk\tests\sample_documents')     
    print(f"Loaded {len(documents)} documents")
    for i, doc in enumerate(documents):
        print(f"Document {i+1}:\n{doc[:200]}")


if __name__ == "__main__":
    main()