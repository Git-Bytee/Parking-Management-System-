import threading
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import messagebox, ttk

from data import DataService, PREMIUM_SLOTS, SLOT_CAPACITY, VEHICLE_COSTS
from booking import BookingService
from analytics import AnalyticsService

class ParkingApp:
    """Tkinter application for the parking management system."""

    def __init__(self, root):
        self.root = root
        self.ui = {}
        self.data_service = DataService()
        self.booking_service = BookingService(self.data_service)
        self.analytics_service = AnalyticsService(self.data_service)

        self.ui['selected_slot'] = tk.StringVar()
        self.data_service.initialize_data_files()
        self._configure_style()
        self._build_ui()
        self.show_home_tab()

    def _configure_style(self):
        style = ttk.Style()
        style.configure('TFrame', background='#ecf0f1')
        style.configure('TButton', font=('Arial', 11), padding=5)
        style.configure('TLabel', font=('Arial', 11), background='#ecf0f1')
        style.configure('Header.TLabel', font=('Arial', 16, 'bold'), foreground='#2c3e50', background='#ecf0f1')
        style.configure('TLabelFrame.Label', font=('Arial', 12, 'bold'), foreground='#34495e')
        style.configure('Card.TFrame', background='white', relief='solid', borderwidth=1)
        style.configure('Card.TLabel', font=('Arial', 20, 'bold'), background='white')
        style.configure('Remove.TButton', font=('Arial', 11, 'bold'), foreground='black', background='#f0f0f0', padding=5)
        style.configure('TNotebook.Tab', font=('Arial', 12, 'bold'), padding=[10, 5])
        style.configure('Treeview.Heading', font=('Arial', 12, 'bold'))
        style.configure('Treeview', font=('Arial', 10), rowheight=25)

    def _build_ui(self):
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)
        self._create_sidebar(main_container)

        main_content_frame = ttk.Frame(main_container)
        main_content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._create_home_tab(main_content_frame)
        self._create_dashboard_tab(main_content_frame)
        self._create_parking_tab(main_content_frame)
        self._create_bookings_tab(main_content_frame)

    def _create_sidebar(self, parent):
        sidebar = ttk.Frame(parent, width=200)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        ttk.Label(sidebar, text='Parking System', style='Header.TLabel').pack(pady=20)

        buttons = [
            ('Home', self.show_home_tab),
            ('Dashboard', self.show_dashboard_tab),
            ('Parking', self.show_parking_tab),
            ('Bookings', self.show_bookings_tab)
        ]

        for text, command in buttons:
            btn = ttk.Button(sidebar, text=text, command=command, width=15)
            btn.pack(pady=5, ipady=5)

    def _create_home_tab(self, parent):
        self.ui['home_tab'] = ttk.Frame(parent)
        ttk.Label(self.ui['home_tab'], text='Real-Time Status', style='Header.TLabel').pack(pady=50)
        stats_frame = ttk.Frame(self.ui['home_tab'])
        stats_frame.pack(pady=20)

        self.ui['stats_labels'] = {}
        stats = [
            ('Total Slots', 'total_slots'),
            ('Slots with Vehicles', 'occupied_slots'),
            ('Empty Slots', 'available_slots'),
            ('Currently Parked Vehicles', 'vehicles_parked')
        ]

        for i, (text, key) in enumerate(stats):
            frame = ttk.Frame(stats_frame)
            frame.grid(row=i // 2, column=i % 2, padx=20, pady=10)
            ttk.Label(frame, text=text, font=('Arial', 12)).pack()
            self.ui['stats_labels'][key] = ttk.Label(frame, font=('Arial', 24, 'bold'))
            self.ui['stats_labels'][key].pack()

    def _create_dashboard_tab(self, parent):
        self.ui['dashboard_tab'] = ttk.Frame(parent)
        self.ui['dashboard_title_label'] = ttk.Label(self.ui['dashboard_tab'], text="Today's Analytics", style='Header.TLabel')
        self.ui['dashboard_title_label'].pack(pady=(20, 10))

        date_filter_frame = ttk.Frame(self.ui['dashboard_tab'])
        date_filter_frame.pack(pady=5)
        ttk.Label(date_filter_frame, text='Select Date:', font=('Arial', 11)).pack(side=tk.LEFT, padx=5)

        self.ui['analytics_date_var'] = tk.StringVar()
        self.ui['analytics_date_combo'] = ttk.Combobox(
            date_filter_frame,
            textvariable=self.ui['analytics_date_var'],
            state='readonly',
            width=18,
            font=('Arial', 10)
        )
        self.ui['analytics_date_combo'].pack(side=tk.LEFT)
        self.ui['analytics_date_combo'].bind('<<ComboboxSelected>>', self.on_analytics_date_selected)

        dash_frame = ttk.Frame(self.ui['dashboard_tab'])
        dash_frame.pack(pady=15)
        self.ui['dashboard_labels'] = {}

        dash_stats = [
            ('Total Revenue', 'revenue'),
            ('Premium Revenue', 'premium_revenue'),
            ('Penalty Revenue', 'penalty_revenue'),
            ('Vehicles Today', 'total_vehicles'),
            ('Avg. Park Time', 'avg_duration'),
            ('Cars (Non-EV)', 'cars'),
            ('EV Cars', 'ev_cars'),
            ('Bikes', 'bike'),
            ('EV Bikes', 'ev_bike')
        ]

        items_per_row = 3
        for i, (text, key) in enumerate(dash_stats):
            labelframe = ttk.LabelFrame(dash_frame, text=text)
            labelframe.grid(row=i // items_per_row, column=i % items_per_row, padx=10, pady=10, sticky='nsew')
            card_frame = ttk.Frame(labelframe, style='Card.TFrame')
            card_frame.pack(fill='both', expand=True, padx=1, pady=1)
            self.ui['dashboard_labels'][key] = ttk.Label(card_frame, text='0', font=('Arial', 20, 'bold'), anchor='center', style='Card.TLabel')
            self.ui['dashboard_labels'][key].pack(pady=10, padx=15)

        ttk.Button(dash_frame, text='Refresh Stats', command=self.refresh_dashboard_view).grid(
            row=(len(dash_stats) // items_per_row) + 1,
            column=0,
            columnspan=items_per_row,
            pady=20
        )

    def _create_parking_tab(self, parent):
        self.ui['parking_tab'] = ttk.Frame(parent)
        main_frame = ttk.Frame(self.ui['parking_tab'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Label(left_frame, text='Parking Grid', style='Header.TLabel').pack(pady=5)
        self.ui['slots_frame'] = ttk.Frame(left_frame)
        self.ui['slots_frame'].pack(pady=10)

        action_panel = ttk.Frame(main_frame, width=350)
        action_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(20, 0))
        self.ui['action_title_label'] = ttk.Label(action_panel, text='Select a Slot to Begin', style='Header.TLabel')
        self.ui['action_title_label'].pack(pady=10)

        self.ui['park_action_frame'] = ttk.LabelFrame(action_panel, text='Park a Vehicle')
        ttk.Label(self.ui['park_action_frame'], text='Vehicle Number:').grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.ui['vehicle_entry'] = ttk.Entry(self.ui['park_action_frame'], font=('Arial', 12))
        self.ui['vehicle_entry'].grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(self.ui['park_action_frame'], text='Vehicle Type:').grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.ui['vehicle_type_var'] = tk.StringVar()
        self.ui['vehicle_type_menu'] = ttk.Combobox(self.ui['park_action_frame'], textvariable=self.ui['vehicle_type_var'], state='readonly', width=18)
        self.ui['vehicle_type_menu'].grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(self.ui['park_action_frame'], text='Confirm Parking', command=self.park_vehicle).grid(row=2, column=0, columnspan=2, pady=10)

        self.ui['remove_action_frame'] = ttk.LabelFrame(action_panel, text='Remove a Vehicle')
        self.ui['vehicle_to_remove_label'] = ttk.Label(self.ui['remove_action_frame'], text='Select Vehicle:')
        self.ui['vehicle_to_remove_label'].grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.ui['vehicle_to_remove_var'] = tk.StringVar()
        self.ui['vehicle_to_remove_menu'] = ttk.Combobox(self.ui['remove_action_frame'], textvariable=self.ui['vehicle_to_remove_var'], state='readonly', width=18)
        self.ui['vehicle_to_remove_menu'].grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(self.ui['remove_action_frame'], text='Confirm Removal', command=self.remove_vehicle, style='Remove.TButton').grid(row=1, column=0, columnspan=2, pady=10)

    def _create_bookings_tab(self, parent):
        self.ui['bookings_tab'] = ttk.Frame(parent)
        notebook = ttk.Notebook(self.ui['bookings_tab'])
        notebook.pack(fill='both', expand=True, padx=10, pady=10)

        new_booking_frame = ttk.Frame(notebook)
        notebook.add(new_booking_frame, text='New Booking')
        self._setup_new_booking_tab(new_booking_frame)

        view_frame = ttk.Frame(notebook)
        notebook.add(view_frame, text='View Bookings')
        self._setup_view_bookings_tab(view_frame)

    def _setup_new_booking_tab(self, parent):
        header = ttk.Label(parent, text='Pre-Book Your Parking Slot', style='Header.TLabel')
        header.pack(pady=(10, 20))
        form_frame = ttk.Frame(parent)
        form_frame.pack(fill='x', padx=50, pady=10)

        ttk.Label(form_frame, text='Vehicle Number:', font=('Arial', 12)).grid(row=0, column=0, sticky='e', padx=5, pady=10)
        self.ui['booking_vehicle_entry'] = ttk.Entry(form_frame, font=('Arial', 12))
        self.ui['booking_vehicle_entry'].grid(row=0, column=1, sticky='w', padx=5, pady=10)

        ttk.Label(form_frame, text='Vehicle Type:', font=('Arial', 12)).grid(row=1, column=0, sticky='e', padx=5, pady=10)
        self.ui['booking_vehicle_type_var'] = tk.StringVar()
        self.ui['booking_vehicle_type_menu'] = ttk.Combobox(
            form_frame,
            textvariable=self.ui['booking_vehicle_type_var'],
            values=list(VEHICLE_COSTS.keys()),
            font=('Arial', 12),
            state='readonly'
        )
        self.ui['booking_vehicle_type_menu'].grid(row=1, column=1, sticky='w', padx=5, pady=10)
        self.ui['booking_vehicle_type_menu'].bind('<<ComboboxSelected>>', self.update_booking_slot_options)

        ttk.Label(form_frame, text='Parking Slot:', font=('Arial', 12)).grid(row=2, column=0, sticky='e', padx=5, pady=10)
        self.ui['booking_slot_var'] = tk.StringVar()
        self.ui['booking_slot_menu'] = ttk.Combobox(form_frame, textvariable=self.ui['booking_slot_var'], values=[], font=('Arial', 12), state='readonly')
        self.ui['booking_slot_menu'].grid(row=2, column=1, sticky='w', padx=5, pady=10)

        ttk.Label(form_frame, text='Booking Date:', font=('Arial', 12)).grid(row=3, column=0, sticky='e', padx=5, pady=10)
        date_frame = ttk.Frame(form_frame)
        date_frame.grid(row=3, column=1, sticky='w')
        now = datetime.now()
        self.ui['year_var'] = tk.StringVar(value=str(now.year))
        ttk.Combobox(date_frame, textvariable=self.ui['year_var'], width=5, values=[str(y) for y in range(now.year, now.year + 2)]).pack(side='left')
        self.ui['month_var'] = tk.StringVar(value=f'{now.month:02d}')
        ttk.Combobox(date_frame, textvariable=self.ui['month_var'], width=3, values=[f'{m:02d}' for m in range(1, 13)]).pack(side='left', padx=5)
        self.ui['day_var'] = tk.StringVar(value=f'{now.day:02d}')
        ttk.Combobox(date_frame, textvariable=self.ui['day_var'], width=3, values=[f'{d:02d}' for d in range(1, 32)]).pack(side='left')

        time_frame = ttk.Frame(form_frame)
        time_frame.grid(row=4, column=0, columnspan=2, pady=10)
        ttk.Label(time_frame, text='From:', font=('Arial', 12)).pack(side='left', padx=5)
        self.ui['start_hour_var'] = tk.StringVar(value=f'{(now.hour + 1) % 24:02d}')
        ttk.Combobox(time_frame, textvariable=self.ui['start_hour_var'], width=3, values=[f'{h:02d}' for h in range(0, 24)]).pack(side='left')
        self.ui['start_min_var'] = tk.StringVar(value='00')
        ttk.Combobox(time_frame, textvariable=self.ui['start_min_var'], width=3, values=['00', '15', '30', '45']).pack(side='left', padx=5)
        ttk.Label(time_frame, text='To:', font=('Arial', 12)).pack(side='left', padx=10)
        self.ui['end_hour_var'] = tk.StringVar(value=f'{(now.hour + 2) % 24:02d}')
        ttk.Combobox(time_frame, textvariable=self.ui['end_hour_var'], width=3, values=[f'{h:02d}' for h in range(0, 24)]).pack(side='left')
        self.ui['end_min_var'] = tk.StringVar(value='00')
        ttk.Combobox(time_frame, textvariable=self.ui['end_min_var'], width=3, values=['00', '15', '30', '45']).pack(side='left', padx=5)

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text='Check Availability', command=self.check_availability).pack(side='left', padx=10)
        ttk.Button(btn_frame, text='Calculate Fare & Book', command=self.make_booking).pack(side='left', padx=10)

    def _setup_view_bookings_tab(self, parent):
        header = ttk.Label(parent, text='Your Bookings', style='Header.TLabel')
        header.pack(pady=(10, 20))

        filter_frame = ttk.Frame(parent)
        filter_frame.pack(fill='x', padx=20, pady=10)
        ttk.Label(filter_frame, text='Filter by:', font=('Arial', 12)).pack(side='left', padx=5)
        self.ui['filter_var'] = tk.StringVar(value='All')
        ttk.Combobox(filter_frame, textvariable=self.ui['filter_var'], values=['All', 'Confirmed', 'Active', 'Completed'], state='readonly', width=12).pack(side='left', padx=5)
        ttk.Button(filter_frame, text='Apply', command=self.refresh_bookings).pack(side='left', padx=10)

        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill='both', expand=True, padx=20, pady=10)
        columns = ('ID', 'Vehicle', 'Type', 'Slot', 'Date', 'Time', 'Fee', 'Status', 'Original Slot')
        self.ui['bookings_tree'] = ttk.Treeview(tree_frame, columns=columns, show='headings', height=12)
        for col in columns:
            self.ui['bookings_tree'].heading(col, text=col)

        self.ui['bookings_tree'].column('ID', width=40, anchor='center')
        self.ui['bookings_tree'].column('Vehicle', width=100, anchor='center')
        self.ui['bookings_tree'].column('Type', width=100, anchor='center')
        self.ui['bookings_tree'].column('Slot', width=40, anchor='center')
        self.ui['bookings_tree'].column('Date', width=100, anchor='center')
        self.ui['bookings_tree'].column('Time', width=120, anchor='center')
        self.ui['bookings_tree'].column('Fee', width=80, anchor='e')
        self.ui['bookings_tree'].column('Status', width=80, anchor='center')
        self.ui['bookings_tree'].column('Original Slot', width=80, anchor='center')

        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=self.ui['bookings_tree'].yview)
        self.ui['bookings_tree'].configure(yscrollcommand=scrollbar.set)
        self.ui['bookings_tree'].pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill='x', pady=10, padx=20)
        ttk.Button(btn_frame, text='Refresh', command=self.refresh_bookings).pack(side='left', padx=5)
        ttk.Button(btn_frame, text='Activate Booking', command=self.handle_activate_booking).pack(side='left', padx=5)
        ttk.Button(btn_frame, text='Cancel Booking', command=self.handle_cancel_booking, style='Remove.TButton').pack(side='left', padx=5)

    def hide_all_tabs(self):
        for key in ['home_tab', 'parking_tab', 'dashboard_tab', 'bookings_tab']:
            if key in self.ui:
                self.ui[key].pack_forget()

    def show_home_tab(self):
        self.hide_all_tabs()
        self.ui['home_tab'].pack(fill=tk.BOTH, expand=True)
        self.update_home_stats()

    def show_parking_tab(self):
        self.hide_all_tabs()
        self.ui['parking_tab'].pack(fill=tk.BOTH, expand=True)
        self.update_slots_display()
        self.update_action_frames(None)

    def show_dashboard_tab(self):
        self.hide_all_tabs()
        self.ui['dashboard_tab'].pack(fill=tk.BOTH, expand=True)
        self.refresh_dashboard_view()

    def show_bookings_tab(self):
        self.hide_all_tabs()
        self.ui['bookings_tab'].pack(fill=tk.BOTH, expand=True)
        self.refresh_bookings()
        self.update_booking_slot_options()

    def update_home_stats(self):
        data = self.data_service.load_data()
        occupied_slots_count = sum(1 for s in data['slots'].values() if s['capacity_left'] < SLOT_CAPACITY)
        self.ui['stats_labels']['total_slots'].config(text=str(50))
        self.ui['stats_labels']['available_slots'].config(text=str(50 - occupied_slots_count))
        self.ui['stats_labels']['occupied_slots'].config(text=str(occupied_slots_count))
        self.ui['stats_labels']['vehicles_parked'].config(text=str(len(data['vehicles'])))

    def on_analytics_date_selected(self, event=None):
        selected_formatted_string = self.ui['analytics_date_var'].get()
        if selected_formatted_string and selected_formatted_string != 'No Data':
            target_date_str = selected_formatted_string.split(' ')[0]
            self.update_dashboard_stats(target_date_str)

    def refresh_dashboard_view(self):
        all_dates_formatted, today_str = self.analytics_service.update_and_get_analytics_dates()
        self.ui['analytics_date_combo']['values'] = all_dates_formatted
        today_formatted_str = next((d for d in all_dates_formatted if d.startswith(today_str)), '')

        if today_formatted_str:
            self.ui['analytics_date_var'].set(today_formatted_str)
        elif all_dates_formatted:
            self.ui['analytics_date_var'].set(all_dates_formatted[0])
        else:
            self.ui['analytics_date_var'].set('No Data')

        self.update_dashboard_stats(today_str)

    def update_dashboard_stats(self, target_date_str):
        stats_to_display = self.analytics_service.get_stats_for_date(target_date_str)
        self.ui['dashboard_title_label'].config(text=f'Analytics for {target_date_str}')
        self.ui['dashboard_labels']['revenue'].config(text=f'₹{stats_to_display.get("total_revenue", 0):.2f}')
        self.ui['dashboard_labels']['premium_revenue'].config(text=f'₹{stats_to_display.get("premium_revenue", 0):.2f}')
        self.ui['dashboard_labels']['penalty_revenue'].config(text=f'₹{stats_to_display.get("penalty_revenue", 0):.2f}')
        self.ui['dashboard_labels']['total_vehicles'].config(text=str(stats_to_display.get('total_vehicles', 0)))
        self.ui['dashboard_labels']['avg_duration'].config(text=f"{stats_to_display.get('avg_duration_hours', 0):.1f} hours")

        vehicle_counts = stats_to_display.get('vehicle_counts', {})
        self.ui['dashboard_labels']['cars'].config(text=str(vehicle_counts.get('Car', 0)))
        self.ui['dashboard_labels']['bike'].config(text=str(vehicle_counts.get('Bike', 0)))
        self.ui['dashboard_labels']['ev_cars'].config(text=str(vehicle_counts.get('EV Car', 0)))
        self.ui['dashboard_labels']['ev_bike'].config(text=str(vehicle_counts.get('EV Bike', 0)))

    def update_action_frames(self, selected_slot_data):
        self.ui['park_action_frame'].pack_forget()
        self.ui['remove_action_frame'].pack_forget()

        if selected_slot_data is None:
            self.ui['action_title_label'].config(text='Select a Slot to Begin')
            return

        slot_num = self.ui['selected_slot'].get()
        title_text = f'Actions for Slot {slot_num}'
        if selected_slot_data.get('is_premium'):
            title_text += ' (Premium ⭐)'
        if selected_slot_data.get('is_ev'):
            title_text += ' (EV ⚡)'
        self.ui['action_title_label'].config(text=title_text)

        bookings = self.booking_service.get_bookings()
        active_booking = next((b for b in bookings if b['slot'] == slot_num and b['status'] == 'Active'), None)
        physical_vehicles = selected_slot_data['vehicles']

        if selected_slot_data['capacity_left'] > 0:
            self.ui['park_action_frame'].pack(fill='x', padx=5, pady=5)
            allowed_types = []
            is_ev = selected_slot_data.get('is_ev', False)
            if selected_slot_data['capacity_left'] >= VEHICLE_COSTS['Car']:
                allowed_types.extend(['Car', 'Bike'])
                if is_ev:
                    allowed_types.extend(['EV Car', 'EV Bike'])
            else:
                allowed_types.append('Bike')
                if is_ev:
                    allowed_types.append('EV Bike')
            if not is_ev:
                allowed_types = [t for t in allowed_types if 'EV' not in t]
            self.ui['vehicle_type_menu']['values'] = allowed_types
            self.ui['vehicle_type_var'].set('')

        if physical_vehicles or active_booking:
            self.ui['remove_action_frame'].pack(fill='x', padx=5, pady=5)
            if physical_vehicles:
                if len(physical_vehicles) > 1:
                    self.ui['vehicle_to_remove_label'].grid()
                    self.ui['vehicle_to_remove_menu'].grid()
                    self.ui['vehicle_to_remove_menu']['values'] = physical_vehicles
                    self.ui['vehicle_to_remove_var'].set('')
                else:
                    self.ui['vehicle_to_remove_label'].grid_remove()
                    self.ui['vehicle_to_remove_menu'].grid_remove()
            else:
                self.ui['vehicle_to_remove_label'].grid_remove()
                self.ui['vehicle_to_remove_menu'].grid_remove()

    def select_slot(self, slot_num):
        self.ui['selected_slot'].set(str(slot_num))
        data = self.data_service.load_data()
        slot_data = data['slots'][str(slot_num)]
        self.update_action_frames(slot_data)
        self.update_slots_display()

    def update_slots_display(self):
        for widget in self.ui['slots_frame'].winfo_children():
            widget.destroy()

        data = self.data_service.load_data()
        slots = data['slots']
        bookings = self.booking_service.get_bookings()
        now = datetime.now()
        selected = self.ui['selected_slot'].get()

        active_reservations = {}
        next_reservations = {}
        for booking in bookings:
            if booking['status'] == 'Active':
                active_reservations[booking['slot']] = booking
            elif booking['status'] == 'Confirmed':
                start_time = datetime.strptime(booking['start_time'], '%Y-%m-%d %H:%M:%S')
                if booking['slot'] not in next_reservations or start_time < datetime.strptime(next_reservations[booking['slot']]['start_time'], '%Y-%m-%d %H:%M:%S'):
                    next_reservations[booking['slot']] = booking

        for i in range(1, 51):
            slot_str = str(i)
            slot_data = slots[slot_str]
            vehicle_list = slot_data['vehicles']
            capacity_left = slot_data['capacity_left']
            is_ev = slot_data['is_ev']
            is_premium = slot_data['is_premium']
            icon = ''
            if is_premium and is_ev:
                icon = ' ⭐⚡'
            elif is_premium:
                icon = ' ⭐'
            elif is_ev:
                icon = ' ⚡'

            if capacity_left < SLOT_CAPACITY:
                if capacity_left == 0:
                    color = '#e74c3c'
                    text = f"Slot {i}\nFull{icon}\n{', '.join(vehicle_list)}"
                else:
                    color = '#e67e22'
                    text = f'Slot {i}\n{len(vehicle_list)} Bike(s){icon}'
            elif slot_str in active_reservations:
                color = '#02EAFF'
                text = f'Slot {i}\nActive{icon}'
            elif slot_str in next_reservations:
                res_time = datetime.strptime(next_reservations[slot_str]['start_time'], '%Y-%m-%d %H:%M:%S')
                color = '#00bcd4'
                text = f"Slot {i}\nReserved{icon}\nFrom {res_time.strftime('%H:%M')}"
            else:
                color = '#f1c40f' if is_premium else '#2ecc71' if is_ev else '#3498db'
                text = f'Slot {i}\nAvailable{icon}'

            if slot_str == selected:
                color = '#8e44ad'

            slot_btn = tk.Button(
                self.ui['slots_frame'],
                text=text,
                bg=color,
                fg='white',
                font=('Arial', 9, 'bold'),
                width=12,
                height=4,
                justify='center',
                command=lambda s=i: self.select_slot(s)
            )
            slot_btn.grid(row=(i - 1) // 10, column=(i - 1) % 10, padx=4, pady=4)

    def park_vehicle(self):
        slot_str = self.ui['selected_slot'].get()
        if not slot_str:
            messagebox.showwarning('Warning', 'Please select a slot.')
            return

        vehicle_number = self.ui['vehicle_entry'].get().strip().upper()
        vehicle_type = self.ui['vehicle_type_var'].get()
        if not vehicle_number or not vehicle_type:
            messagebox.showwarning('Warning', 'Please enter vehicle number and type.')
            return

        data = self.data_service.load_data()
        slot_data = data['slots'][slot_str]
        now = datetime.now()
        cost = VEHICLE_COSTS[vehicle_type]
        is_ev_vehicle = 'EV' in vehicle_type

        if is_ev_vehicle and not slot_data['is_ev']:
            messagebox.showerror('Invalid Slot', 'EVs can only park in EV-capable slots (⚡).')
            return

        if vehicle_number in data['vehicles']:
            messagebox.showerror('Error', f'Vehicle {vehicle_number} is already parked.')
            return

        if slot_data['capacity_left'] < cost:
            messagebox.showerror('Capacity Error', f'Not enough space in Slot {slot_str}.')
            return

        bookings = self.booking_service.get_bookings()
        capacity_used_by_bookings = 0
        for booking in bookings:
            if booking['slot'] != slot_str or booking['status'] != 'Active':
                continue
            start_time = datetime.strptime(booking['start_time'], '%Y-%m-%d %H:%M:%S')
            end_time = datetime.strptime(booking['end_time'], '%Y-%m-%d %H:%M:%S')
            if start_time <= now < end_time and booking['vehicle'].upper() != vehicle_number:
                capacity_used_by_bookings += booking.get('cost', 1)

        if (SLOT_CAPACITY - slot_data['capacity_left']) + capacity_used_by_bookings + cost > SLOT_CAPACITY:
            messagebox.showerror('Reservation Conflict', f'Slot {slot_str} is reserved. Not enough capacity for this {vehicle_type}.')
            return

        future_bookings_for_slot = [b for b in bookings if b['slot'] == slot_str and b['status'] == 'Confirmed' and datetime.strptime(b['start_time'], '%Y-%m-%d %H:%M:%S') > now]
        if future_bookings_for_slot:
            next_booking = min(future_bookings_for_slot, key=lambda b: datetime.strptime(b['start_time'], '%Y-%m-%d %H:%M:%S'))
            next_booking_start = datetime.strptime(next_booking['start_time'], '%Y-%m-%d %H:%M:%S')
            hours_available = (next_booking_start - now).total_seconds() / 3600
            confirmation = messagebox.askyesno(
                'Temporary Parking',
                f"Slot {slot_str} is reserved from {next_booking_start.strftime('%H:%M')} .\n\nYou can park for a maximum of {hours_available:.1f} hours.\n\nDo you want to proceed?"
            )
            if not confirmation:
                return

        slot_data['vehicles'].append(vehicle_number)
        slot_data['capacity_left'] -= cost
        data['vehicles'][vehicle_number] = {
            'slot': slot_str,
            'type': vehicle_type,
            'entry_time': now.strftime('%Y-%m-%d %H:%M:%S')
        }
        self.data_service.save_data(data)
        self.speak(f'Vehicle {self.format_vehicle_number_for_speech(vehicle_number)} parked in slot {slot_str}.')
        threading.Timer(0.1, lambda: messagebox.showinfo('Success', f'{vehicle_type} {vehicle_number} parked in slot {slot_str}')).start()

        self.ui['vehicle_entry'].delete(0, tk.END)
        self.ui['selected_slot'].set('')
        self.update_action_frames(None)
        self.update_slots_display()
        self.update_home_stats()

    def remove_vehicle(self):
        slot_str = self.ui['selected_slot'].get()
        if not slot_str:
            messagebox.showwarning('Warning', 'Please select a slot.')
            return

        data = self.data_service.load_data()
        slot_data = data['slots'][slot_str]
        vehicles_in_slot = slot_data['vehicles']
        vehicle_to_remove = ''

        if vehicles_in_slot:
            vehicle_to_remove = vehicles_in_slot[0]
            if len(vehicles_in_slot) > 1:
                selected_vehicle = self.ui['vehicle_to_remove_var'].get()
                if not selected_vehicle:
                    messagebox.showwarning('Selection Needed', 'Please select a bike to remove.')
                    return
                vehicle_to_remove = selected_vehicle

            vehicle_details = data['vehicles'][vehicle_to_remove]
            vehicle_type = vehicle_details['type']
            entry_time = datetime.strptime(vehicle_details['entry_time'], '%Y-%m-%d %H:%M:%S')
            cost = VEHICLE_COSTS[vehicle_type]
            exit_time = datetime.now()
            hours = (exit_time - entry_time).total_seconds() / 3600
            billed_hours = max(1, int(hours) + (1 if hours % 1 > 0 else 0))
            rate = VEHICLE_COSTS[vehicle_type]
            if billed_hours <= 6:
                base_charge = rate
            elif billed_hours <= 12:
                base_charge = rate + (billed_hours - 6) * (rate * 0.9)
            else:
                base_charge = rate + 6 * (rate * 0.9) + (billed_hours - 12) * (rate * 0.8)

            overnight_fee = 100 if exit_time.date() > entry_time.date() else 0
            weekend_multiplier = 1.10 if exit_time.weekday() in {5, 6} else 1.0
            premium_fee_applied = 0
            if slot_data.get('is_premium'):
                extra_premium_blocks = int(hours // 6)
                premium_fee_applied = 50 + (extra_premium_blocks * 50)

            penalty_fee = vehicle_details.get('penalty', 0)
            final_total_charge = round((base_charge + overnight_fee + premium_fee_applied) * weekend_multiplier + penalty_fee, 2)

            log_entry = {
                'vehicle_number': vehicle_to_remove,
                'type': vehicle_type,
                'slot': slot_str,
                'entry_time': vehicle_details['entry_time'],
                'exit_time': exit_time.strftime('%Y-%m-%d %H:%M:%S'),
                'duration_hours': round(hours, 2),
                'charge': final_total_charge,
                'premium_fee': premium_fee_applied,
                'overnight_fee': overnight_fee,
                'penalty_fee': penalty_fee,
                'weekend_multiplier': weekend_multiplier
            }
            self.data_service.save_to_log(log_entry)
            slot_data['vehicles'].remove(vehicle_to_remove)
            slot_data['capacity_left'] += cost
            del data['vehicles'][vehicle_to_remove]
            self.data_service.save_data(data)

            charge_message = (
                f'Vehicle: {vehicle_to_remove}\n'
                f'Duration: {hours:.2f} hours (Billed for {billed_hours}h)\n'
                f'Base Charge: ₹{base_charge:.2f}\n'
                f'Overnight Fee: ₹{overnight_fee}\n'
                f'Premium Slot Fee: ₹{premium_fee_applied:.2f}\n'
                f'Weekend Multiplier: x{weekend_multiplier:.2f}\n'
            )
            if penalty_fee > 0:
                charge_message += f'Overstay Penalty: ₹{penalty_fee:.2f}\n\n'
            charge_message += f'Total Charge: ₹{final_total_charge:.2f}'

            self.speak(f'Vehicle {self.format_vehicle_number_for_speech(vehicle_to_remove)} removed. Total charge is {final_total_charge:.0f} rupees.')
            threading.Timer(0.1, lambda: messagebox.showinfo('Success', f'Vehicle removed.\n\n{charge_message}')).start()
        else:
            self._remove_booking_vehicle(slot_str)

        self.ui['selected_slot'].set('')
        self.update_action_frames(None)
        self.update_slots_display()
        self.update_home_stats()
        self.update_booking_slot_options()
        self.refresh_bookings()

    def _remove_booking_vehicle(self, slot_str):
        bookings = self.booking_service.get_bookings()
        active_booking = next((b for b in bookings if b['slot'] == slot_str and b['status'] == 'Active'), None)
        if not active_booking:
            messagebox.showerror('Error', 'Slot is empty.')
            return

        vehicle_type = active_booking['vehicle_type']
        entry_time = datetime.strptime(active_booking['start_time'], '%Y-%m-%d %H:%M:%S')
        advance_paid = active_booking.get('charge', 0)
        exit_time = datetime.now()
        hours = (exit_time - entry_time).total_seconds() / 3600
        billed_hours = max(1, int(hours) + (1 if hours % 1 > 0 else 0))
        rate = VEHICLE_COSTS[vehicle_type]

        if billed_hours <= 6:
            base_charge = rate
        elif billed_hours <= 12:
            base_charge = rate + (billed_hours - 6) * (rate * 0.9)
        else:
            base_charge = rate + 6 * (rate * 0.9) + (billed_hours - 12) * (rate * 0.8)

        overnight_fee = 100 if exit_time.date() > entry_time.date() else 0
        weekend_multiplier = 1.10 if exit_time.weekday() in {5, 6} else 1.0
        premium_fee_applied = 0
        data = self.data_service.load_data()
        slot_data = data['slots'][slot_str]
        if slot_data.get('is_premium'):
            extra_premium_blocks = int(hours // 6)
            premium_fee_applied = 50 + (extra_premium_blocks * 50)

        total_charge = round((base_charge + overnight_fee + premium_fee_applied) * weekend_multiplier, 2)
        final_due = round(total_charge - advance_paid, 2)

        log_entry = {
            'vehicle_number': active_booking['vehicle'],
            'type': vehicle_type,
            'slot': slot_str,
            'entry_time': active_booking['start_time'],
            'exit_time': exit_time.strftime('%Y-%m-%d %H:%M:%S'),
            'duration_hours': round(hours, 2),
            'charge': total_charge,
            'premium_fee': premium_fee_applied,
            'overnight_fee': overnight_fee,
            'weekend_multiplier': weekend_multiplier
        }
        self.data_service.save_to_log(log_entry)
        active_booking['status'] = 'Completed'
        self.data_service.save_bookings(bookings)

        charge_message = (
            f"Booked Vehicle: {active_booking['vehicle']}\n"
            f'Duration: {hours:.2f} hours (Billed for {billed_hours}h)\n'
            f'Total Charge: ₹{total_charge:.2f}\n'
            f'Advance Paid: -₹{advance_paid:.2f}\n\n'
            f'Final Amount Due: ₹{final_due:.2f}'
        )
        self.speak(f"Booking for {self.format_vehicle_number_for_speech(active_booking['vehicle'])} completed. Final amount due is {final_due:.0f} rupees.")
        threading.Timer(0.1, lambda: messagebox.showinfo('Booking Completed', charge_message)).start()

    def refresh_bookings(self):
        for item in self.ui['bookings_tree'].get_children():
            self.ui['bookings_tree'].delete(item)

        filter_status = self.ui['filter_var'].get()
        bookings = self.booking_service.get_bookings()
        for booking in bookings:
            if filter_status == 'All' or booking['status'] == filter_status:
                start = datetime.strptime(booking['start_time'], '%Y-%m-%d %H:%M:%S')
                end = datetime.strptime(booking['end_time'], '%Y-%m-%d %H:%M:%S')
                date_str = start.strftime('%Y-%m-%d')
                time_str = f"{start.strftime('%H:%M')} to {end.strftime('%H:%M')}"
                fee_str = f"₹{booking.get('charge', 0):.2f}"
                slot_display = booking['slot']
                original_slot = booking.get('original_slot', '-')

                self.ui['bookings_tree'].insert('', 'end', values=(
                    booking['id'],
                    booking['vehicle'],
                    booking.get('vehicle_type', 'N/A'),
                    slot_display,
                    date_str,
                    time_str,
                    fee_str,
                    booking['status'],
                    original_slot
                ))

    def handle_cancel_booking(self):
        selected = self.ui['bookings_tree'].selection()
        if not selected:
            messagebox.showwarning('Warning', 'Please select a booking to cancel')
            return

        booking_id = int(self.ui['bookings_tree'].item(selected[0], 'values')[0])
        booking_status = self.ui['bookings_tree'].item(selected[0], 'values')[7]
        if booking_status != 'Confirmed':
            messagebox.showerror('Error', "Cannot cancel a booking that is '{booking_status}'.")
            return

        success, message = self.booking_service.cancel_booking_by_id(booking_id)
        if success:
            self.speak('Booking cancelled.')
            threading.Timer(0.1, lambda: messagebox.showinfo('Success', message)).start()
            self.refresh_bookings()
            self.update_slots_display()
        else:
            messagebox.showerror('Error', message)

    def handle_activate_booking(self):
        selected = self.ui['bookings_tree'].selection()
        if not selected:
            messagebox.showwarning('Warning', 'Please select a booking to activate.')
            return

        item = self.ui['bookings_tree'].item(selected[0], 'values')
        booking_id = int(item[0])
        booking_status = item[7]
        if booking_status == 'Active':
            messagebox.showinfo('Info', 'This booking is already active.')
            return
        if booking_status == 'Completed':
            messagebox.showerror('Error', 'This booking is already completed.')
            return
        if booking_status != 'Confirmed':
            messagebox.showerror('Error', f"Cannot activate a booking with status '{booking_status}'.")
            return

        bookings_data = self.data_service.load_bookings()
        target_booking = next((b for b in bookings_data if b['id'] == booking_id), None)
        if not target_booking:
            messagebox.showerror('Error', 'Booking not found in database.')
            return

        slot_data = self.data_service.load_data()['slots'][target_booking['slot']]
        cost = target_booking.get('cost', VEHICLE_COSTS.get(target_booking['vehicle_type'], 1))
        if slot_data['capacity_left'] < cost:
            self._resolve_slot_conflict(target_booking, slot_data)
            return

        self._activate_booking_same_slot(target_booking)

    def _resolve_slot_conflict(self, target_booking, occupied_slot_data):
        data = self.data_service.load_data()
        penalty_applied_to = []
        for vehicle_num in occupied_slot_data['vehicles']:
            if vehicle_num in data['vehicles']:
                data['vehicles'][vehicle_num]['penalty'] = data['vehicles'][vehicle_num].get('penalty', 0) + 100
                penalty_applied_to.append(vehicle_num)
        if penalty_applied_to:
            self.data_service.save_data(data)
            messagebox.showwarning(
                'Penalty Applied',
                f"Vehicle(s) {', '.join(penalty_applied_to)} are overstaying in reserved slot {target_booking['slot']} and a ₹100 penalty has been added."
            )

        new_slot_id = None
        is_ev_vehicle = 'EV' in target_booking['vehicle_type']
        required_cost = target_booking['cost']
        start_time_obj = datetime.strptime(target_booking['start_time'], '%Y-%m-%d %H:%M:%S')
        end_time_obj = datetime.strptime(target_booking['end_time'], '%Y-%m-%d %H:%M:%S')
        candidate_slots = []

        for slot_id, s_data in data['slots'].items():
            if s_data['capacity_left'] < required_cost:
                continue
            if is_ev_vehicle and not s_data['is_ev']:
                continue
            available, _ = self.booking_service.is_slot_available(slot_id, target_booking['vehicle_type'], start_time_obj, end_time_obj)
            if available:
                candidate_slots.append((slot_id, s_data))

        if candidate_slots:
            premium_candidates = [s for s in candidate_slots if s[1]['is_premium']]
            new_slot_id = premium_candidates[0][0] if premium_candidates else candidate_slots[0][0]

        if new_slot_id:
            original_charge = target_booking['charge']
            discounted_charge = round(original_charge * 0.90, 2)
            target_booking['charge'] = discounted_charge
            target_booking['original_charge'] = original_charge
            target_booking['slot'] = new_slot_id
            target_booking['original_slot'] = target_booking['slot']
            target_booking['status'] = 'Active'
            self.data_service.save_bookings(self.data_service.load_bookings())
            speak_msg = (
                f"Sorry for the inconvenience. Your slot {target_booking['original_slot']} was occupied. "
                f"You have been {'upgraded to premium' if data['slots'][new_slot_id]['is_premium'] else 'moved to'} slot {new_slot_id}. "
                'An additional 10 percent discount has been applied.'
            )
            self.speak(speak_msg)
            popup_msg = (
                f"Sorry for the inconvenience!\n\nYour original slot {target_booking['original_slot']} was occupied. "
                f"You have been moved to {'Premium' if data['slots'][new_slot_id]['is_premium'] else ''} Slot {new_slot_id}.\n\n"
                f"- Original Fee: ₹{original_charge:.2f}\n"
                f"- New Fee (10% off): ₹{discounted_charge:.2f}\n\n"
                'This booking is now active.'
            )
            threading.Timer(0.1, lambda: messagebox.showinfo('Booking Upgraded!', popup_msg)).start()
        else:
            self.speak(f"We are extremely sorry. Your booked slot {target_booking['slot']} is occupied, and we could not find another free slot.")
            messagebox.showerror(
                'System Failure',
                f"Your booked slot {target_booking['slot']} is occupied.\n\nA penalty was applied to the offending vehicle(s), but we could NOT find any other empty slot for you.\n\nPlease contact the manager for an immediate resolution."
            )

        self.refresh_bookings()
        self.update_slots_display()

    def _activate_booking_same_slot(self, target_booking):
        start = datetime.strptime(target_booking['start_time'], '%Y-%m-%d %H:%M:%S')
        now = datetime.now()
        target_booking['status'] = 'Active'
        if now < start:
            target_booking['start_time'] = now.strftime('%Y-%m-%d %H:%M:%S')
            self.speak(f"Early check in for slot {target_booking['slot']} activated.")
            threading.Timer(0.1, lambda: messagebox.showinfo('Success', 'Early check-in successful. Booking is now active.')).start()
        else:
            self.speak(f"Booking for slot {target_booking['slot']} activated.")
            threading.Timer(0.1, lambda: messagebox.showinfo('Success', 'Booking is now active.')).start()
        self.data_service.save_bookings(self.data_service.load_bookings())

    def _validate_and_get_times(self):
        try:
            year = int(self.ui['year_var'].get())
            month = int(self.ui['month_var'].get())
            day = int(self.ui['day_var'].get())
            datetime(year, month, day)

            start_time = datetime.strptime(f"{year}-{month:02d}-{day:02d} {self.ui['start_hour_var'].get()}:{self.ui['start_min_var'].get()}", '%Y-%m-%d %H:%M')
            end_time = datetime.strptime(f"{year}-{month:02d}-{day:02d} {self.ui['end_hour_var'].get()}:{self.ui['end_min_var'].get()}", '%Y-%m-%d %H:%M')

            if start_time < datetime.now() - timedelta(minutes=10):
                messagebox.showerror('Error', 'Cannot book for a time in the past.')
                return None, None
            if end_time <= start_time:
                messagebox.showerror('Error', 'End time must be after start time')
                return None, None

            return start_time, end_time
        except (ValueError, TypeError):
            messagebox.showerror('Error', 'Invalid date or time input.')
            return None, None

    def check_availability(self):
        slot = self.ui['booking_slot_var'].get()
        vehicle_type = self.ui['booking_vehicle_type_var'].get()
        if not slot or not vehicle_type:
            messagebox.showwarning('Warning', 'Please select a vehicle type and slot')
            return

        start_time, end_time = self._validate_and_get_times()
        if not start_time:
            return

        available, message = self.booking_service.is_slot_available(slot, vehicle_type, start_time, end_time)
        if available:
            total, base, premium = self.booking_service.calculate_booking_fee(slot, vehicle_type, start_time, end_time)
            fee_message = (
                f'Base Charge: ₹{base:.2f}\n'
                f'Premium Slot Fee: ₹{premium:.2f}\n\n'
                f'Total Advance: ₹{total:.2f}'
            )
            self.speak(f'Slot {slot} is available. The total advance is {total:.0f} rupees.')
            threading.Timer(0.1, lambda: messagebox.showinfo('Available', f'Slot {slot} is available!\n\n{fee_message}')).start()
        else:
            self.speak(message)
            threading.Timer(0.1, lambda: messagebox.showwarning('Not Available', message)).start()

    def make_booking(self):
        vehicle = self.ui['booking_vehicle_entry'].get().strip().upper()
        vehicle_type = self.ui['booking_vehicle_type_var'].get()
        slot = self.ui['booking_slot_var'].get()
        if not vehicle or not slot or not vehicle_type:
            messagebox.showerror('Error', 'Please fill all required fields')
            return

        start_time, end_time = self._validate_and_get_times()
        if not start_time:
            return

        available, message = self.booking_service.is_slot_available(slot, vehicle_type, start_time, end_time)
        if not available:
            self.speak(message)
            threading.Timer(0.1, lambda: messagebox.showerror('Booking Error', message)).start()
            self.update_booking_slot_options()
            return

        total, base, premium = self.booking_service.calculate_booking_fee(slot, vehicle_type, start_time, end_time)
        if total <= 0:
            messagebox.showerror('Error', 'Invalid booking duration or type.')
            return

        fee_message = (
            f'Vehicle: {vehicle}\n'
            f'Slot: {slot} ({"Premium" if premium > 0 else "Standard"})\n'
            f'From: {start_time.strftime("%Y-%m-%d %H:%M")}\n'
            f'To:   {end_time.strftime("%Y-%m-%d %H:%M")}\n\n'
            f'Base Charge: ₹{base:.2f}\n'
            f'Premium Slot Fee: ₹{premium:.2f}\n\n'
            f'Total Advance: ₹{total:.2f}'
        )

        self.speak(f'The total advance fee for slot {slot} is {total:.0f} rupees. Please pay now to confirm your booking.')
        confirmation = messagebox.askyesno('Confirm Payment', f'Please confirm your booking details:\n\n{fee_message}\n\nPay now to confirm this booking?')
        if confirmation:
            success, message = self.booking_service.add_booking(vehicle, vehicle_type, slot, start_time, end_time, total, premium)
            if success:
                self.speak(f'Booking confirmed for slot {slot}.')
                threading.Timer(0.1, lambda: messagebox.showinfo('Success', message)).start()
                self.refresh_bookings()
                self.update_slots_display()
                self.ui['booking_vehicle_entry'].delete(0, tk.END)
                self.update_booking_slot_options()
            else:
                messagebox.showerror('Error', message)
        else:
            self.speak('Booking cancelled.')
            threading.Timer(0.1, lambda: messagebox.showinfo('Booking Cancelled', 'Booking was not confirmed.')).start()

    def update_booking_slot_options(self, event=None):
        vehicle_type = self.ui['booking_vehicle_type_var'].get()
        if not vehicle_type:
            self.ui['booking_slot_menu']['values'] = []
            self.ui['booking_slot_var'].set('')
            return

        is_ev_vehicle = 'EV' in vehicle_type
        cost = VEHICLE_COSTS[vehicle_type]
        compatible_slots = []
        data = self.data_service.load_data()
        for i in range(1, 51):
            slot_str = str(i)
            slot_data = data['slots'][slot_str]
            if slot_data['capacity_left'] < cost:
                continue
            if is_ev_vehicle and not slot_data['is_ev']:
                continue
            compatible_slots.append(slot_str)

        self.ui['booking_slot_menu']['values'] = compatible_slots
        self.ui['booking_slot_var'].set('')

    @staticmethod
    def format_vehicle_number_for_speech(vehicle_number):
        spoken_form = ''
        for char in vehicle_number.strip().upper():
            if char == '0':
                spoken_form += 'zero '
            elif char == 'E':
                spoken_form += 'ee '
            else:
                spoken_form += f'{char} '
        return spoken_form.strip()

    @staticmethod
    def speak(text):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            rate = engine.getProperty('rate')
            engine.setProperty('rate', rate - 10)
            threading.Thread(target=lambda: (engine.say(text), engine.runAndWait()), daemon=True).start()
        except Exception:
            pass


if __name__ == '__main__':
    root = tk.Tk()
    root.title('Advanced Parking Management System')
    root.state('zoomed')
    ParkingApp(root)
    root.mainloop()
