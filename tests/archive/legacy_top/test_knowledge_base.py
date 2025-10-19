'''
import unittest
import os
from unittest.mock import patch, Mock
from rag_kmk import initialize_rag, build_knowledge_base
from tests import TEST_CONFIG

class TestKnowledgeBase(unittest.TestCase):
    pass



    @classmethod
    def setUpClass(cls):
        # Initialize the RAG system with the test configuration
        cls.config = TEST_CONFIG

    def setUp(self):
        # Create a list of sample documents for each test
        self.sample_docs = [
            "This is a sample document for testing.",
            "Another sample document with different content.",
            "A third document to ensure we can handle multiple inputs."
        ]

    @patch('rag_kmk.knowledge_base.document_loader.load_documents')
    @patch('rag_kmk.knowledge_base.text_splitter.split_text')
    @patch('rag_kmk.knowledge_base.vectorizer.vectorize_chunks')
    def test_build_knowledge_base(self, mock_vectorize, mock_split, mock_load):
        # Set up mock returns
        mock_load.return_value = self.sample_docs
        mock_split.return_value = [doc.split() for doc in self.sample_docs]
        mock_vectorize.return_value = [Mock() for _ in self.sample_docs]

        # Call the function we're testing
        result = build_knowledge_base(["file1.txt", "file2.txt"], self.config)

        # Assert that the mocked functions were called with the correct arguments
        mock_load.assert_called_once_with(["file1.txt", "file2.txt"])
        mock_split.assert_called_once()
        mock_vectorize.assert_called_once()

        # Assert that the result is as expected
        self.assertEqual(len(result), len(self.sample_docs))
        self.assertTrue(all(isinstance(vec, Mock) for vec in result))

    def test_build_knowledge_base_with_empty_input(self):
        with self.assertRaises(ValueError):
            build_knowledge_base([], self.config)

    @patch('rag_kmk.knowledge_base.document_loader.load_documents')
    def test_build_knowledge_base_with_unsupported_file_type(self, mock_load):
        mock_load.side_effect = ValueError("Unsupported file type")

        with self.assertRaises(ValueError):
            build_knowledge_base(["unsupported.xyz"], self.config)

    # Add more tests as needed for edge cases and specific functionalities


if __name__ == '__main__':
    unittest.main()

    '''