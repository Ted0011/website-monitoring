# Website Monitoring System

A lightweight Docker-based solution for monitoring website availability and sending alerts to Slack.

## Overview

This system monitors a list of websites for availability, tracks their status in a persistent SQLite database, and sends notifications to Slack when websites go down or recover.

## Features

- Containerized solution using Docker
- Persistent status tracking between restarts
- Automatic retry mechanism for failed checks
- Slack notifications for down/recovery events
- Comprehensive logging

## Setup

1. Clone this repository
2. Configure your websites in `app/main.py`
3. Set your Slack webhook URL in `docker-compose.yml`
4. Run with `docker-compose up -d`

## Technical Details

### Database Schema

The system uses a SQLite database with the following schema:

```sql
CREATE TABLE IF NOT EXISTS websites (
    url TEXT PRIMARY KEY,
    status TEXT,
    last_status_code INTEGER,
    last_checked TIMESTAMP,
    failure_count INTEGER DEFAULT 0
);
```

**Fields:**
- `url`: The website URL being monitored (primary key)
- `status`: Current status ("healthy" or "failed")
- `last_status_code`: HTTP status code from the most recent check
- `last_checked`: Timestamp of the last check
- `failure_count`: Number of consecutive failures

### Directory Structure

```
website-monitor/
├── docker-compose.yml
├── Dockerfile
├── README.md
├── app/
│   └── main.py
└── data/
    └── websites.db (created automatically)
```

## Configuration

Edit the `WEBSITES` list in `app/main.py` to add or remove monitored sites.
Adjust `MAX_RETRIES` and `RETRY_DELAY` for sensitivity tuning.

## Logs

Logs are stored in `/data/monitor.log` inside the container and are also available via `docker logs`.
