import yaml
import os
# Correct the path to navigate up one directory from the script's location
config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.yaml')
config_path = os.path.normpath(config_path)  # Normalize the path to resolve '..'


def load_config(custom_config_path=None):
    """
    Initialize the RAG system with either the default or a custom config.
    If the specified config file does not exist, return an empty config.
    """
    try:
        if custom_config_path:
            with open(custom_config_path, 'r') as config_file:
                CONFIG = yaml.safe_load(config_file)
                return CONFIG or {}
        else:
            with open(config_path, 'r') as config_file:
                CONFIG = yaml.safe_load(config_file)
                return CONFIG or {}
    except FileNotFoundError:
        return {}


def mask_config(config: dict, keys: tuple = ('api_key', 'api_key_env_var')) -> dict:
    """Return a shallow copy of config with sensitive keys masked.

    This is a helper for logging or printing configs without leaking secrets.
    """
    import copy
    c = copy.deepcopy(config or {})
    def mask_obj(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if any(s in k.lower() for s in keys):
                    obj[k] = '****'
                else:
                    mask_obj(v)

    mask_obj(c)
    return c