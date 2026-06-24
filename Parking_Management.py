import json
import os
from datetime import datetime, date, timedelta
import tkinter as tk
from tkinter import messagebox, ttk
import math
import threading
import pyttsx3

try:
    engine = pyttsx3.init()
    rate = engine.getProperty('rate')
    engine.setProperty('rate', rate - 10)
    
except Exception:
    print("pyttsx3 not found. Speech features will be disabled.")
    
    class DummyEngine:
        def say(self, text): pass
        def runAndWait(self): pass
        def setProperty(self, name, value): pass
        def getProperty(self, name): return 150
            
    engine = DummyEngine()

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

def _speak_thread(text):
    try:
        engine.say(text)
        engine.runAndWait()
        
    except Exception as e:
        print(f"Speech engine error: {e}")

def speak(text):
    if engine:
        threading.Thread(target=_speak_thread, args=(text,), daemon=True).start()

def format_vehicle_number_for_speech(vehicle_number):
    spoken_form = ""
    
    for char in vehicle_number.strip().upper():
        if char == '0':
            spoken_form += "zero "
            
        elif char == 'E':
            spoken_form += "ee "
            
        else:
            spoken_form += f"{char} "
            
    return spoken_form.strip()

def show_message_after_speech(msg_type, title, message, delay=0.1):
    def show_msg():
        if msg_type == "info":
            messagebox.showinfo(title, message)
            
        elif msg_type == "warning":
            messagebox.showwarning(title, message)
            
        elif msg_type == "error":
            messagebox.showerror(title, message)
            
    threading.Timer(delay, show_msg).start()

def initialize_data_files():
    if not os.path.exists(DATA_FILE):
        slots_data = {}
        
        for i in range(1, MAX_SLOTS + 1):
            slot_id = str(i)
            slots_data[slot_id] = {
                'vehicles': [], 
                'capacity_left': SLOT_CAPACITY,
                'is_ev': slot_id in EV_SLOTS,
                'is_premium': slot_id in PREMIUM_SLOTS
                }
        save_data({'slots': slots_data, 'vehicles': {}})
        
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w') as f:
            json.dump([], f)
            
    if not os.path.exists(BOOKINGS_FILE):
        with open(BOOKINGS_FILE, 'w') as f:
            json.dump([], f)
    
    if not os.path.exists(ANALYTICS_FILE):
        with open(ANALYTICS_FILE, 'w') as f:
            json.dump([], f)
    
    prune_old_analytics()

def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
        
    except (FileNotFoundError, json.JSONDecodeError):
        messagebox.showerror("Error", f"Could not read {DATA_FILE}. A new one will be created.")
        slots_data = {}
        
        for i in range(1, MAX_SLOTS + 1):
            slot_id = str(i)
            slots_data[slot_id] = {
                'vehicles': [], 
                'capacity_left': SLOT_CAPACITY,
                'is_ev': slot_id in EV_SLOTS, 
                'is_premium': slot_id in PREMIUM_SLOTS
            }
            
        default_data = {'slots': slots_data, 'vehicles': {}}
        save_data(default_data)
        return default_data

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def load_log_data():
    try:
        with open(LOG_FILE, 'r') as f:
            return json.load(f)
        
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_to_log(log_entry):
    logs = load_log_data()
    logs.append(log_entry)
    
    with open(LOG_FILE, 'w') as f:
        json.dump(logs, f, indent=4)

def load_bookings():
    try:
        with open(BOOKINGS_FILE, 'r') as f:
            return json.load(f)
        
    except (FileNotFoundError, json.JSONDecodeError):
        messagebox.showerror("Error", f"Could not read {BOOKINGS_FILE}. A new one will be created.")
        default_bookings = []
        save_bookings(default_bookings)
        return default_bookings

