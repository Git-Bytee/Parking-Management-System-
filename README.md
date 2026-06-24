# Parking Management System

## Overview

An advanced desktop parking management system built with Python and Tkinter. The app supports real-time slot allocation, EV and premium slots, booking management, billing logic, penalty handling, and analytics.

## Key Features

- Interactive parking grid for live slot status
- Vehicle parking and removal with capacity checks
- EV and premium slot support
- Pre-booking system with scheduling and availability validation
- Dynamic fare calculation with weekend, overnight, and premium pricing
- Booking activation, cancellation, and conflict resolution
- Daily analytics dashboard with revenue, vehicle mix, and occupancy trends
- Persistent data storage using JSON files
- Speech notifications for better user feedback

## Tech Stack

- Python 3
- Tkinter for GUI
- JSON file persistence
- pyttsx3 for speech notifications

## Getting Started

### Prerequisites

- Python 3.8 or newer
- `pyttsx3` library

### Installation

1. Clone or download the repository.
2. Open a terminal in the project folder.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

### Run the App

```bash
python Parking_Management.py
```

## Files

- `ui.py` — Tkinter GUI and application entrypoint
- `data.py` — persistence layer for JSON storage
- `booking.py` — booking rules, availability checks, and fee calculation
- `analytics.py` — dashboard analytics and daily statistics
- `parking_data.json` — current parking and vehicle state
- `parking_bookings.json` — booking records
- `parking_log.json` — parking history logs
- `daily_analytics.json` — compiled analytics data

## Future Improvements

- Migrate storage from JSON to SQLite or a web database
- Add user authentication and admin roles
- Build a web-based frontend with Flask or FastAPI
- Add charts and visualizations for analytics
- Add email/sms notifications for booking confirmations
