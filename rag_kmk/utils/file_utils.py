import os


def get_file_extension(filename):
    return os.path.splitext(filename)[1].lower()

def is_supported_file_type(filename, supported_types=None):
    if supported_types is None:
        supported_types = CONFIG['supported_file_types']    
    return get_file_extension(filename) in supported_types