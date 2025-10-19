def retrieve_chunks(chroma_collection, query, n_results=5,
                    return_only_docs=False, filterType=None, filterValue=None):
    """
    Run a similarity query against a Chroma collection and return raw results.

    Assumes the chroma_collection exposes a `query` method that accepts:
      - query_texts: list[str]
      - include: list[str]
      - where: dict (optional)
      - n_results: int

    The returned structure is expected to contain keys:
      - 'documents': [[...]]
      - 'metadatas': [[...]]
      - 'distances': [[...]]
    """
    if filterType is not None and filterValue is not None:
        results = chroma_collection.query(
            query_texts=[query],
            include=["documents", "metadatas", "distances"],
            where={filterType: filterValue},
            n_results=n_results,
        )
    else:
        results = chroma_collection.query(
            query_texts=[query],
            include=["documents", "metadatas", "distances"],
            n_results=n_results,
        )

    if return_only_docs:
        docs = results.get("documents", [[]])[0]
        if len(docs) == 0:
            # print("No results found.")
            return []

        # Suppress verbose printing of document contents; callers can use
        # the returned list for inspection or logging as needed.
        # for i, doc in enumerate(docs):
        #     print(f"Document {i+1}:")
        #     print("\tDocument Text: ")
        #     print(doc)
        #     try:
        #         src = results["metadatas"][0][i].get("document")
        #     except Exception:
        #         src = None
        #     print(f"\tDocument Source: {src}")
        #     try:
        #         dist = results["distances"][0][i]
        #     except Exception:
        #         dist = None
        #     print(f"\tDocument Distance: {dist}")

        return docs

    return results


def show_results(results, return_only_docs=False):
    """
    Pretty-print results returned by `retrieve_chunks` or similar.
    - If return_only_docs is True, `results` is a list of document strings.
    - Otherwise `results` is a dict with keys 'documents', 'metadatas', 'distances'.
    """
    if return_only_docs:
        retrieved_documents = results
        if not retrieved_documents:
            # print("No results found.")
            return
        # Suppress verbose printing of retrieved documents.
        # for i, doc in enumerate(retrieved_documents):
        #     print(f"Document {i+1}:")
        #     print("\tDocument Text: ")
        #     print(doc)
        return

    retrieved_documents = results.get("documents", [[]])[0]
    if len(retrieved_documents) == 0:
        print("No results found.")
        return

    retrieved_documents_metadata = results.get("metadatas", [[]])[0]
    retrieved_documents_distances = results.get("distances", [[]])[0]
    # Suppress verbose printing of retrieved documents; callers can inspect
    # and log details as needed.
    # print("------- retrieved documents -------\n")
    # for i, doc in enumerate(retrieved_documents):
    #     print(f"Document {i+1}:")
    #     print("\tDocument Text: ")
    #     print(doc)
    #     try:
    #         src = retrieved_documents_metadata[i].get("document")
    #     except Exception:
    #         src = None
    #     try:
    #         cat = retrieved_documents_metadata[i].get("category")
    #     except Exception:
    #         cat = None
    #     try:
    #         dist = retrieved_documents_distances[i]
    #     except Exception:
    #         dist = None
    #     print(f"\tDocument Source: {src}")
    #     print(f"\tDocument Source Type: {cat}")
    #     print(f"\tDocument Distance: {dist}")