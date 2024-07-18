from .database import VectorDatabase

def build_vector_db(vectors, config):
    db_config = config['vector_db']
    db = VectorDatabase(db_config)
    db.add_vectors(vectors)
    return db

__all__ = ['build_vector_db']