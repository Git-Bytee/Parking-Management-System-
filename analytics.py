from datetime import datetime, date

from data import DataService, VEHICLE_COSTS

class AnalyticsService:
    """Compute dashboard statistics and maintain analytics history."""

    def __init__(self, data_service: DataService):
        self.data_service = data_service

    def update_and_get_analytics_dates(self):
        """Rebuild analytics from today's log and return the most recent dates."""
        today_str = str(date.today())
        logs = self.data_service.load_log_data()
        today_logs = [log for log in logs if log['exit_time'].startswith(today_str)]

        revenue_from_exits = sum(log['charge'] for log in today_logs)
        premium_from_exits = sum(log.get('premium_fee', 0) for log in today_logs)
        penalty_from_exits = sum(log.get('penalty_fee', 0) for log in today_logs)
        total_vehicles = len(today_logs)
        vehicle_counts = {
            v_type: sum(1 for log in today_logs if log['type'] == v_type)
            for v_type in VEHICLE_COSTS.keys()
        }
        total_duration_hours = sum(log['duration_hours'] for log in today_logs)
        avg_duration = total_duration_hours / total_vehicles if total_vehicles > 0 else 0

        bookings = self.data_service.load_bookings()
        new_bookings_today = [b for b in bookings if b.get('creation_time', '').startswith(today_str)]
        revenue_from_new_bookings = sum(b.get('charge', 0) for b in new_bookings_today)
        premium_from_new_bookings = sum(b.get('premium_fee', 0) for b in new_bookings_today)

        total_revenue = revenue_from_exits + revenue_from_new_bookings
        premium_revenue = premium_from_exits + premium_from_new_bookings

        today_stats_obj = {
            'date': today_str,
            'total_revenue': total_revenue,
            'premium_revenue': premium_revenue,
            'penalty_revenue': penalty_from_exits,
            'total_vehicles': total_vehicles,
            'avg_duration_hours': avg_duration,
            'vehicle_counts': vehicle_counts
        }

        all_analytics = self.data_service.load_analytics_data()
        found = False

        for i, entry in enumerate(all_analytics):
            if entry['date'] == today_str:
                all_analytics[i] = today_stats_obj
                found = True
                break

        if not found:
            all_analytics.append(today_stats_obj)

        self.data_service.save_analytics_data(all_analytics)

        formatted_dates = []
        sorted_analytics = sorted(all_analytics, key=lambda x: x['date'], reverse=True)
        for entry in sorted_analytics[:15]:
            date_str = entry['date']
            try:
                weekday = datetime.strptime(date_str, '%Y-%m-%d').strftime('%A')
                formatted_dates.append(f'{date_str} ({weekday})')
            except ValueError:
                formatted_dates.append(date_str)

        return formatted_dates, today_str

    def get_stats_for_date(self, target_date_str):
        """Return analytics stats for a specific date."""
        today_str = str(date.today())
        if target_date_str == today_str:
            logs = self.data_service.load_log_data()
            today_logs = [log for log in logs if log['exit_time'].startswith(target_date_str)]

            revenue_from_exits = sum(log['charge'] for log in today_logs)
            premium_from_exits = sum(log.get('premium_fee', 0) for log in today_logs)
            penalty_from_exits = sum(log.get('penalty_fee', 0) for log in today_logs)
            total_vehicles = len(today_logs)
            vehicle_counts = {
                v_type: sum(1 for log in today_logs if log['type'] == v_type)
                for v_type in VEHICLE_COSTS.keys()
            }
            total_duration_hours = sum(log['duration_hours'] for log in today_logs)
            avg_duration = total_duration_hours / total_vehicles if total_vehicles > 0 else 0

            bookings = self.data_service.load_bookings()
            new_bookings_today = [b for b in bookings if b.get('creation_time', '').startswith(target_date_str)]
            revenue_from_new_bookings = sum(b.get('charge', 0) for b in new_bookings_today)
            premium_from_new_bookings = sum(b.get('premium_fee', 0) for b in new_bookings_today)

            total_revenue = revenue_from_exits + revenue_from_new_bookings
            premium_revenue = premium_from_exits + premium_from_new_bookings

            return {
                'total_revenue': total_revenue,
                'premium_revenue': premium_revenue,
                'penalty_revenue': penalty_from_exits,
                'total_vehicles': total_vehicles,
                'avg_duration_hours': avg_duration,
                'vehicle_counts': vehicle_counts
            }

        all_analytics = self.data_service.load_analytics_data()
        return next((item for item in all_analytics if item['date'] == target_date_str), {})
