import math
from datetime import datetime

from data import DataService, HOURLY_RATES, PREMIUM_SLOTS, SLOT_CAPACITY, VEHICLE_COSTS

class BookingService:
    """Business logic for bookings, availability, and billing."""

    def __init__(self, data_service: DataService):
        self.data_service = data_service

    def calculate_booking_fee(self, slot_str, vehicle_type, start_time, end_time):
        """Calculate advanced booking fees for a time range."""
        hours = (end_time - start_time).total_seconds() / 3600
        if hours <= 0:
            return 0, 0, 0

        billed_hours = max(1, math.ceil(hours))
        rate = HOURLY_RATES.get(vehicle_type, 0)

        if billed_hours <= 6:
            base_charge = rate
        elif billed_hours <= 12:
            base_charge = rate + (billed_hours - 6) * (rate * 0.9)
        else:
            base_charge = rate + 6 * (rate * 0.9) + (billed_hours - 12) * (rate * 0.8)

        overnight_fee = 100 if end_time.date() > start_time.date() else 0
        weekend_multiplier = 1.10 if end_time.weekday() in {5, 6} else 1.0

        premium_fee_applied = 0
        if slot_str in PREMIUM_SLOTS:
            extra_premium_blocks = int(hours // 6)
            premium_fee_applied = 50 + (extra_premium_blocks * 50)

        total_charge = round((base_charge + overnight_fee + premium_fee_applied) * weekend_multiplier, 2)
        return total_charge, base_charge, premium_fee_applied

    def is_slot_available(self, slot, vehicle_type, start_time, end_time):
        """Verify whether a slot can accommodate a booking for the requested period."""
        cost = VEHICLE_COSTS.get(vehicle_type, 0)
        data = self.data_service.load_data()
        slot_data = data['slots'].get(slot)

        if not slot_data:
            return False, 'Invalid slot.'

        is_ev_vehicle = 'EV' in vehicle_type
        if is_ev_vehicle and not slot_data['is_ev']:
            return False, f'EVs cannot be booked in non-EV slot {slot}.'

        if slot_data['capacity_left'] < cost:
            return False, f'Slot {slot} is currently too full for a {vehicle_type} (Capacity Left: {slot_data["capacity_left"]}).'

        bookings_data = self.data_service.load_bookings()
        available_capacity = SLOT_CAPACITY
        physical_cost = SLOT_CAPACITY - slot_data['capacity_left']
        available_capacity -= physical_cost

        for booking in bookings_data:
            if booking['slot'] != slot or booking['status'] not in ['Confirmed', 'Active']:
                continue

            booking_start = datetime.strptime(booking['start_time'], '%Y-%m-%d %H:%M:%S')
            booking_end = datetime.strptime(booking['end_time'], '%Y-%m-%d %H:%M:%S')
            if not (end_time <= booking_start or start_time >= booking_end):
                available_capacity -= booking.get('cost', 1)

        if available_capacity < cost:
            return False, f'Slot {slot} does not have enough capacity for a {vehicle_type} during that time due to other bookings.'

        return True, 'Slot is available.'

    def add_booking(self, vehicle_number, vehicle_type, slot, start_time, end_time, total_charge, premium_fee_applied):
        """Create and persist a confirmed booking."""
        bookings_data = self.data_service.load_bookings()
        max_id = max((b['id'] for b in bookings_data), default=0)
        new_id = max_id + 1
        vehicle_number = vehicle_number.strip().upper()

        new_booking = {
            'id': new_id,
            'vehicle': vehicle_number,
            'vehicle_type': vehicle_type,
            'slot': slot,
            'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'end_time': end_time.strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'Confirmed',
            'charge': total_charge,
            'premium_fee': premium_fee_applied,
            'cost': VEHICLE_COSTS.get(vehicle_type, 1),
            'creation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        bookings_data.append(new_booking)
        self.data_service.save_bookings(bookings_data)
        return True, 'Booking confirmed and paid!'

    def cancel_booking_by_id(self, booking_id):
        """Delete a booking if it is still confirmed."""
        bookings_data = self.data_service.load_bookings()
        filtered_bookings = [b for b in bookings_data if b['id'] != booking_id]

        if len(filtered_bookings) == len(bookings_data):
            return False, 'Booking not found!'

        self.data_service.save_bookings(filtered_bookings)
        return True, 'Booking cancelled successfully!'

    def get_bookings(self):
        """Return bookings with updated status based on current time."""
        bookings_data = self.data_service.load_bookings()
        now = datetime.now()
        updated = False

        for booking in bookings_data:
            if booking['status'] == 'Completed':
                continue

            start = datetime.strptime(booking['start_time'], '%Y-%m-%d %H:%M:%S')
            end = datetime.strptime(booking['end_time'], '%Y-%m-%d %H:%M:%S')
            new_status = booking['status']

            if now > end:
                new_status = 'Completed'

            if booking['status'] != new_status:
                booking['status'] = new_status
                updated = True

        if updated:
            self.data_service.save_bookings(bookings_data)

        return bookings_data
