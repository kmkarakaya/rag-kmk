def split_text(documents, chunk_size, chunk_overlap):
    # Implement your text splitting logic here
    chunks = []
    for doc in documents:
        # This is a simple implementation. You might want to use a more sophisticated method.
        words = doc.split()
        for i in range(0, len(words), chunk_size - chunk_overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            chunks.append(chunk)
    return chunks