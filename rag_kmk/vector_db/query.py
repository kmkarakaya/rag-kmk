

def retrieve_chunks(chroma_collection, query, n_results=5,
                 return_only_docs=False, filterType=None, filterValue=None):
    
    if filterType is not None and filterValue is not None:
        results = chroma_collection.query(
            query_texts=[query],
            include=["documents", "metadatas", "distances"],
            where={filterType: filterValue},
            n_results=n_results)

    else:
        results = chroma_collection.query(
            query_texts=[query],
            include= [ "documents","metadatas",'distances' ],
            n_results=n_results)

    if return_only_docs:
        return results['documents'][0]
    else:
        return results






def show_results(results, return_only_docs=False):
  
  

  if return_only_docs:
    retrieved_documents = results
    if len(retrieved_documents) == 0:
      print("No results found.")
      return
    for i, doc in enumerate(retrieved_documents):
      print(f"Document {i+1}:")
      print("\tDocument Text: ")
      print(doc)
  else:

      retrieved_documents = results['documents'][0]
      if len(retrieved_documents) == 0:
          print("No results found.")
          return
      retrieved_documents_metadata = results['metadatas'][0]
      retrieved_documents_distances = results['distances'][0]
      print("------- retreived documents -------\n")

      for i, doc in enumerate(retrieved_documents):
          print(f"Document {i+1}:")
          print("\tDocument Text: ")
          print(doc)
          print(f"\tDocument Source: {retrieved_documents_metadata[i]['document']}")
          print(f"\tDocument Source Type: {retrieved_documents_metadata[i]['category']}")
          print(f"\tDocument Distance: {retrieved_documents_distances[i]}")