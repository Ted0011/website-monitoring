#!/usr/bin/env python3
import os
import time
import sqlite3
import json
import requests
import logging
import hashlib
from datetime import datetime
import pytz
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/data/monitor.log"),
        logging.StreamHandler()
    ]
)

# Configuration from docker-compose.yml file
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')
#### UN-COMMENT IF SECOND_ANY_WEBHOOK_URL IS REQUIRED
#SECOND_ANY_WEBHOOK_URL = os.environ.get('SECOND_ANY_WEBHOOK_URL')
DB_PATH = "/data/websites.db"
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# List of websites to monitor
WEBSITES = [
    "https://dashboard.paaspay.io",
    "https://api.paaspay.io/swagger/index.html",
    "https://aususerapi.isendremit.com/swagger/index.html",
    "https://ausremitadminapi.isendremit.com/swagger/index.html",
    "https://sgpremitadminapi.isendremit.com/swagger/index.html",
    "https://sgpuserapi.isendremit.com/swagger/index.html",
    "https://usaremitadminapi.isendremit.com/swagger/index.html",
    "https://usauserapi.isendremit.com/swagger/index.html",
    "https://sendingmiddleware.isendremit.com/swagger/index.html"
]

# Default user credentials
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin_password"

def hash_password(password):
    """Hash the password using SHA-256 (you can use bcrypt for more security)"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def init_database():
    """Initialize the SQLite database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create websites table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS websites (
        url TEXT PRIMARY KEY,
        status TEXT,
        last_status_code INTEGER,
        last_checked TIMESTAMP,
        failure_count INTEGER DEFAULT 0
    )
    ''')

    # Create users table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password_hash TEXT
    )
    ''')

    # Insert default user if it doesn't exist
    cursor.execute("SELECT * FROM users WHERE username = ?", (DEFAULT_USERNAME,))
    result = cursor.fetchone()
    if not result:
        hashed_password = hash_password(DEFAULT_PASSWORD)
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (DEFAULT_USERNAME, hashed_password)
        )
        logging.info(f"Default user {DEFAULT_USERNAME} created.")
    
    # Insert websites if they don't exist
    for website in WEBSITES:
        cursor.execute(
            "INSERT OR IGNORE INTO websites (url, status, failure_count, last_checked) VALUES (?, ?, ?, ?)",
            (website, "healthy", 0, datetime.now(pytz.timezone('Asia/Kathmandu')).isoformat())
        )
    
    conn.commit()
    conn.close()
    logging.info("Database initialized")

def send_slack_notification(message):
    """Send a notification to Slack"""
    if not SLACK_WEBHOOK_URL:
        logging.warning("Slack webhook URL not set, skipping notification")
        return
    
    try:
        response = requests.post(
            SLACK_WEBHOOK_URL,
            json={"text": message}
        )
        if response.status_code != 200:
            logging.error(f"Failed to send Slack notification: {response.text}")
    except Exception as e:
        logging.error(f"Error sending Slack notification: {str(e)}")
        
##UN-COMMENT IF REQUIRED
'''def second_any_webhook_message_posting_notification(message):
    """ SEND SECOND NOTIFICATION TO ANY CHANNEL"""
    if not SECOND_ANY_WEBHOOK_URL:
        logging.warning("ANY other webhook cannot be called, skipping notification")
        return
    try:
        response = requests.post(
            SECOND_ANY_WEBHOOK_URL,
            json={"text": message}
        )
        if response.status_code != 200:
            logging.error(f"Failed to send Second webhook notification: {response.text}")
    except Exception as e:
        logging.error(f"Error sending second webhook message: {str(e)}")
'''

def check_website(url):
    """Check a website's status with retries"""
    failure_count = 0
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, timeout=10)
            status_code = response.status_code
            
            if status_code != 200:
                failure_count += 1
                logging.debug(f"Attempt {attempt+1} for {url} failed with status {status_code}")
            else:
                # If we succeed, no need for more attempts
                break
                
        except Exception as e:
            failure_count += 1
            status_code = 0  # Use 0 to indicate connection error
            logging.debug(f"Attempt {attempt+1} for {url} failed with error: {str(e)}")
        
        # Wait before next retry if not the last attempt
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY)
    
    return status_code, failure_count

def update_website_status(url, status_code, failure_count):
    """Update website status in the database and send notifications if needed"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get previous status
    cursor.execute("SELECT status FROM websites WHERE url = ?", (url,))
    result = cursor.fetchone()
    previous_status = result[0] if result else "unknown"
    
    timestamp = datetime.now(pytz.timezone('Asia/Kathmandu')).isoformat()  # Use Asia/Kathmandu timezone
    new_status = "failed" if failure_count >= 2 else "healthy"
    
    # Always update the database
    cursor.execute(
        "UPDATE websites SET status = ?, last_status_code = ?, failure_count = ?, last_checked = ? WHERE url = ?",
        (new_status, status_code, failure_count, timestamp, url)
    )
    conn.commit()
    
    # Log the status change
    if new_status == "failed":
        log_message = f"Website {url} failed {failure_count}/{MAX_RETRIES} times. Last status code: {status_code}."
        logging.info(log_message)
        
        # Send alert if status changed from healthy to failed
        if previous_status != "failed":
            alert_message = f":warning: [{timestamp}] {log_message}"
            send_slack_notification(alert_message)
            ##UN-COMMENT IF REQUIRED
            ##second_any_webhook_message_posting_notification(alert_message)
            logging.warning(f"ALERT ALERT - {log_message}")
    else:
        log_message = f"Website {url} is healthy. Status code: {status_code}."
        logging.info(log_message)
        
        # Send recovery notification if status changed from failed to healthy
        if previous_status == "failed":
            recovery_message = f":white_check_mark: [{timestamp}] Website {url} is now healthy. Status code: {status_code}."
            send_slack_notification(recovery_message)
            ##UN-COMMENT IF REQUIRED
            ##second_any_webhook_message_posting_notification(recovery_message)
            logging.info(f"RECOVERY - {log_message}")
    
    conn.close()

def monitor_websites():
    """Main function to monitor all websites"""
    logging.info("Starting website monitoring check")
    
    for url in WEBSITES:
        status_code, failure_count = check_website(url)
        update_website_status(url, status_code, failure_count)
    
    logging.info("Completed website monitoring check")

def main():
    """Main entry point"""
    # Initialize the database
    init_database()
    
    # Run monitoring continuously
    while True:
        try:
            monitor_websites()
        except Exception as e:
            logging.error(f"Error in monitoring cycle: {str(e)}")
            logging.error('Restarting monitor cycle in 60 seconds.......')
            time.sleep(60)
        
        # Wait before next check
        time.sleep(300)  # 5 minutes between checks

if __name__ == "__main__":
    main()
