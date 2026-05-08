"""
Utility functions for logging and SMTP alerts.
"""

import logging
from logging.handlers import TimedRotatingFileHandler
import smtplib
from email.mime.text import MIMEText
import os
import socket
from config import Config


def setup_logging(config: Config) -> logging.Logger:
    """Setup logging with rotation."""
    logger = logging.getLogger('gpo_generator')
    logger.setLevel(logging.INFO)

    # Create logs directory if it doesn't exist
    os.makedirs(config.log_directory, exist_ok=True)

    # Create rotating file handler
    log_file = os.path.join(config.log_directory, 'gpo_generator.log')
    handler = TimedRotatingFileHandler(
        log_file,
        when='midnight',
        interval=config.log_rotation_days,
        backupCount=5  # Keep 5 backup files
    )

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(handler)

    return logger


def send_smtp_alert(config: Config, subject: str, message: str, logger: logging.Logger):
    """Send SMTP alert email."""
    if not config.smtp_server:
        logger.warning("SMTP not configured, skipping alert")
        return

    try:
        # Get system information
        hostname = socket.gethostname()
        script_path = os.path.abspath(__file__)

        # Prepend system information to message
        enhanced_message = f"""System: {hostname}
Script: {script_path}

{message}"""

        msg = MIMEText(enhanced_message)
        msg['Subject'] = subject
        msg['From'] = config.smtp_from_email
        msg['To'] = config.smtp_to_email

        with smtplib.SMTP(config.smtp_server, config.smtp_port) as server:
            server.sendmail(config.smtp_from_email, config.smtp_to_email, msg.as_string())

        logger.info(f"SMTP alert sent: {subject}")

    except Exception as e:
        logger.error(f"Failed to send SMTP alert: {e}")
        # Don't raise, as this might cause infinite loop if alerting about alert failure