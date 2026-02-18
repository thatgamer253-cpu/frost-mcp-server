# llm_service.py

import json

class LLMService:
    def __init__(self, config_path='llm_config.json', model_mapping_path='model_mapping.json'):
        self.config = self._load_config(config_path)
        self.model_mapping = self._load_model_mapping(model_mapping_path)
        self.model_name = self.config.get('model_name')
        self.provider, self.model_type = self._get_model_details(self.model_name)

    def _load_config(self, config_path):
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: Config file not found at {config_path}")
            return {}
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in config file at {config_path}")
            return {}

    def _load_model_mapping(self, model_mapping_path):
        try:
            with open(model_mapping_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: Model mapping file not found at {model_mapping_path}")
            return {}
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in model mapping file at {model_mapping_path}")
            return {}

    def _get_model_details(self, model_name):
        model_info = self.model_mapping.get(model_name)
        if model_info:
            return model_info['provider'], model_info['model_type']
        else:
            print(f"Error: Model {model_name} not found in model mapping.")
            return None, None

    def get_llm_details(self):
        return self.provider, self.model_type, self.model_name

# Example usage:
if __name__ == '__main__':
    llm_service = LLMService()
    provider, model_type, model_name = llm_service.get_llm_details()
    print(f"Provider: {provider}, Model Type: {model_type}, Model Name: {model_name}")