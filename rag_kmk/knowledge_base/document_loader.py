import os
import fitz  # PyMuPDF
from rag_kmk import CONFIG


def load_documents(document_directory_path):
    """
    Loads documents from a specified directory. Supported file types are defined in CONFIG['supported_file_types'].
    Currently supports .txt, .pdf, and .docx files.

    Parameters:
    - directory_path (str): The path to the directory containing the documents to be loaded.

    Returns:
    - list: A list of document contents as strings.
    """


    documents = []

    if not os.path.isdir(document_directory_path):
        print(f'{document_directory_path} is not a directory.')
        return documents

    for filename in os.listdir(document_directory_path):
        file_path = os.path.join(document_directory_path, filename)
        file_extension = os.path.splitext(filename)[1]

        if file_extension in CONFIG['supported_file_types']:
            try:
                if file_extension == '.txt':
                    with open(file_path, 'r') as file:
                        document = file.read()
                    documents.append(document)
                    print(f'Text document loaded successfully from {file_path}')
                elif file_extension == '.pdf':
                    with fitz.open(file_path) as doc:
                        text = ''
                        for page in doc:
                            text += page.get_text()
                    documents.append(text)
                    print(f'PDF document loaded successfully from {file_path}')
                elif file_extension == '.docx':
                    doc = Document(file_path)
                    text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
                    documents.append(text)
                    print(f'DOCX document loaded successfully from {file_path}')
            except Exception as e:
                print(f'Failed to load document from {file_path}: {e}')
        else:
            print(f'Skipping unsupported file type: {file_path}')

    return documents
