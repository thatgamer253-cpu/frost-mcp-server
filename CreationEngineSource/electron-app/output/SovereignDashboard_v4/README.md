# Sovereign System Dashboard README

## Overview

The Sovereign System Dashboard is a comprehensive monitoring and management tool designed to provide real-time insights into system health, performance metrics, and alert notifications. It includes features such as:

- Real-time data visualization through an intuitive GUI.
- Automated data persistence for historical analysis.
- Robust system monitoring with customizable thresholds.
- An alerting mechanism that sends timely notifications via email.

## Setup Instructions

### Prerequisites
Ensure you have the following installed on your machine:
- Python 3.8 or higher
- pip (Python package installer)
- SQLite (for database operations)

### Installation Steps

1. Clone this repository to your local machine.
2. Create a virtual environment and activate it.
   ```bash
   python -m venv env
   source env/bin/activate
   ```
3. Install the required dependencies listed in `requirements.txt`.
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and fill in your API keys, SMTP server details, and other configurations.
5. Run the installation script to set up necessary files and directories.
   ```bash
   ./install.sh
   ```

### Running the Application

Start the Flask development server:
```bash
python main.py
```
Access the dashboard via `http://localhost:5000`.

## API References

The Sovereign System Dashboard exposes several APIs for data retrieval, monitoring, and alerting. Refer to the documentation within each module (`dashboard_gui.py`, `data_persistence.py`, etc.) for detailed usage instructions.

### Example Usage
```python
from dashboard_gui import get_dashboard_data

# Fetch real-time system metrics
metrics = get_dashboard_data()
print(metrics)
```

## Contribution Guidelines

1. Fork this repository and clone it to your local machine.
2. Create a new branch for your feature or bug fix.
3. Write tests for any new functionality you add.
4. Ensure all existing tests pass before submitting a pull request.

### Code of Conduct
Please adhere to the [Contributor Covenant](https://www.contributor-covenant.org/) when participating in this project.

## License

This project is licensed under the MIT License - see the LICENSE file for details.