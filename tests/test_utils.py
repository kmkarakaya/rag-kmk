#$env:PYTHONPATH = "C:\Codes\AI_MODULES\rag-kmk;" + $env:PYTHONPATH

import unittest
from unittest.mock import patch, mock_open
from rag_kmk.utils.config import load_config


class ConfigTestCase(unittest.TestCase):
    def test_load_config(self):
        # Test case 1: Check if the function returns a dictionary
        config = load_config()
        self.assertIsInstance(config, dict)
        

    def test_load_invalid_config(self):
        # Test case 3: Check if the function handles missing config file gracefully
        # In this case, the function should return an empty dictionary
        config = load_config('nonexistent_config_file.yaml')
        self.assertEqual(config, {})

    
if __name__ == '__main__':
    unittest.main()