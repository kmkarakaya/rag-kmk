# rag-kmk


[![image](https://img.shields.io/pypi/v/rag-kmk.svg)](https://pypi.python.org/pypi/rag-kmk)
[![image](https://img.shields.io/conda/vn/conda-forge/rag-kmk.svg)](https://anaconda.org/conda-forge/rag-kmk)


**A simple RAG implementation for educational purposes implemented by Murat Karakaya Akademi**


-   Free software: MIT License
-   Documentation: https://kmkarakaya.github.io/rag-kmk
-   Tutorial: https://www.youtube.com/@MuratKarakayaAkademi
    

## Features

- TODO: 
- add other file types

## Local development notes

- The project stores a local persistent ChromaDB under `./chromaDB` by default.
- To avoid checking runtime DB files into source control, add `chromaDB/` to your `.gitignore`.

If you need to switch to an in-memory collection for quick tests, set `vector_db.chromaDB_path` to `null` in `rag_kmk/config/config.yaml`.
