#!/usr/bin/env python3
import os
import time
import sqlite3
import json
import requests
import logging
import hashlib
from datetime import datetime, timedelta
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

# Configuration
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')
SECOND_MS_TEAM_WEBHOOK_URL = os.environ.get('SECOND_MS_TEAM_WEBHOOK_URL')
#SLACK_PHONE_CALL_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')
SLACK_API_TOKEN='_____SLACK__________API________TOKEN___'
ALERT_CHANNEL_ID='C08EFE7DMEC'
CALL_USERS='U086W59JJ11,U073G707R17,U06CTN9370T'
DB_PATH = "/data/websites.db"
MAX_RETRIES = 10
RETRY_DELAY = 5  # seconds
MIN_DOWNTIME_FOR_CALL = 5 * 60  # 5 minutes in seconds

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
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS websites (
        url TEXT PRIMARY KEY,
        status TEXT,
        last_status_code INTEGER,
        last_checked TIMESTAMP,
        failure_count INTEGER DEFAULT 0,
        first_failure_time TIMESTAMP,
        downtime_duration INTEGER DEFAULT 0,
        last_downtime_minutes REAL DEFAULT 0  
    )
    ''')
    cursor.execute('''
    CREATE VIEW IF NOT EXISTS website_downtimes AS
    SELECT 
        url,
        status,
        last_status_code,
        datetime(last_checked) as last_checked,
        failure_count,
        datetime(first_failure_time) as first_failure_time,
        last_downtime_minutes as downtime_minutes,
        CASE 
            WHEN last_downtime_minutes > 5 THEN 'YES' 
            ELSE 'NO' 
        END as exceeded_threshold
    FROM websites
    ORDER BY last_checked DESC
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

def send_second_ms_team_notification(message):
    """Send a notification to MS-Team"""
    if not SECOND_MS_TEAM_WEBHOOK_URL:
        logging.warning("MS-TEAM webhook URL not set, skipping notification")
        return
    try:
        response = requests.post(
                SECOND_MS_TEAM_WEBHOOK_URL,
                json={"text": message}
        )
        if response.status_code != 200:
            logging.error(f"Failed to send MS-TEAM notification: {response.text}")
            
    except Exception as e:
        logging.error(f"Error sending MS-TEAM notification: {str(e)}")
'''
def make_slack_phone_call(message):
    """Make a phone call via Slack"""
    if not SLACK_PHONE_CALL_WEBHOOK_URL:
        logging.warning("Slack phone call webhook URL not set, skipping phone call")
        return
    
    try:
        response = requests.post(
            SLACK_PHONE_CALL_WEBHOOK_URL,
            json={
                "text": message,
                "action": "call"  # This might vary based on your Slack app configuration
            }
        )
        if response.status_code != 200:
            logging.error(f"Failed to make Slack phone call: {response.text}")
    except Exception as e:
        logging.error(f"Error making Slack phone call: {str(e)}")
'''
def make_slack_phone_call(message):
    """Make an urgent Slack notification that can trigger phone alerts"""
    slack_token = os.environ.get('SLACK_API_TOKEN')
    alert_channel = os.environ.get('ALERT_CHANNEL_ID')
    call_users = os.environ.get('CALL_USERS')
    
    if not all([slack_token, alert_channel, call_users]):
        logging.warning("Slack call configuration incomplete")
        return
    
    try:
        # 1. Post urgent message
        response = requests.post(
            'https://slack.com/api/chat.postMessage',
            headers={'Authorization': f'Bearer {slack_token}'},
            json={
                'channel': alert_channel,
                'text': f"<!here> :rotating_light: URGENT DOWNTIME ALERT :rotating_light:",
                'blocks': [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{message}*\nThis requires immediate attention!"
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Acknowledge"
                                },
                                "style": "danger",
                                "value": "acknowledge"
                            }
                        ]
                    }
                ]
            }
        )
        
        if response.status_code != 200 or not response.json().get('ok'):
            logging.error(f"Slack message error: {response.text}")
        
        # 2. Trigger phone notifications via Slack's reminder API
        for user_id in call_users.split(','):
            reminder_response = requests.post(
                'https://slack.com/api/reminders.add',
                headers={'Authorization': f'Bearer {slack_token}'},
                json={
                    'text': f"URGENT: {message}",
                    'user': user_id,
                    'time': 'now'
                }
            )
            
            if not reminder_response.json().get('ok'):
                logging.error(f"Slack reminder error for user {user_id}: {reminder_response.text}")
            
    except Exception as e:
        logging.error(f"Slack notification error: {str(e)}")
        