def save_bookings(data):
    with open(BOOKINGS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def load_analytics_data():
    try:
        with open(ANALYTICS_FILE, 'r') as f:
            return json.load(f)
        
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_analytics_data(data):
    with open(ANALYTICS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def prune_old_analytics():
    analytics = load_analytics_data()
    
    if not analytics:
        return
    
    cutoff_date = date.today() - timedelta(days=15)
    
    recent_analytics = [
        entry for entry in analytics
        if datetime.strptime(entry['date'], '%Y-%m-%d').date() >= cutoff_date
        ]
    
    if len(recent_analytics) < len(analytics):
        save_analytics_data(recent_analytics)

def update_and_get_analytics_dates():
    today_str = str(date.today())
    logs = load_log_data()
    today_logs = [log for log in logs if log['exit_time'].startswith(today_str)]
    
    revenue_from_exits = sum(log['charge'] for log in today_logs)
    premium_from_exits = sum(log.get('premium_fee', 0) for log in today_logs)
    penalty_from_exits = sum(log.get('penalty_fee', 0) for log in today_logs) # <-- NEW
    total_vehicles = len(today_logs) 
    vehicle_counts = {v_type: sum(1 for log in today_logs if log['type'] == v_type) 
                        for v_type in VEHICLE_COSTS.keys()}
    total_duration_hours = sum(log['duration_hours'] for log in today_logs)
    avg_duration = (total_duration_hours / total_vehicles) if total_vehicles > 0 else 0

    all_bookings = load_bookings()
    new_bookings_today = [
        b for b in all_bookings 
        if b.get('creation_time', '2000-01-01').startswith(today_str)
        ]
    
    revenue_from_new_bookings = sum(b.get('charge', 0) for b in new_bookings_today)
    premium_from_new_bookings = sum(b.get('premium_fee', 0) for b in new_bookings_today)
    total_revenue = revenue_from_exits + revenue_from_new_bookings
    premium_revenue = premium_from_exits + premium_from_new_bookings
    
    today_stats_obj = {
        "date": today_str,
        "total_revenue": total_revenue,
        "premium_revenue": premium_revenue,
        "penalty_revenue": penalty_from_exits, # <-- NEW
        "total_vehicles": total_vehicles, 
        "avg_duration_hours": avg_duration,
        "vehicle_counts": vehicle_counts 
        }
    
    all_analytics = load_analytics_data()
    found = False
    
    for i, entry in enumerate(all_analytics):
        if entry['date'] == today_str:
            all_analytics[i] = today_stats_obj
            found = True
            break
    
    if not found:
        all_analytics.append(today_stats_obj)
        
    save_analytics_data(all_analytics)
    formatted_dates = []
    sorted_analytics = sorted(all_analytics, key=lambda x: x['date'], reverse=True)
    
    for entry in sorted_analytics[:15]:
        date_str = entry['date']
        
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            weekday_name = date_obj.strftime('%A')
            formatted_dates.append(f"{date_str} ({weekday_name})")
            
        except ValueError:
            formatted_dates.append(date_str) 

    return formatted_dates, today_str

def calculate_booking_fee(slot_str, vehicle_type, start_time, end_time):
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

    overnight_fee = 0
    if end_time.date() > start_time.date():
        overnight_fee = 100

    if end_time.weekday() == 5 or 6:
        weekend_multiplier = 1.10
        
    else:
        weekend_multiplier = 1.0

    premium_fee_applied = 0
    if slot_str in PREMIUM_SLOTS:
        extra_premium_blocks = int(hours // 6)
        premium_fee_applied = PREMIUM_FEE + (extra_premium_blocks * 50)

    total_charge = (base_charge + overnight_fee + premium_fee_applied) * weekend_multiplier
    total_charge = round(total_charge, 2)
    return total_charge, base_charge, premium_fee_applied

def is_slot_available(slot, vehicle_type, start_time, end_time):
    cost = VEHICLE_COSTS[vehicle_type]
    
    data = load_data()
    slot_data = data['slots'].get(slot)
    
    if not slot_data:
        return False, "Invalid slot."
        
    is_ev_vehicle = 'EV' in vehicle_type
    if is_ev_vehicle and not slot_data['is_ev']:
        return False, f"EVs cannot be booked in non-EV slot {slot}."

    if slot_data['capacity_left'] < cost:
        return False, f"Slot {slot} is currently too full for a {vehicle_type} (Capacity Left: {slot_data['capacity_left']})."
    
    bookings_data = load_bookings()
    available_capacity = SLOT_CAPACITY
    physical_cost = SLOT_CAPACITY - slot_data['capacity_left']
    available_capacity -= physical_cost
    
    for booking in bookings_data:
        if booking['slot'] == slot and booking['status'] in ['Confirmed', 'Active']:
            booking_start = datetime.strptime(booking['start_time'], "%Y-%m-%d %H:%M:%S")
            booking_end = datetime.strptime(booking['end_time'], "%Y-%m-%d %H:%M:%S")
            
            if not (end_time <= booking_start or start_time >= booking_end):
                available_capacity -= booking.get('cost', 1) 
    
    if available_capacity < cost:
        return False, f"Slot {slot} does not have enough capacity for a {vehicle_type} during that time due to other bookings."
        
    return True, "Slot is available."

def add_booking(vehicle_number, vehicle_type, slot, start_time, end_time, total_charge, premium_fee_applied):
    vehicle_number = vehicle_number.strip().upper()
    bookings_data = load_bookings()
    max_id = max(b['id'] for b in bookings_data) if bookings_data else 0
    new_id = max_id + 1

    new_booking = {
        'id': new_id,
        'vehicle': vehicle_number,
        'vehicle_type': vehicle_type,
        'slot': slot,
        'start_time': start_time.strftime("%Y-%m-%d %H:%M:%S"),
        'end_time': end_time.strftime("%Y-%m-%d %H:%M:%S"),
        'status': 'Confirmed',
        'charge': total_charge,
        'premium_fee': premium_fee_applied,
        'cost': VEHICLE_COSTS[vehicle_type],
        'creation_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S") 
        }
    
    bookings_data.append(new_booking)
    save_bookings(bookings_data)
    return True, "Booking Confirmed and Paid!"

def cancel_booking_by_id(booking_id):
    bookings_data = load_bookings()
    booking_found = False
    
    for i, booking in enumerate(bookings_data):
        if booking['id'] == booking_id:
            del bookings_data[i]
            booking_found = True
            break
            
    if booking_found:
        save_bookings(bookings_data)
        return True, "Booking cancelled successfully!"
    
    else:
        return False, "Booking not found!"

def get_bookings():
    bookings_data = load_bookings()
    now = datetime.now()
    
    needs_save = False
    for booking in bookings_data:
        if booking['status'] == 'Completed':
            continue
            
        start = datetime.strptime(booking['start_time'], "%Y-%m-%d %H:%M:%S")
        end = datetime.strptime(booking['end_time'], '%Y-%m-%d %H:%M:%S')
        new_status = booking['status']
        
        if booking['status'] == 'Active' and now > end:
            new_status = 'Completed'
            
        elif booking['status'] == 'Confirmed' and now > end:
            new_status = 'Completed' 
        
        if booking['status'] != new_status:
            booking['status'] = new_status
            needs_save = True
            
    if needs_save:
        save_bookings(bookings_data)
            
    return bookings_data

def hide_all_tabs():
    for tab_key in ['home_tab', 'parking_tab', 'dashboard_tab', 'bookings_tab']:
        
        if tab_key in ui:
            ui[tab_key].pack_forget()

def show_home_tab():
    hide_all_tabs()
    ui['home_tab'].pack(fill=tk.BOTH, expand=True)
    update_home_stats()

def show_parking_tab():
    hide_all_tabs()
    ui['parking_tab'].pack(fill=tk.BOTH, expand=True)
    update_slots_display()
    update_action_frames(None)

def show_dashboard_tab():
    hide_all_tabs()
    ui['dashboard_tab'].pack(fill=tk.BOTH, expand=True)
    refresh_dashboard_view()

def show_bookings_tab():
    hide_all_tabs()
    ui['bookings_tab'].pack(fill=tk.BOTH, expand=True)
    refresh_bookings()
    update_booking_slot_options() 
    
def update_home_stats():
    data = load_data()
    occupied_slots_count = sum(1 for s in data['slots'].values() if s['capacity_left'] < SLOT_CAPACITY)
    
    ui['stats_labels']['total_slots'].config(text=str(MAX_SLOTS))
    ui['stats_labels']['available_slots'].config(text=str(MAX_SLOTS - occupied_slots_count))
    ui['stats_labels']['occupied_slots'].config(text=str(occupied_slots_count))
    ui['stats_labels']['vehicles_parked'].config(text=str(len(data['vehicles'])))

def on_analytics_date_selected(event=None):
    selected_formatted_string = ui['analytics_date_var'].get()
    
    if selected_formatted_string and selected_formatted_string != "No Data":
        target_date_str = selected_formatted_string.split(" ")[0]
        update_dashboard_stats(target_date_str)

def refresh_dashboard_view():
    all_dates_formatted, today_str = update_and_get_analytics_dates()
    ui['analytics_date_combo']['values'] = all_dates_formatted
    today_formatted_str = ""
    
    for formatted_date in all_dates_formatted:
        if formatted_date.startswith(today_str):
            today_formatted_str = formatted_date
            break
            
    if today_formatted_str:
        ui['analytics_date_var'].set(today_formatted_str)
        
    elif all_dates_formatted:
        ui['analytics_date_var'].set(all_dates_formatted[0])
        
    else:
        ui['analytics_date_var'].set("No Data")
        
    update_dashboard_stats(today_str)

def update_dashboard_stats(target_date_str):
    stats_to_display = {}
    today_str = str(date.today())
    
    try:
        date_obj = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        weekday_name = date_obj.strftime('%A') 
        
    except ValueError:
        weekday_name = "" 

    if target_date_str == today_str:
        logs = load_log_data()
        today_logs = [log for log in logs if log['exit_time'].startswith(target_date_str)]
        
        revenue_from_exits = sum(log['charge'] for log in today_logs)
        premium_from_exits = sum(log.get('premium_fee', 0) for log in today_logs)
        penalty_from_exits = sum(log.get('penalty_fee', 0) for log in today_logs) 
        total_vehicles = len(today_logs) 
        vehicle_counts = {v_type: sum(1 for log in today_logs if log['type'] == v_type) 
                            for v_type in VEHICLE_COSTS.keys()}
        total_duration_hours = sum(log['duration_hours'] for log in today_logs)
        avg_duration = (total_duration_hours / total_vehicles) if total_vehicles > 0 else 0
        
        all_bookings = load_bookings()
        new_bookings_today = [
            b for b in all_bookings 
            if b.get('creation_time', '2000-01-01').startswith(target_date_str)
            ]
        
        revenue_from_new_bookings = sum(b.get('charge', 0) for b in new_bookings_today)
        premium_from_new_bookings = sum(b.get('premium_fee', 0) for b in new_bookings_today)
        total_revenue = revenue_from_exits + revenue_from_new_bookings
        premium_revenue = premium_from_exits + premium_from_new_bookings
        
        stats_to_display = {
            "total_revenue": total_revenue,
            "premium_revenue": premium_revenue,
            "penalty_revenue": penalty_from_exits, # <-- NEW
            "total_vehicles": total_vehicles, 
            "avg_duration_hours": avg_duration,
            "vehicle_counts": vehicle_counts 
            }
        
        ui['dashboard_title_label'].config(text=f"Today's Analytics ({weekday_name})")

    else:
        all_analytics = load_analytics_data()
        found_stats = next((item for item in all_analytics if item["date"] == target_date_str), None)
        
        if found_stats:
            stats_to_display = found_stats
            
        else:
            stats_to_display = {"vehicle_counts": {}} 
            
        ui['dashboard_title_label'].config(text=f"Analytics for {target_date_str} ({weekday_name})")

    ui['dashboard_labels']['revenue'].config(text=f"₹{stats_to_display.get('total_revenue', 0):.2f}")
    ui['dashboard_labels']['premium_revenue'].config(text=f"₹{stats_to_display.get('premium_revenue', 0):.2f}")
    ui['dashboard_labels']['penalty_revenue'].config(text=f"₹{stats_to_display.get('penalty_revenue', 0):.2f}") # <-- NEW
    ui['dashboard_labels']['total_vehicles'].config(text=str(stats_to_display.get('total_vehicles', 0)))
    ui['dashboard_labels']['avg_duration'].config(text=f"{stats_to_display.get('avg_duration_hours', 0):.1f} hours")
    
    vehicle_counts = stats_to_display.get('vehicle_counts', {})
    ui['dashboard_labels']['cars'].config(text=str(vehicle_counts.get('Car', 0)))
    ui['dashboard_labels']['bike'].config(text=str(vehicle_counts.get('Bike', 0)))
    ui['dashboard_labels']['ev_cars'].config(text=str(vehicle_counts.get('EV Car', 0)))
    ui['dashboard_labels']['ev_bike'].config(text=str(vehicle_counts.get('EV Bike', 0)))

def update_action_frames(selected_slot_data):
    ui['park_action_frame'].pack_forget()
    ui['remove_action_frame'].pack_forget()
    
    if selected_slot_data is None:
        ui['action_title_label'].config(text="Select a Slot to Begin")
        return

    slot_num = ui['selected_slot'].get()
    title_text = f"Actions for Slot {slot_num}"
    if selected_slot_data.get('is_premium'): title_text += " (Premium ⭐)"
    if selected_slot_data.get('is_ev'): title_text += " (EV ⚡)"
    ui['action_title_label'].config(text=title_text)

    bookings = get_bookings() 
    active_booking = next((b for b in bookings if b['slot'] == slot_num and b['status'] == 'Active'), None)
    physical_vehicles = selected_slot_data['vehicles']

    if selected_slot_data['capacity_left'] > 0:
        ui['park_action_frame'].pack(fill='x', padx=5, pady=5)
        allowed_types = []
        is_ev = selected_slot_data.get('is_ev', False)
        
        if selected_slot_data['capacity_left'] >= VEHICLE_COSTS['Car']:
            allowed_types.extend(['Car', 'Bike'])
            if is_ev: allowed_types.extend(['EV Car', 'EV Bike'])
            
        else: 
            allowed_types.append('Bike')
            if is_ev: allowed_types.append('EV Bike')
        
        if not is_ev:
            allowed_types = [t for t in allowed_types if 'EV' not in t]
            
        ui['vehicle_type_menu']['values'] = allowed_types
        ui['vehicle_type_var'].set('')

    if physical_vehicles or active_booking:
        ui['remove_action_frame'].pack(fill='x', padx=5, pady=5)
        
        if physical_vehicles:
            if len(physical_vehicles) > 1:
                ui['vehicle_to_remove_label'].grid()
                ui['vehicle_to_remove_menu'].grid()
                ui['vehicle_to_remove_menu']['values'] = physical_vehicles
                ui['vehicle_to_remove_var'].set('')
                
            else:
                ui['vehicle_to_remove_label'].grid_remove()
                ui['vehicle_to_remove_menu'].grid_remove()
                
        else:
            ui['vehicle_to_remove_label'].grid_remove()
            ui['vehicle_to_remove_menu'].grid_remove()

def select_slot(slot_num):
    ui['selected_slot'].set(str(slot_num))
    data = load_data()
    slot_data = data['slots'][str(slot_num)]
    update_action_frames(slot_data)
    update_slots_display()

def update_slots_display():
    for widget in ui['slots_frame'].winfo_children():
        widget.destroy()
        
    data = load_data()
    slots = data['slots']
    bookings = get_bookings() 
    now = datetime.now()
    selected = ui['selected_slot'].get()

    active_reservations = {}
    next_reservations = {}
    
    for booking in bookings:
        if booking['status'] == 'Active':
            active_reservations[booking['slot']] = booking
            
        elif booking['status'] == 'Confirmed':
            start_time = datetime.strptime(booking['start_time'], "%Y-%m-%d %H:%M:%S")
            
            if booking['slot'] not in next_reservations or start_time < datetime.strptime(next_reservations[booking['slot']]['start_time'], "%Y-%m-%d %H:%M:%S"):
                next_reservations[booking['slot']] = booking

    for i in range(1, MAX_SLOTS + 1):
        slot_str = str(i)
        slot_data = slots[slot_str]
        
        vehicle_list = slot_data['vehicles']
        capacity_left = slot_data['capacity_left']
        is_ev = slot_data['is_ev']
        is_premium = slot_data['is_premium']
        color, text, icon = '', '', ''

        if is_premium and is_ev: icon = " ⭐⚡"
        elif is_premium: icon = " ⭐"
        elif is_ev: icon = " ⚡"
        
        if capacity_left < SLOT_CAPACITY:
            if capacity_left == 0:
                color = '#e74c3c' 
                text = f"Slot {i}\nFull{icon}\n{', '.join(vehicle_list)}"
                
            else:
                color = '#e67e22' #
                text = f"Slot {i}\n{len(vehicle_list)} Bike(s){icon}"
        
        elif slot_str in active_reservations:
            color = "#02EAFF" 
            text = f"Slot {i}\nActive{icon}"
        
        elif slot_str in next_reservations:
            res_time = datetime.strptime(next_reservations[slot_str]['start_time'], "%Y-%m-%d %H:%M:%S")
            color = '#00bcd4' 
            text = f"Slot {i}\nReserved{icon}\nFrom {res_time.strftime('%H:%M')}"
        
        else: 
            if is_premium: color = '#f1c40f' 
            elif is_ev: color = '#2ecc71' 
            else: color = '#3498db' 
            text = f"Slot {i}\nAvailable{icon}"
        
        if slot_str == selected:
            color = '#8e44ad'

        slot_btn = tk.Button(ui['slots_frame'], text=text, bg=color, fg='white',
                            font=('Arial', 9, 'bold'), width=12, height=4, justify='center',
                            command=lambda s=i: select_slot(s))
        slot_btn.grid(row=(i - 1) // 10, column=(i - 1) % 10, padx=4, pady=4)

def park_vehicle():
    slot_str = ui['selected_slot'].get()
    
    if not slot_str:
        messagebox.showwarning("Warning", "Please select a slot.")
        return

    vehicle_number = ui['vehicle_entry'].get().strip().upper()
    vehicle_type = ui['vehicle_type_var'].get()
    
    if not vehicle_number or not vehicle_type:
        messagebox.showwarning("Warning", "Please enter vehicle number and type.")
        return

    data = load_data()
    slot_data = data['slots'][slot_str]
    now = datetime.now()
    cost = VEHICLE_COSTS[vehicle_type]
    is_ev_vehicle = 'EV' in vehicle_type
    
    if is_ev_vehicle and not slot_data.get('is_ev'):
        messagebox.showerror("Invalid Slot", "EVs can only park in EV-capable slots (⚡).")
        return

    if vehicle_number in data['vehicles']:
        messagebox.showerror("Error", f"Vehicle {vehicle_number} is already parked.")
        return

    if slot_data['capacity_left'] < cost:
        messagebox.showerror("Capacity Error", f"Not enough space in Slot {slot_str}.")
        return

    bookings = load_bookings()
    capacity_used_by_bookings = 0
    
    for booking in bookings:
        if booking['slot'] == slot_str and booking['status'] == 'Active':
            start_time = datetime.strptime(booking['start_time'], "%Y-%m-%d %H:%M:%S")
            end_time = datetime.strptime(booking['end_time'], "%Y-%m-%d %H:%M:%S")
            
            if start_time <= now < end_time:
                if booking['vehicle'].upper() != vehicle_number: 
                    capacity_used_by_bookings += booking.get('cost', 1)

    if (SLOT_CAPACITY - slot_data['capacity_left']) + capacity_used_by_bookings + cost > SLOT_CAPACITY:
        messagebox.showerror("Reservation Conflict", f"Slot {slot_str} is reserved. Not enough capacity for this {vehicle_type}.")
        return
    
    future_bookings_for_slot = [b for b in bookings if b['slot'] == slot_str and b['status'] == 'Confirmed' and datetime.strptime(b['start_time'], "%Y-%m-%d %H:%M:%S") > now]
    if future_bookings_for_slot:
        next_booking = min(future_bookings_for_slot, key=lambda b: datetime.strptime(b['start_time'], "%Y-%m-%d %H:%M:%S"))
        next_booking_start = datetime.strptime(next_booking['start_time'], "%Y-%m-%d %H:%M:%S")
        time_available = next_booking_start - now
        hours_available = time_available.total_seconds() / 3600
        
        confirmation = messagebox.askyesno(
            "Temporary Parking",
            f"Slot {slot_str} is reserved from {next_booking_start.strftime('%H:%M')}.\n\n"
            f"You can park for a maximum of {hours_available:.1f} hours.\n\n"
            "Do you want to proceed?"
            )
        if not confirmation:
            return 

    slot_data['vehicles'].append(vehicle_number)
    slot_data['capacity_left'] -= cost
    data['vehicles'][vehicle_number] = {
        'slot': slot_str, 
        'type': vehicle_type, 
        'entry_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    save_data(data)
    spoken_vehicle_num = format_vehicle_number_for_speech(vehicle_number)
    speak(f"Vehicle {spoken_vehicle_num} parked in slot {slot_str}.")
    threading.Timer(0.1, lambda: messagebox.showinfo("Success", f"{vehicle_type} {vehicle_number} parked in slot {slot_str}")).start()
    
    ui['vehicle_entry'].delete(0, tk.END)
    ui['selected_slot'].set("")
    update_action_frames(None)
    update_slots_display()
    update_home_stats()

def remove_vehicle():
    slot_str = ui['selected_slot'].get()
    if not slot_str:
        messagebox.showwarning("Warning", "Please select a slot.")
        return
        
    data = load_data()
    slot_data = data['slots'][slot_str]
    vehicles_in_slot = slot_data['vehicles']
    
    vehicle_to_remove = ""
    vehicle_type = ""
    entry_time = None
    cost = 0
    
    if vehicles_in_slot:
        vehicle_to_remove = vehicles_in_slot[0]
        
        if len(vehicles_in_slot) > 1:
            selected_vehicle = ui['vehicle_to_remove_var'].get()
            
            if not selected_vehicle:
                messagebox.showwarning("Selection Needed", "Please select a bike to remove.")
                return
            
            vehicle_to_remove = selected_vehicle

        vehicle_details = data['vehicles'][vehicle_to_remove]
        vehicle_type = vehicle_details['type']
        entry_time = datetime.strptime(vehicle_details['entry_time'], "%Y-%m-%d %H:%M:%S")
        cost = VEHICLE_COSTS[vehicle_type]
        
        exit_time = datetime.now()
        hours = (exit_time - entry_time).total_seconds() / 3600
        billed_hours = max(1, math.ceil(hours))
        rate = HOURLY_RATES[vehicle_type]
        
        if billed_hours <= 6:
            base_charge = rate
            
        elif billed_hours <= 12:
            base_charge = rate + (billed_hours - 6) * (rate * 0.9)
            
        else:
            base_charge = rate + 6 * (rate * 0.9) + (billed_hours - 12) * (rate * 0.8)
            
        overnight_fee = 100 if exit_time.date() > entry_time.date() else 0
        weekend_multiplier = 1.10 if exit_time.weekday() == 5 or 6 else 1.0
        
        premium_fee_applied = 0
        if slot_data.get('is_premium'):
            extra_premium_blocks = int(hours // 6)
            premium_fee_applied = PREMIUM_FEE + (extra_premium_blocks * 50)

        total_charge = (base_charge + overnight_fee + premium_fee_applied) * weekend_multiplier
        penalty_fee = vehicle_details.get('penalty', 0)
        final_total_charge = round(total_charge + penalty_fee, 2)

        log_entry = {
            'vehicle_number': vehicle_to_remove, 'type': vehicle_type, 'slot': slot_str,
            'entry_time': vehicle_details['entry_time'], 
            'exit_time': exit_time.strftime("%Y-%m-%d %H:%M:%S"),
            'duration_hours': round(hours, 2), 
            'charge': final_total_charge, 
            'premium_fee': premium_fee_applied, 
            'overnight_fee': overnight_fee,
            'penalty_fee': penalty_fee, 
            'weekend_multiplier': weekend_multiplier
            }
        save_to_log(log_entry)
        
        slot_data['vehicles'].remove(vehicle_to_remove)
        slot_data['capacity_left'] += cost
        del data['vehicles'][vehicle_to_remove]
        save_data(data)
        
        charge_message = (f"Vehicle: {vehicle_to_remove}\n"
                            f"Duration: {hours:.2f} hours (Billed for {billed_hours}h)\n"
                            f"Base Charge: ₹{base_charge:.2f}\n"
                            f"Overnight Fee: ₹{overnight_fee}\n"
                            f"Premium Slot Fee: ₹{premium_fee_applied:.2f}\n"
                            f"Weekend Multiplier: x{weekend_multiplier:.2f}\n")
        
        if penalty_fee > 0:
            charge_message += f"Overstay Penalty: ₹{penalty_fee:.2f}\n\n"
        
        charge_message += f"Total Charge: ₹{final_total_charge:.2f}"
        spoken_vehicle_num = format_vehicle_number_for_speech(vehicle_to_remove)
        speak(f"Vehicle {spoken_vehicle_num} removed. Total charge is {final_total_charge:.0f} rupees.")
        
        threading.Timer(0.1, lambda: messagebox.showinfo("Success", f"Vehicle removed.\n\n{charge_message}")).start()

    else:
        bookings = load_bookings()
        active_booking = next((b for b in bookings if b['slot'] == slot_str and b['status'] == 'Active'), None)
        
        if not active_booking:
            messagebox.showerror("Error", "Slot is empty.")
            return

        vehicle_to_remove = active_booking['vehicle']
        vehicle_type = active_booking['vehicle_type']
        entry_time = datetime.strptime(active_booking['start_time'], "%Y-%m-%d %H:%M:%S")
        advance_paid = active_booking.get('charge', 0)
        
        exit_time = datetime.now()
        hours = (exit_time - entry_time).total_seconds() / 3600
        billed_hours = max(1, math.ceil(hours))
        rate = HOURLY_RATES[vehicle_type]
        
        if billed_hours <= 6:
            base_charge = rate
            
        elif billed_hours <= 12:
            base_charge = rate + (billed_hours - 6) * (rate * 0.9)
            
        else:
            base_charge = rate + 6 * (rate * 0.9) + (billed_hours - 12) * (rate * 0.8)
            
        overnight_fee = 100 if exit_time.date() > entry_time.date() else 0
        weekend_multiplier = 1.10 if exit_time.weekday() == 5 or 6 else 1.0
        premium_fee_applied = 0
        
        if slot_data.get('is_premium'):
            extra_premium_blocks = int(hours // 6)
            premium_fee_applied = PREMIUM_FEE + (extra_premium_blocks * 50)

        total_charge = round((base_charge + overnight_fee + premium_fee_applied) * weekend_multiplier, 2)
        
        if 'original_charge' in active_booking:
            advance_paid = active_booking['charge'] 
            
        final_due = round(total_charge - advance_paid, 2)
        
        log_entry = {
            'vehicle_number': vehicle_to_remove, 'type': vehicle_type, 'slot': slot_str,
            'entry_time': active_booking['start_time'], 
            'exit_time': exit_time.strftime("%Y-%m-%d %H:%M:%S"),
            'duration_hours': round(hours, 2), 
            'charge': total_charge, 
            'premium_fee': premium_fee_applied, 'overnight_fee': overnight_fee,
            'weekend_multiplier': weekend_multiplier
            }
        
        save_to_log(log_entry)
        active_booking['status'] = 'Completed'
        save_bookings(bookings)
        
        charge_message = (f"Booked Vehicle: {vehicle_to_remove}\n"
                            f"Duration: {hours:.2f} hours (Billed for {billed_hours}h)\n"
                            f"Total Charge: ₹{total_charge:.2f}\n"
                            f"Advance Paid: -₹{advance_paid:.2f}\n\n"
                            f"Final Amount Due: ₹{final_due:.2f}")
        
        spoken_vehicle_num = format_vehicle_number_for_speech(vehicle_to_remove)
        speak(f"Booking for {spoken_vehicle_num} completed. Final amount due is {final_due:.0f} rupees.")
        threading.Timer(0.1, lambda: messagebox.showinfo("Booking Completed", charge_message)).start()
    
    ui['selected_slot'].set("")
    update_action_frames(None)
    update_slots_display()
    update_home_stats()
    update_booking_slot_options()
    refresh_bookings() 

def refresh_bookings():
    for item in ui['bookings_tree'].get_children():
        ui['bookings_tree'].delete(item)
        
    filter_status = ui['filter_var'].get()
    bookings = get_bookings()
    
    for booking in bookings:
        if filter_status == "All" or booking['status'] == filter_status:
            start = datetime.strptime(booking['start_time'], "%Y-%m-%d %H:%M:%S")
            end = datetime.strptime(booking['end_time'], '%Y-%m-%d %H:%M:%S')
            date_str = start.strftime("%Y-%m-%d")
            time_str = f"{start.strftime('%H:%M')} to {end.strftime('%H:%M')}"
            fee_str = f"₹{booking.get('charge', 0):.2f}"
            
            slot_display = booking['slot']
            original_slot = booking.get('original_slot')

            ui['bookings_tree'].insert("", "end", values=(
                booking['id'], booking['vehicle'], booking.get('vehicle_type', 'N/A'), 
                booking['slot'], date_str, time_str, fee_str, booking['status'],
                original_slot if original_slot else "-" 
            ))

def handle_cancel_booking():
    selected = ui['bookings_tree'].selection()
    
    if not selected:
        messagebox.showwarning("Warning", "Please select a booking to cancel")
        return
        
    booking_id = int(ui['bookings_tree'].item(selected[0], 'values')[0])
    booking_status = ui['bookings_tree'].item(selected[0], 'values')[7]
    
    if booking_status != 'Confirmed':
        messagebox.showerror("Error", f"Cannot cancel a booking that is '{booking_status}'.")
        return

    success, message = cancel_booking_by_id(booking_id)
    
    if success:
        speak("Booking cancelled.") 
        threading.Timer(0.1, lambda: messagebox.showinfo("Success", message)).start()
        refresh_bookings()
        update_slots_display()
        
    else:
        messagebox.showerror("Error", message)

def handle_activate_booking():
    selected = ui['bookings_tree'].selection()
    
    if not selected:
        messagebox.showwarning("Warning", "Please select a booking to activate.")
        return
        
    item = ui['bookings_tree'].item(selected[0], 'values')
    booking_id = int(item[0])
    booking_status = item[7]
    
    if booking_status == 'Active':
        messagebox.showinfo("Info", "This booking is already active.")
        return
    
    if booking_status == 'Completed':
        messagebox.showerror("Error", "This booking is already completed.")
        return
    
    if booking_status != 'Confirmed':
        messagebox.showerror("Error", f"Cannot activate a booking with status '{booking_status}'.")
        return
    
    bookings_data = load_bookings()
    data = load_data()
    target_booking = None
    
    for booking in bookings_data:
        if booking['id'] == booking_id:
            target_booking = booking
            break
    
    if not target_booking:
        messagebox.showerror("Error", "Booking not found in database.")
        return
    
    original_slot_str = target_booking['slot']
    slot_data = data['slots'][original_slot_str]
    cost = target_booking.get('cost', VEHICLE_COSTS.get(target_booking['vehicle_type'], 1))
    
    if slot_data['capacity_left'] < cost:
        offending_vehicles = slot_data['vehicles']
        penalty_applied_to = []
        for vehicle_num in offending_vehicles:
            if vehicle_num in data['vehicles']:
                data['vehicles'][vehicle_num]['penalty'] = data['vehicles'][vehicle_num].get('penalty', 0) + 100
                penalty_applied_to.append(vehicle_num)
        
        if penalty_applied_to:
            save_data(data) 
            messagebox.showwarning("Penalty Applied", 
                f"Vehicle(s) {', '.join(penalty_applied_to)} are overstaying in reserved slot {original_slot_str}.\n\n"
                "A ₹100 penalty has been added to each vehicle's bill.")
        
        new_slot_id = None
        is_ev_vehicle = 'EV' in target_booking['vehicle_type']
        required_cost = target_booking['cost']
        start_time_obj = datetime.strptime(target_booking['start_time'], "%Y-%m-%d %H:%M:%S")
        end_time_obj = datetime.strptime(target_booking['end_time'], "%Y-%m-%d %H:%M:%S")
        
        candidate_slots = []
        for slot_id, s_data in data['slots'].items():
            if s_data['capacity_left'] >= required_cost:
                if is_ev_vehicle and not s_data['is_ev']:
                    continue 
                
                available, _ = is_slot_available(slot_id, target_booking['vehicle_type'], start_time_obj, end_time_obj)
                if available:
                    candidate_slots.append((slot_id, s_data))

        if candidate_slots:
            premium_candidates = [s for s in candidate_slots if s[1]['is_premium']]
            if premium_candidates:
                new_slot_id = premium_candidates[0][0]
                
            else:
                new_slot_id = candidate_slots[0][0]
        
        if new_slot_id:
            original_charge = target_booking['charge']
            discounted_charge = round(original_charge * 0.90, 2)
            target_booking['charge'] = discounted_charge
            target_booking['original_charge'] = original_charge
            
            target_booking['slot'] = new_slot_id
            target_booking['original_slot'] = original_slot_str
            target_booking['status'] = 'Active'
            
            save_bookings(bookings_data)
            
            is_premium_upgrade = data['slots'][new_slot_id]['is_premium']
            
            speak_msg = (f"Sorry for the inconvenience. Your slot {original_slot_str} was occupied. "
                        f"You have been {'upgraded to premium' if is_premium_upgrade else 'moved to'} slot {new_slot_id}. "
                        "An additional 10 percent discount has been applied.")
            
            popup_msg = (f"Sorry for the inconvenience!\n\n"
                        f"Your original slot {original_slot_str} was occupied. "
                        f"You have been moved to {'Premium' if is_premium_upgrade else ''} Slot {new_slot_id}.\n\n"
                        f"- Original Fee: ₹{original_charge:.2f}\n"
                        f"- New Fee (10% off): ₹{discounted_charge:.2f}\n\n"
                        "This booking is now active.")
            
            speak(speak_msg)
            threading.Timer(0.1, lambda: messagebox.showinfo("Booking Upgraded!", popup_msg)).start()
            
        else:
            speak(f"We are extremely sorry. Your booked slot {original_slot_str} is occupied, and we could not find any other free slot. Please contact the manager.")
            messagebox.showerror("System Failure", 
                f"Your booked slot {original_slot_str} is occupied.\n\n"
                f"A penalty was applied to the offending vehicle(s), but we could NOT find any other empty slot for you.\n\n"
                "Please contact the manager for an immediate resolution.")
    
    else:
        start = datetime.strptime(target_booking['start_time'], "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        target_booking['status'] = 'Active'
        
        if now < start: 
            target_booking['start_time'] = now.strftime("%Y-%m-%d %H:%M:%S")
            speak(f"Early check in for slot {original_slot_str} activated.")
            threading.Timer(0.1, lambda: messagebox.showinfo("Success", 
                                    "Early check-in successful. Booking is now active.")).start()
        
        else:
            speak(f"Booking for slot {original_slot_str} activated.")
            threading.Timer(0.1, lambda: messagebox.showinfo("Success", "Booking is now active.")).start()
        
        save_bookings(bookings_data)
    
    refresh_bookings()
    update_slots_display()

def _validate_and_get_times():
    try:
        year = int(ui['year_var'].get())
        month = int(ui['month_var'].get())
        day = int(ui['day_var'].get())
        
        try:
            date_obj = datetime(year, month, day)
            
        except ValueError:
            messagebox.showerror("Error", f"Invalid date selected: {day}/{month}/{year} does not exist.")
            return None, None
        
        start_time = datetime.strptime(f"{year}-{month:02d}-{day:02d} {ui['start_hour_var'].get()}:{ui['start_min_var'].get()}", "%Y-%m-%d %H:%M")
        end_time = datetime.strptime(f"{year}-{month:02d}-{day:02d} {ui['end_hour_var'].get()}:{ui['end_min_var'].get()}", "%Y-%m-%d %H:%M")

        if start_time < datetime.now() - timedelta(minutes=10):
            messagebox.showerror("Error", "Cannot book for a time in the past.")
            return None, None

        if end_time <= start_time:
            messagebox.showerror("Error", "End time must be after start time")
            return None, None
        
        return start_time, end_time

    except (ValueError, TypeError):
        messagebox.showerror("Error", f"Invalid date or time input.")
        return None, None

def check_availability():
    slot = ui['booking_slot_var'].get()
    vehicle_type = ui['booking_vehicle_type_var'].get()
    
    if not slot or not vehicle_type:
        messagebox.showwarning("Warning", "Please select a vehicle type and slot")
        return
    
    start_time, end_time = _validate_and_get_times()
    if not start_time:
        return

    available, message = is_slot_available(slot, vehicle_type, start_time, end_time)
    
    if available:
        total, base, premium = calculate_booking_fee(slot, vehicle_type, start_time, end_time)
        fee_message = (f"Base Charge: ₹{base:.2f}\n"
                        f"Premium Slot Fee: ₹{premium:.2f}\n\n"
                        f"Total Advance: ₹{total:.2f}")
        
        speak(f"Slot {slot} is available. The total advance is {total:.0f} rupees.")
        threading.Timer(0.1, lambda: messagebox.showinfo("Available", f"Slot {slot} is available!\n\n{fee_message}")).start() 
    
    else:
        speak(message)
        threading.Timer(0.1, lambda: messagebox.showwarning("Not Available", message)).start() 

def make_booking():
    vehicle = ui['booking_vehicle_entry'].get().strip().upper()
    vehicle_type = ui['booking_vehicle_type_var'].get()
    slot = ui['booking_slot_var'].get()
    
    if not vehicle or not slot or not vehicle_type:
        messagebox.showerror("Error", "Please fill all required fields")
        return
        
    start_time, end_time = _validate_and_get_times()
    if not start_time:
        return
        
    available, message = is_slot_available(slot, vehicle_type, start_time, end_time)
    
    if not available:
        speak(message)
        threading.Timer(0.1, lambda: messagebox.showerror("Booking Error", message)).start()
        update_booking_slot_options()
        return

    total, base, premium = calculate_booking_fee(slot, vehicle_type, start_time, end_time)
    
    if total <= 0:
        messagebox.showerror("Error", "Invalid booking duration or type.")
        return

    fee_message = (f"Vehicle: {vehicle}\n"
                    f"Slot: {slot} ({'Premium' if premium > 0 else 'Standard'})\n"
                    f"From: {start_time.strftime('%Y-%m-%d %H:%M')}\n"
                    f"To:   {end_time.strftime('%Y-%m-%d %H:%M')}\n\n"
                    f"Base Charge: ₹{base:.2f}\n"
                    f"Premium Slot Fee: ₹{premium:.2f}\n\n"
                    f"Total Advance: ₹{total:.2f}")

    speak(f"The total advance fee for slot {slot} is {total:.0f} rupees. Please pay now to confirm your booking.")
    confirmation = messagebox.askyesno("Confirm Payment", 
        f"Please confirm your booking details:\n\n{fee_message}\n\nPay now to confirm this booking?")
    
    if confirmation:
        success, message = add_booking(vehicle, vehicle_type, slot, start_time, end_time, total, premium)
        
        if success:
            speak(f"Booking confirmed for slot {slot}.")
            threading.Timer(0.1, lambda: messagebox.showinfo("Success", message)).start()
            
            refresh_bookings()
            update_slots_display() 
            ui['booking_vehicle_entry'].delete(0, tk.END)
            update_booking_slot_options()
            
        else:
            messagebox.showerror("Error", message)
            
    else:
        speak("Booking cancelled.")
        threading.Timer(0.1, lambda: messagebox.showinfo("Booking Cancelled", "Booking was not confirmed.")).start() 

def update_booking_slot_options(event=None):
    try:
        vehicle_type = ui['booking_vehicle_type_var'].get()
        
        if not vehicle_type:
            ui['booking_slot_menu']['values'] = []
            ui['booking_slot_var'].set('')
            return

        is_ev_vehicle = 'EV' in vehicle_type
        cost = VEHICLE_COSTS[vehicle_type]
        compatible_slots = []
        data = load_data() 
        
        for i in range(1, MAX_SLOTS + 1):
            slot_str = str(i)
            slot_data = data['slots'][slot_str]
            
            if slot_data['capacity_left'] < cost:
                continue 
            is_slot_ev = slot_data['is_ev']
            
            if is_ev_vehicle and is_slot_ev:
                compatible_slots.append(slot_str)
                
            elif not is_ev_vehicle: 
                compatible_slots.append(slot_str)
        
        ui['booking_slot_menu']['values'] = compatible_slots
        ui['booking_slot_var'].set('') 
    
    except KeyError:
        pass

def create_sidebar(parent):
    sidebar = ttk.Frame(parent, width=200)
    sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
    ttk.Label(sidebar, text="Parking System", style='Header.TLabel').pack(pady=20)
    
    buttons = [("Home", show_home_tab), 
                ("Dashboard", show_dashboard_tab), 
                ("Parking", show_parking_tab),
                ("Bookings", show_bookings_tab)]
    
    for text, command in buttons:
        btn = ttk.Button(sidebar, text=text, command=command, width=15)
        btn.pack(pady=5, ipady=5)

def create_home_tab(parent):
    ui['home_tab'] = ttk.Frame(parent)
    ttk.Label(ui['home_tab'], text="Real-Time Status", style='Header.TLabel').pack(pady=50)
    stats_frame = ttk.Frame(ui['home_tab'])
    stats_frame.pack(pady=20)
    ui['stats_labels'] = {}
    stats = [("Total Slots", "total_slots"), ("Slots with Vehicles", "occupied_slots"),
        ("Empty Slots", "available_slots"), ("Currently Parked Vehicles", "vehicles_parked")]
    
    for i, (text, key) in enumerate(stats):
        frame = ttk.Frame(stats_frame)
        frame.grid(row=i//2, column=i%2, padx=20, pady=10)
        ttk.Label(frame, text=text, font=('Arial', 12)).pack()
        ui['stats_labels'][key] = ttk.Label(frame, font=('Arial', 24, 'bold'))
        ui['stats_labels'][key].pack()

def create_dashboard_tab(parent):
    ui['dashboard_tab'] = ttk.Frame(parent)
    ui['dashboard_title_label'] = ttk.Label(ui['dashboard_tab'], text="Today's Analytics", style='Header.TLabel')
    ui['dashboard_title_label'].pack(pady=(20, 10)) 
    
    date_filter_frame = ttk.Frame(ui['dashboard_tab'])
    date_filter_frame.pack(pady=5)
    ttk.Label(date_filter_frame, text="Select Date:", font=('Arial', 11)).pack(side=tk.LEFT, padx=5)
    
    ui['analytics_date_var'] = tk.StringVar()
    ui['analytics_date_combo'] = ttk.Combobox(date_filter_frame, textvariable=ui['analytics_date_var'], 
                                            state="readonly", width=18, font=('Arial', 10))
    ui['analytics_date_combo'].pack(side=tk.LEFT)
    ui['analytics_date_combo'].bind("<<ComboboxSelected>>", on_analytics_date_selected)
    
    dash_frame = ttk.Frame(ui['dashboard_tab'])
    dash_frame.pack(pady=15)
    ui['dashboard_labels'] = {}
    
    dash_stats = [
        ("Total Revenue", "revenue"), ("Premium Revenue", "premium_revenue"),
        ("Penalty Revenue", "penalty_revenue"), # <-- NEW CARD
        ("Vehicles Today", "total_vehicles"), ("Avg. Park Time", "avg_duration"), 
        ("Cars (Non-EV)", "cars"), ("EV Cars", "ev_cars"),
        ("Bikes", "bike"), ("EV Bikes", "ev_bike")
        ]
    
    items_per_row = 3
    for i, (text, key) in enumerate(dash_stats):
        labelframe = ttk.LabelFrame(dash_frame, text=text)
        labelframe.grid(row=i // items_per_row, column=i % items_per_row, padx=10, pady=10, sticky="nsew")
        card_frame = ttk.Frame(labelframe, style='Card.TFrame')
        card_frame.pack(fill="both", expand=True, padx=1, pady=1)
        ui['dashboard_labels'][key] = ttk.Label(card_frame, text="0", font=('Arial', 20, 'bold'),
                                        anchor='center', style='Card.TLabel')
        ui['dashboard_labels'][key].pack(pady=10, padx=15)

    ttk.Button(dash_frame, text="Refresh Stats", command=refresh_dashboard_view).grid(row=(len(dash_stats)//items_per_row)+1, 
                                        column=0, columnspan=items_per_row, pady=20)

def create_parking_tab(parent):
    ui['parking_tab'] = ttk.Frame(parent)
    main_frame = ttk.Frame(ui['parking_tab'])
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    left_frame = ttk.Frame(main_frame)
    left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    ttk.Label(left_frame, text="Parking Grid", style='Header.TLabel').pack(pady=5)
    ui['slots_frame'] = ttk.Frame(left_frame)
    ui['slots_frame'].pack(pady=10)

    action_panel = ttk.Frame(main_frame, width=350)
    action_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(20, 0))
    ui['action_title_label'] = ttk.Label(action_panel, text="Select a Slot to Begin", style='Header.TLabel')
    ui['action_title_label'].pack(pady=10)

    ui['park_action_frame'] = ttk.LabelFrame(action_panel, text="Park a Vehicle")
    ttk.Label(ui['park_action_frame'], text="Vehicle Number:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
    ui['vehicle_entry'] = ttk.Entry(ui['park_action_frame'], font=('Arial', 12))
    ui['vehicle_entry'].grid(row=0, column=1, padx=5, pady=5)
    ttk.Label(ui['park_action_frame'], text="Vehicle Type:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
    ui['vehicle_type_var'] = tk.StringVar()
    ui['vehicle_type_menu'] = ttk.Combobox(ui['park_action_frame'], 
                                textvariable=ui['vehicle_type_var'], state="readonly", width=18)
    ui['vehicle_type_menu'].grid(row=1, column=1, padx=5, pady=5)
    ttk.Button(ui['park_action_frame'], text="Confirm Parking", command=park_vehicle).grid(row=2, column=0, columnspan=2, pady=10)

    ui['remove_action_frame'] = ttk.LabelFrame(action_panel, text="Remove a Vehicle")
    ui['vehicle_to_remove_label'] = ttk.Label(ui['remove_action_frame'], text="Select Vehicle:")
    ui['vehicle_to_remove_label'].grid(row=0, column=0, padx=5, pady=5, sticky="w")
    ui['vehicle_to_remove_var'] = tk.StringVar()
    ui['vehicle_to_remove_menu'] = ttk.Combobox(ui['remove_action_frame'], 
                                    textvariable=ui['vehicle_to_remove_var'], state="readonly", width=18)
    ui['vehicle_to_remove_menu'].grid(row=0, column=1, padx=5, pady=5)
    ttk.Button(ui['remove_action_frame'], text="Confirm Removal", command=remove_vehicle, 
                style='Remove.TButton').grid(row=1, column=0, columnspan=2, pady=10)

def create_bookings_tab(parent):
    frame = ttk.Frame(parent)
    notebook = ttk.Notebook(frame)
    notebook.pack(fill='both', expand=True, padx=10, pady=10)
    
    new_booking_frame = ttk.Frame(notebook) 
    notebook.add(new_booking_frame, text="New Booking")
    setup_new_booking_tab(new_booking_frame)
    
    view_frame = ttk.Frame(notebook) 
    notebook.add(view_frame, text="View Bookings")
    setup_view_bookings_tab(view_frame)
    ui['bookings_tab'] = frame

def setup_new_booking_tab(parent):
    header = ttk.Label(parent, text="Pre-Book Your Parking Slot", style='Header.TLabel')
    header.pack(pady=(10, 20))
    form_frame = ttk.Frame(parent)
    form_frame.pack(fill="x", padx=50, pady=10)

    ttk.Label(form_frame, text="Vehicle Number:", font=("Arial", 12)).grid(row=0, column=0, 
                                                    sticky="e", padx=5, pady=10)
    ui['booking_vehicle_entry'] = ttk.Entry(form_frame, font=("Arial", 12))
    ui['booking_vehicle_entry'].grid(row=0, column=1, sticky="w", padx=5, pady=10)
    
    ttk.Label(form_frame, text="Vehicle Type:", font=("Arial", 12)).grid(row=1, column=0, 
                                                    sticky="e", padx=5, pady=10)
    ui['booking_vehicle_type_var'] = tk.StringVar()
    ui['booking_vehicle_type_menu'] = ttk.Combobox(form_frame, textvariable=ui['booking_vehicle_type_var'], 
                                    values=list(VEHICLE_COSTS.keys()), font=("Arial", 12), state="readonly")
    ui['booking_vehicle_type_menu'].grid(row=1, column=1, sticky="w", padx=5, pady=10)
    ui['booking_vehicle_type_menu'].bind("<<ComboboxSelected>>", update_booking_slot_options)

    ttk.Label(form_frame, text="Parking Slot:", font=("Arial", 12)).grid(row=2, column=0, sticky="e", padx=5, pady=10)
    ui['booking_slot_var'] = tk.StringVar()
    ui['booking_slot_menu'] = ttk.Combobox(form_frame, textvariable=ui['booking_slot_var'], 
                                            values=[], font=("Arial", 12), state="readonly")
    ui['booking_slot_menu'].grid(row=2, column=1, sticky="w", padx=5, pady=10)
    
    ttk.Label(form_frame, text="Booking Date:", font=("Arial", 12)).grid(row=3, column=0, sticky="e", padx=5, pady=10)
    date_frame = ttk.Frame(form_frame)
    date_frame.grid(row=3, column=1, sticky="w")
    now = datetime.now()
    ui['year_var'] = tk.StringVar(value=str(now.year))
    ttk.Combobox(date_frame, textvariable=ui['year_var'], width=5, values=[str(y) for y in range(now.year, now.year + 2)]).pack(side="left")
    ui['month_var'] = tk.StringVar(value=f"{now.month:02d}")
    ttk.Combobox(date_frame, textvariable=ui['month_var'], width=3, values=[f"{m:02d}" for m in range(1, 13)]).pack(side="left", padx=5)
    ui['day_var'] = tk.StringVar(value=f"{now.day:02d}")
    ttk.Combobox(date_frame, textvariable=ui['day_var'], width=3, values=[f"{d:02d}" for d in range(1, 32)]).pack(side="left")

    time_frame = ttk.Frame(form_frame)
    time_frame.grid(row=4, column=0, columnspan=2, pady=10)
    ttk.Label(time_frame, text="From:", font=("Arial", 12)).pack(side="left", padx=5)
    ui['start_hour_var'] = tk.StringVar(value=f"{(now.hour + 1) % 24:02d}")
    ttk.Combobox(time_frame, textvariable=ui['start_hour_var'], width=3, values=[f"{h:02d}" for h in range(0, 24)]).pack(side="left")
    ui['start_min_var'] = tk.StringVar(value="00")
    ttk.Combobox(time_frame, textvariable=ui['start_min_var'], width=3, values=["00", "15", "30", "45"]).pack(side="left", padx=5)
    ttk.Label(time_frame, text="To:", font=("Arial", 12)).pack(side="left", padx=10)
    ui['end_hour_var'] = tk.StringVar(value=f"{(now.hour + 2) % 24:02d}")
    ttk.Combobox(time_frame, textvariable=ui['end_hour_var'], width=3, values=[f"{h:02d}" for h in range(0, 24)]).pack(side="left")
    ui['end_min_var'] = tk.StringVar(value="00")
    ttk.Combobox(time_frame, textvariable=ui['end_min_var'], width=3, values=["00", "15", "30", "45"]).pack(side="left", padx=5)

    btn_frame = ttk.Frame(parent)
    btn_frame.pack(pady=20)
    ttk.Button(btn_frame, text="Check Availability", command=check_availability).pack(side="left", padx=10)
    ttk.Button(btn_frame, text="Calculate Fare & Book", command=make_booking).pack(side="left", padx=10)

def setup_view_bookings_tab(parent):
    header = ttk.Label(parent, text="Your Bookings", style='Header.TLabel')
    header.pack(pady=(10, 20))

    filter_frame = ttk.Frame(parent)
    filter_frame.pack(fill="x", padx=20, pady=10)
    ttk.Label(filter_frame, text="Filter by:", font=("Arial", 12)).pack(side="left", padx=5)
    ui['filter_var'] = tk.StringVar(value="All")
    ttk.Combobox(filter_frame, textvariable=ui['filter_var'], 
                values=["All", "Confirmed", "Active", "Completed"], 
                state="readonly", width=12).pack(side="left", padx=5)
    ttk.Button(filter_frame, text="Apply", command=refresh_bookings).pack(side="left", padx=10)
    
    tree_frame = ttk.Frame(parent)
    tree_frame.pack(fill='both', expand=True, padx=20, pady=10)
    
    columns = ("ID", "Vehicle", "Type", "Slot", "Date", "Time", "Fee", "Status", "Original Slot") # <-- NEW COLUMN
    ui['bookings_tree'] = ttk.Treeview(tree_frame, columns=columns, show="headings", height=12)
    for col in columns:
        ui['bookings_tree'].heading(col, text=col)
        
    ui['bookings_tree'].column("ID", width=40, anchor="center")
    ui['bookings_tree'].column("Vehicle", width=100, anchor="center")
    ui['bookings_tree'].column("Type", width=100, anchor="center")
    ui['bookings_tree'].column("Slot", width=40, anchor="center")
    ui['bookings_tree'].column("Date", width=100, anchor="center")
    ui['bookings_tree'].column("Time", width=120, anchor="center")
    ui['bookings_tree'].column("Fee", width=80, anchor="e") 
    ui['bookings_tree'].column("Status", width=80, anchor="center")
    ui['bookings_tree'].column("Original Slot", width=80, anchor="center") # <-- NEW COLUMN
    
    scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=ui['bookings_tree'].yview)
    ui['bookings_tree'].configure(yscrollcommand=scrollbar.set)
    ui['bookings_tree'].pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    btn_frame = ttk.Frame(parent)
    btn_frame.pack(fill="x", pady=10, padx=20)
    ttk.Button(btn_frame, text="Refresh", command=refresh_bookings).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Activate Booking", command=handle_activate_booking).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Cancel Booking", command=handle_cancel_booking, 
                style='Remove.TButton').pack(side="left", padx=5)

if __name__ == "__main__":
    root = tk.Tk()
    ui = {}
    
    initialize_data_files()
    root.title("Advanced Parking Management System")
    root.state('zoomed')
    ui['selected_slot'] = tk.StringVar()

    style = ttk.Style()
    style.configure('TFrame', background='#ecf0f1')
    style.configure('TButton', font=('Arial', 11), padding=5)
    style.configure('TLabel', font=('Arial', 11), background='#ecf0f1')
    style.configure('Header.TLabel', font=('Arial', 16, 'bold'), foreground='#2c3e50', 
                    background='#ecf0f1')
    style.configure('TLabelFrame.Label', font=('Arial', 12, 'bold'), foreground='#34495e')
    style.configure('Card.TFrame', background='white', relief='solid', borderwidth=1)
    style.configure('Card.TLabel', font=('Arial', 20, 'bold'), background='white')
    style.configure('Remove.TButton', font=('Arial', 11, 'bold'), foreground='black', 
                    background="#f0f0f0", padding=5)
    style.configure("TNotebook.Tab", font=('Arial', 12, 'bold'), padding=[10, 5])
    style.configure("Treeview.Heading", font=('Arial', 12, 'bold'))
    style.configure("Treeview", font=('Arial', 10), rowheight=25)
    
    main_container = ttk.Frame(root)
    main_container.pack(fill=tk.BOTH, expand=True)
    create_sidebar(main_container) 
    main_content_frame = ttk.Frame(main_container)
    main_content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
    
    create_home_tab(main_content_frame)
    create_dashboard_tab(main_content_frame)
    create_parking_tab(main_content_frame)
    create_bookings_tab(main_content_frame)
    
    show_home_tab() 
    root.mainloop()
