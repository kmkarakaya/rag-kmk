import logging
import os

def setup_logger(name, log_filename, level=logging.INFO):
    """
    Sets up a logger with a relative path to the log file.

    Parameters:
    - name (str): The name of the logger.
    - log_filename (str): The relative path to the log file within the library.
    - level (int, optional): The logging level. Defaults to logging.INFO.

    Returns:
    - logging.Logger: The configured logger.
    """

    # Get the absolute path to the log file based on library location
    base_path = os.path.dirname(__file__)  # Get the directory of this file
    log_file_path = os.path.join(base_path, '..', log_filename)  # Join with logs/document_loader.log

    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler = logging.FileHandler(log_file_path)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger
