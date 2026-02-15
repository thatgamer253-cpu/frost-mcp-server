import logging
import yaml

def initialize_logging():
    logging_config = {
        'level': logging.INFO,
        'format': '%(asctime)s - %(levelname)s - %(message)s',
    }
    logging.basicConfig(**logging_config)
    logging.info("Logging initialized.")

def main():
    initialize_logging()
    
    try:
        logging.info("Starting system initialization.")
        
        # Initialize core components
        with open('config.yaml', 'r') as config_file:
            config = yaml.safe_load(config_file)
        db_path = config.get('database', {})
        # Continue with the rest of the logic
    except Exception as e:
        logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()