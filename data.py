import json
import os
from datetime import date, timedelta

MAX_SLOTS = 50
PREMIUM_FEE = 50
SLOT_CAPACITY = 3
DATA_FILE = 'parking_data.json'
LOG_FILE = 'parking_log.json'
ANALYTICS_FILE = 'daily_analytics.json'
BOOKINGS_FILE = 'parking_bookings.json'
PREMIUM_SLOTS = {str(i) for i in range(1, 11)}
EV_SLOTS = {str(i) for i in range(8, 11)} | {str(i) for i in range(41, 51)}

VEHICLE_COSTS = {
    'Bike': 1,
    'Car': 3,
    'EV Bike': 1,
    'EV Car': 3
}

HOURLY_RATES = {
    'Bike': 50,
    'Car': 100,
    'EV Bike': 80,
    'EV Car': 150
}

class DataService:
    """Service responsible for reading and writing persistent parking data."""

    def __init__(self,
                 data_file=DATA_FILE,
                 log_file=LOG_FILE,
                 analytics_file=ANALYTICS_FILE,
                 bookings_file=BOOKINGS_FILE):
        self.data_file = data_file
        self.log_file = log_file
        self.analytics_file = analytics_file
        self.bookings_file = bookings_file

    def initialize_data_files(self):
        """Ensure all storage files exist with a valid initial structure."""
        if not os.path.exists(self.data_file):
            slots_data = {
                str(i): {
                    'vehicles': [],
                    'capacity_left': SLOT_CAPACITY,
                    'is_ev': str(i) in EV_SLOTS,
                    'is_premium': str(i) in PREMIUM_SLOTS
                }
                for i in range(1, MAX_SLOTS + 1)
            }
            self.save_data({'slots': slots_data, 'vehicles': {}})

        if not os.path.exists(self.log_file):
            self.save_json(self.log_file, [])

        if not os.path.exists(self.bookings_file):
            self.save_json(self.bookings_file, [])

        if not os.path.exists(self.analytics_file):
            self.save_json(self.analytics_file, [])

        self.prune_old_analytics()

    def load_data(self):
        """Load the parking slot and vehicle state."""
        return self.load_json(self.data_file, default=self._default_data())

    def save_data(self, data):
        """Save the parking slot and vehicle state."""
        self.save_json(self.data_file, data)

    def load_log_data(self):
        """Load historic parking log entries."""
        return self.load_json(self.log_file, default=[])

    def save_to_log(self, log_entry):
        """Append a new entry to the parking history log."""
        logs = self.load_log_data()
        logs.append(log_entry)
        self.save_json(self.log_file, logs)

    def load_bookings(self):
        """Load current and past booking records."""
        return self.load_json(self.bookings_file, default=[])

    def save_bookings(self, bookings):
        """Save bookings to storage."""
        self.save_json(self.bookings_file, bookings)

    def load_analytics_data(self):
        """Load saved analytics summary data."""
        return self.load_json(self.analytics_file, default=[])

    def save_analytics_data(self, analytics_data):
        """Save analytics summary data."""
        self.save_json(self.analytics_file, analytics_data)

    def prune_old_analytics(self):
        """Keep only analytics data from the last 15 days."""
        analytics = self.load_analytics_data()
        cutoff_date = date.today() - timedelta(days=15)
        recent_analytics = [
            entry for entry in analytics
            if self._parse_date(entry.get('date')) >= cutoff_date
        ]
        if len(recent_analytics) < len(analytics):
            self.save_analytics_data(recent_analytics)

    def load_json(self, path, default=None):
        """Load JSON from a file and return a default value on failure."""
        if default is None:
            default = {}

        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return default

    def save_json(self, path, data):
        """Persist JSON data with indentation."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def _default_data(self):
        return {
            'slots': {
                str(i): {
                    'vehicles': [],
                    'capacity_left': SLOT_CAPACITY,
                    'is_ev': str(i) in EV_SLOTS,
                    'is_premium': str(i) in PREMIUM_SLOTS
                }
                for i in range(1, MAX_SLOTS + 1)
            },
            'vehicles': {}
        }

    @staticmethod
    def _parse_date(date_str):
        try:
            return date.fromisoformat(date_str)
        except (TypeError, ValueError):
            return date.min
