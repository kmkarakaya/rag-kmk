import os
from rag_kmk.utils import load_config, setup_logger, is_supported_file_type, clean_text

def load_documents(file_list):
    config = load_config()  # Load the configuration
    logger = setup_logger('document_loader', config['logging']['file'])
    
    supported_file_types = config['supported_file_types']
    max_file_size = config.get('knowledge_base', {}).get('max_file_size', 10 * 1024 * 1024)  # Default 10MB if not specified
    
    documents = []
    for file in file_list:
        if is_supported_file_type(file, supported_file_types):
            try:
                file_size = os.path.getsize(file)
                if file_size > max_file_size:
                    logger.warning(f"File {file} exceeds maximum size limit. Skipping.")
                    continue
                
                # Load the file
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                cleaned_content = clean_text(content)
                documents.append(cleaned_content)
                logger.info(f"Successfully loaded and cleaned: {file}")
            except Exception as e:
                logger.error(f"Error processing file {file}: {str(e)}")
        else:
            logger.warning(f"Unsupported file type: {file}")
    
    if not documents:
        logger.warning("No documents were successfully loaded.")
    
    return documents