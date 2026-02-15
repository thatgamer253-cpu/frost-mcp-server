import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from guardian import guardian

load_dotenv()

class NotificationManager:
    """
    Alerts the user when 'Action Required' or 'Money Received'.
    Supports SMTP (Email) and can be extended for Discord/Telegram.
    """
    def __init__(self):
        self.email = os.getenv("SMTP_USER")
        self.password = os.getenv("SMTP_PASSWORD")
        self.target = os.getenv("NOTIFY_EMAIL", self.email)
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))

    def send_alert(self, subject, message):
        """Sends a high-priority notification."""
        guardian.log_activity(f"NOTIFIER: Sending alert - {subject}")
        
        if not self.email or not self.password:
            guardian.log_activity("NOTIFIER Error: SMTP credentials not configured.")
            return False

        try:
            msg = EmailMessage()
            msg.set_content(message)
            msg['Subject'] = f"❄️ FROST ALERT: {subject}"
            msg['From'] = self.email
            msg['To'] = self.target

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email, self.password)
                server.send_message(msg)
            
            return True
        except Exception as e:
            guardian.log_activity(f"NOTIFIER Error: {str(e)}", "WARNING")
            return False

# Singleton
notifier = NotificationManager()