def check_website(url):
    """Check a website's status with retries"""
    failure_count = 0
    status_code = 0  # Default to 0 for connection errors
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, timeout=10)
            status_code = response.status_code
            
            if status_code == 200:
                # If we succeed, reset failure count and break
                failure_count = 0
                break
            else:
                failure_count += 1
                logging.debug(f"Attempt {attempt+1} for {url} failed with status {status_code}")
                
        except Exception as e:
            failure_count += 1
            status_code = 0  # Use 0 to indicate connection error
            logging.debug(f"Attempt {attempt+1} for {url} failed with error: {str(e)}")
        
        # Wait before next retry if not the last attempt
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY)
    
    # Return the final status code and total failure count
    return status_code, failure_count
'''    
def update_website_status(url, status_code, failure_count):
    """Update website status in the database and send notifications if needed"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get previous status and failure time
    cursor.execute("SELECT status, failure_count, first_failure_time FROM websites WHERE url = ?", (url,))
    result = cursor.fetchone()
    previous_status = result[0] if result else "unknown"
    previous_failure_count = result[1] if result else 0
    previous_first_failure_time = result[2] if result else None
    
    timestamp = datetime.now(pytz.timezone('Asia/Kathmandu'))
    
    # Website is considered failed only if all retries failed
    new_status = "failed" if failure_count >= MAX_RETRIES else "healthy"
    
    # Calculate downtime duration if this is a recovery
    downtime_duration = 0
    if new_status == "healthy" and previous_status == "failed" and previous_first_failure_time:
        first_failure_time = datetime.fromisoformat(previous_first_failure_time)
        downtime_duration = (timestamp - first_failure_time).total_seconds()
    
    # Update first_failure_time if this is a new failure
    first_failure_time_to_store = None
    if new_status == "failed" and previous_status != "failed":
        first_failure_time_to_store = timestamp.isoformat()
    elif previous_first_failure_time:
        first_failure_time_to_store = previous_first_failure_time
    
    # Always update the database
    cursor.execute(
        "UPDATE websites SET status = ?, last_status_code = ?, failure_count = ?, last_checked = ?, first_failure_time = ?, downtime_duration = ? WHERE url = ?",
        (new_status, status_code, failure_count, timestamp.isoformat(), first_failure_time_to_store, downtime_duration, url)
    )
    conn.commit()
    
    # Log the status change
    if new_status == "failed":
        log_message = f"Website {url} failed all {MAX_RETRIES} attempts. Last status code: {status_code}."
        logging.info(log_message)
        
        # Only send alert if this is a new complete failure (previous failure count was less than MAX_RETRIES)
        if previous_failure_count < MAX_RETRIES:
            alert_message = f":warning: [{timestamp}] {log_message}"
            alert_message_teams = f":S [{timestamp}] {log_message}"
            send_slack_notification(alert_message)
            send_second_ms_team_notification(alert_message_teams)
            logging.warning(f"ALERT ALERT - {log_message}")
    else:
        log_message = f"Website {url} is healthy. Status code: {status_code}."
        logging.info(log_message)
        
        # Send recovery notification only if it was previously in complete failure
        if previous_status == "failed" and previous_failure_count >= MAX_RETRIES:
            downtime_minutes = round(downtime_duration / 60, 1)
            recovery_message = f":white_check_mark: [{timestamp}] Website {url} is now healthy after {downtime_minutes} minutes of downtime. Status code: {status_code}."
            recovery_message_teams = f":D [{timestamp}] Website {url} is now healthy after {downtime_minutes} minutes of downtime. Status code: {status_code}."
            send_slack_notification(recovery_message)
            send_second_ms_team_notification(recovery_message_teams)
            logging.info(f"RECOVERY - {log_message}")
            
            # Make phone call if downtime was more than threshold
            if downtime_duration > MIN_DOWNTIME_FOR_CALL:
                phone_message = f"URGENT: Website {url} was down for {downtime_minutes} minutes and is now back up. Please investigate!"
                make_slack_phone_call(phone_message)
    
    conn.close()
'''
def update_website_status(url, status_code, failure_count):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get previous status
    cursor.execute("SELECT status, failure_count, first_failure_time, last_downtime_minutes FROM websites WHERE url = ?", (url,))
    result = cursor.fetchone()
    previous_status = result[0] if result else "unknown"
    previous_failure_count = result[1] if result else 0
    previous_first_failure_time = result[2] if result else None
    previous_downtime_minutes = result[3] if result else 0
    
    timestamp = datetime.now(pytz.timezone('Asia/Kathmandu'))
    new_status = "failed" if failure_count >= MAX_RETRIES else "healthy"
    
    # Calculate current downtime for sites that are still down
    current_downtime_minutes = 0
    current_downtime_seconds = 0
    if new_status == "failed" and previous_first_failure_time:
        first_failure_time = datetime.fromisoformat(previous_first_failure_time)
        current_downtime_seconds = (timestamp - first_failure_time).total_seconds()
        current_downtime_minutes = round(current_downtime_seconds / 60, 2)
    
    # Calculate downtime for sites that have recovered
    recovery_downtime_minutes = 0
    if new_status == "healthy" and previous_status == "failed" and previous_first_failure_time:
        first_failure_time = datetime.fromisoformat(previous_first_failure_time)
        downtime_seconds = (timestamp - first_failure_time).total_seconds()
        recovery_downtime_minutes = round(downtime_seconds / 60, 2)
    
    # Update database
    cursor.execute('''
    UPDATE websites 
    SET status = ?, 
        last_status_code = ?, 
        failure_count = ?, 
        last_checked = ?,
        first_failure_time = CASE 
            WHEN ? = 'failed' AND status != 'failed' THEN ?
            ELSE first_failure_time 
        END,
        downtime_duration = ?,
        last_downtime_minutes = ?
    WHERE url = ?
    ''', (
        new_status, 
        status_code, 
        failure_count, 
        timestamp.isoformat(),
        new_status,
        timestamp.isoformat(),
        recovery_downtime_minutes * 60 if new_status == "healthy" else current_downtime_seconds,
        recovery_downtime_minutes if new_status == "healthy" else current_downtime_minutes,
        url
    ))
    
    conn.commit()
    
    # Notification logic
    if new_status == "failed":
        log_message = f"Website {url} failed all {MAX_RETRIES} attempts. Status code: {status_code}"
        if previous_failure_count < MAX_RETRIES:
            alert_message = f":warning: [{timestamp}] {log_message}"
            alert_message_teams = f":S [{timestamp}] {log_message}"
            send_slack_notification(alert_message)
            send_second_ms_team_notification(alert_message_teams)
        
        # Check if site has been down for more than threshold and we haven't sent a call yet
        # We can track if we've sent a call by checking previous_downtime_minutes
        # If it's greater than MIN_DOWNTIME_FOR_CALL/60, we've likely already sent a call
        if current_downtime_seconds > MIN_DOWNTIME_FOR_CALL and previous_downtime_minutes < (MIN_DOWNTIME_FOR_CALL / 60):
            phone_message = f"URGENT: {url} has been down for more than {MIN_DOWNTIME_FOR_CALL/60} minutes!"
            make_slack_phone_call(phone_message)
            logging.warning(f"PHONE ALERT - {url} down for {current_downtime_minutes} minutes")
    else:
        log_message = f"Website {url} is healthy. Status code: {status_code}"
        if previous_status == "failed" and previous_failure_count >= MAX_RETRIES:
            recovery_message = f":white_check_mark: [{timestamp}] Website recovered after {recovery_downtime_minutes} minutes"
            recovery_message_teams = f":D [{timestamp}] Website {url} is now healthy after {downtime_minutes} minutes of downtime. Status code: {status_code}."
            send_slack_notification(recovery_message)
            send_second_ms_team_notification(recovery_message_teams)
            
            if recovery_downtime_minutes > (MIN_DOWNTIME_FOR_CALL / 60):
                phone_message = f"RECOVERY NOTICE: {url} was down for {recovery_downtime_minutes} minutes but is now back up!"
                make_slack_phone_call(phone_message)
    
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
#    test_url = WEBSITES[0]
#    update_website_status(test_url, 0, MAX_RETRIES)  # Simulate failure
#    time.sleep(310)  # Wait 5+ minutes
#    update_website_status(test_url, 200, 0)  # Simulate recovery
    # Run monitoring continuously
    while True:
        try:
            monitor_websites()
        except Exception as e:
            logging.error(f"Error in monitoring cycle: {str(e)}")
            logging.error('Restarting monitor cycle in 60 seconds.......')
            time.sleep(60)
        
        # Wait before next check
        time.sleep(120)  # 2 minutes between checks

if __name__ == "__main__":
    main()


