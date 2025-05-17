import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from notification.logger import _logger
from config.donotshare.donotshare import SENDGRID_API_KEY as sgkey
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email

# using SendGrid's Python Library
# https://github.com/sendgrid/sendgrid-python


# Set up the server
_sender_email = 'akossyrev@gmail.com'  # Your email address
_receiver_email = 'akossyrev@gmail.com'  # Receiver's email address


class EmailNotifier:
    def __init__(self, api_key: str):
        """
        Initialize the email notifier.
        
        Args:
            api_key (str): SendGrid API key
        """
        self.logger = _logger.get_logger(__name__)
        self.api_key = api_key
        
        # Test connection on initialization
        try:
            sg = SendGridAPIClient(api_key)
            self.logger.info("Successfully connected to SendGrid")
        except Exception as e:
            self.logger.error(f"Failed to connect to SendGrid: {e}")
            raise


    def send_email(self, to_addr : str, from_addr : str, subject : str, body : str):
        # Create the email content
        message = Mail(
            from_email=_sender_email,
            to_emails=_receiver_email,
            subject=subject,
            html_content=body)
        try:
            sg = SendGridAPIClient(sgkey)
            response = sg.send(message)
        except Exception as e:
            self.logger.error (e)


    def send_notification_email(self, buy_or_sell : str, symbol : str, price : float, amount : float, body : str = ''):
        subject = f"Trade notification: {buy_or_sell} {symbol} at {price} with {amount}"
        self.send_email(_sender_email, _receiver_email, subject, body=body)
        self.logger.debug (f"Email sent successfully: {subject}")


#######################################
# Quick test. Keep commented out.
#######################################
# Example usage
if __name__ == "__main__":
    # Code that should only run when the script is executed directly
    EmailNotifier.send_email(_sender_email, _receiver_email, "TA test subject", "TA test body")
    _logger.debug ("Email sent successfully!")
