from flask import Flask, jsonify
from core.engine import initialize_engine
from core.database import initialize_database
from core.health_monitor import start_health_monitor
from core.logging import setup_logging
from plugins.ui_components import initialize_ui
from plugins.notifications import setup_notifications
from config.settings import Config
from utils.watchdog import start_watchdog

app = Flask(__name__)
app.config.from_object(Config)

# Setup logging
setup_logging()

# Initialize core components
initialize_engine()
initialize_database()

# Start health monitoring
start_health_monitor()

# Initialize UI components
initialize_ui(app)

# Setup notifications
setup_notifications()

# Start watchdog for system monitoring
start_watchdog()

@app.route('/health', methods=['GET'])
def health_check():
    # Example health check response
    return jsonify({
        "status": "healthy",
        "uptime": "24h",
        "version": "1.0.0",
        "checks": {
            "db": "connected",
            "cache": "operational",
            "disk": "sufficient"
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

# Explanation:
# - **Flask Application**: The main entry point is a Flask application that initializes various components and services.
# - **Logging**: Sets up structured logging for the application.
# - **Core Components**: Initializes the engine and database, which are critical for the application's backend operations.
# - **Health Monitoring**: Starts a health monitor to ensure the application is running smoothly.
# - **UI Initialization**: Sets up the UI components using a plugin architecture.
# - **Notifications**: Configures the notification system to alert users of important events.
# - **Watchdog**: Starts a watchdog to monitor system resources and application health.
# - **Health Endpoint**: Provides a `/health` endpoint to check the application's health status.
# - **Run Server**: Configures the Flask app to run on all available IP addresses on port 5000.