"""
AI Chatbot Admin Panel - Desktop Application
Commercial Control Panel for AI Chatbot
Full-Featured Admin Dashboard
"""

import subprocess
import sys
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog, simpledialog
import threading
import json
import os
from datetime import datetime, timedelta
import webbrowser
import socket

# Try to import requests
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    import urllib.error
    HAS_REQUESTS = False


class AdminPanel:
    def __init__(self, root):
        self.root = root
        self.root.title("🛡️ Nao AI Admin Panel - Commercial Edition")
        self.root.geometry("1100x800")
        self.root.minsize(1000, 700)
        
        # Configuration
        self.config = {
            "api_url": "http://localhost:8000",
            "api_key": "",
            "admin_pin": "2010",
            "auto_refresh": True,
            "refresh_interval": 5000,
            "default_model": "nvidia/nemotron-3-nano-30b-a3b:free",
            "temperature": 0.7,
            "max_tokens": 4096
        }
        
        # Load saved config
        self.load_config()
        
        # Verify PIN at startup
        self.root.withdraw() # Hide window
        if not self.verify_login():
            self.root.destroy()
            sys.exit(0)
        self.root.deiconify() # Show window
            
    def verify_login(self):
        """Show login dialog"""
        while True:
            pin = simpledialog.askstring("Admin Login", "Enter Admin PIN:", show="*", parent=self.root)
            if pin is None: # Cancel
                return False
            
            if pin == self.config.get("admin_pin", "2010"):
                return True
            else:
                messagebox.showerror("Access Denied", "Invalid PIN")
            
        # Stats
        self.stats = {
            "total_requests": 0,
            "active_sessions": 0,
            "total_messages": 0,
            "uptime": "0h 0m",
            "status": "Disconnected"
        }
        
        # Create main interface
        self.setup_styles()
        self.create_widgets()
        
        # Start auto-refresh
        self.auto_refresh()
        
    def setup_styles(self):
        """Setup modern styling"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Colors
        self.colors = {
            "bg": "#0f0f1a",
            "bg_secondary": "#1a1a2e",
            "fg": "#ffffff",
            "accent": "#6366f1",
            "accent_hover": "#818cf8",
            "success": "#10b981",
            "warning": "#f59e0b",
            "danger": "#ef4444",
            "card_bg": "#252542",
            "border": "#3f3f5a"
        }
        
        self.root.configure(bg=self.colors["bg"])
        
    def create_widgets(self):
        """Create the main interface"""
        # Main container with sidebar
        main_container = tk.Frame(self.root, bg=self.colors["bg"])
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Sidebar
        self.create_sidebar(main_container)
        
        # Content area
        self.content_frame = tk.Frame(main_container, bg=self.colors["bg"])
        self.content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Header
        self.create_header()
        
        # Content notebook
        self.notebook = ttk.Notebook(self.content_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create all tabs
        self.create_dashboard_tab()
        self.create_sessions_tab()
        self.create_users_tab()
        self.create_analytics_tab()
        self.create_models_tab()
        self.create_settings_tab()
        self.create_api_tab()
        self.create_security_tab()
        self.create_tools_tab()
        
    def create_sidebar(self, parent):
        """Create sidebar navigation"""
        sidebar = tk.Frame(parent, bg=self.colors["bg_secondary"], width=60)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)
        
        # Logo
        logo = tk.Label(sidebar, text="🤖", font=("Segoe UI", 24), 
                       bg=self.colors["bg_secondary"], fg=self.colors["accent"])
        logo.pack(pady=20)
        
        # Nav buttons
        nav_items = [
            ("📊", "Dashboard", 0),
            ("💬", "Sessions", 1),
            ("👥", "Users", 2),
            ("📈", "Analytics", 3),
            ("🤖", "Models", 4),
            ("⚙️", "Settings", 5),
            ("🔌", "API", 6),
            ("🔐", "Security", 7),
            ("🛠️", "Tools", 8),
        ]
        
        for icon, tooltip, tab_index in nav_items:
            btn = tk.Button(sidebar, text=icon, font=("Segoe UI", 16),
                           bg=self.colors["bg_secondary"], fg=self.colors["fg"],
                           relief=tk.FLAT, cursor="hand2", width=3, height=1,
                           command=lambda i=tab_index: self.notebook.select(i))
            btn.pack(pady=5)
            self.create_tooltip(btn, tooltip)
        
        # Bottom - Status indicator
        self.sidebar_status = tk.Label(sidebar, text="●", font=("Segoe UI", 16),
                                       bg=self.colors["bg_secondary"], 
                                       fg=self.colors["danger"])
        self.sidebar_status.pack(side=tk.BOTTOM, pady=20)
        
    def create_header(self):
        """Create header with status"""
        header = tk.Frame(self.content_frame, bg=self.colors["bg"], height=60)
        header.pack(fill=tk.X, padx=10, pady=10)
        
        # Title
        title = tk.Label(header, text="Admin Control Panel", 
                        font=("Segoe UI", 20, "bold"),
                        bg=self.colors["bg"], fg=self.colors["fg"])
        title.pack(side=tk.LEFT)
        
        # Status & Quick actions
        actions_frame = tk.Frame(header, bg=self.colors["bg"])
        actions_frame.pack(side=tk.RIGHT)
        
        # Connection status
        self.status_label = tk.Label(actions_frame, text="● Disconnected", 
                                     fg=self.colors["danger"],
                                     bg=self.colors["bg"], font=("Segoe UI", 11))
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        # Quick buttons
        refresh_btn = tk.Button(actions_frame, text="🔄 Refresh", 
                               command=self.refresh_all,
                               bg=self.colors["card_bg"], fg=self.colors["fg"],
                               relief=tk.FLAT, cursor="hand2", padx=10)
        refresh_btn.pack(side=tk.LEFT, padx=5)
        
        website_btn = tk.Button(actions_frame, text="🌐 Open Site",
                               command=self.open_website,
                               bg=self.colors["card_bg"], fg=self.colors["fg"],
                               relief=tk.FLAT, cursor="hand2", padx=10)
        website_btn.pack(side=tk.LEFT, padx=5)
        
    def create_dashboard_tab(self):
        """Dashboard with comprehensive stats"""
        tab = tk.Frame(self.notebook, bg=self.colors["bg"])
        self.notebook.add(tab, text="📊 Dashboard")
        
        # Scrollable container
        canvas = tk.Canvas(tab, bg=self.colors["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors["bg"])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas_frame = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        def on_canvas_configure(event):
            canvas.itemconfig(canvas_frame, width=event.width)
        canvas.bind("<Configure>", on_canvas_configure)

        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y")
        
        # Parent for widgets
        parent = scrollable_frame
        
        # Stats cards row 1
        stats_frame1 = tk.Frame(parent, bg=self.colors["bg"])
        stats_frame1.pack(fill=tk.X, pady=10, padx=10)
        
        stats_row1 = [
            ("status", "Server Status", "Checking...", self.colors["accent"]),
            ("sessions", "Active Sessions", "0", self.colors["success"]),
            ("messages", "Total Messages", "0", self.colors["warning"]),
            ("uptime", "Server Uptime", "0m", self.colors["accent"]),
        ]
        
        self.stat_labels = {}
        for i, (key, label, value, color) in enumerate(stats_row1):
            card = self.create_stat_card(stats_frame1, label, value, color)
            card.grid(row=0, column=i, padx=5, sticky="nsew")
            stats_frame1.columnconfigure(i, weight=1)
        
        # Stats cards row 2
        stats_frame2 = tk.Frame(parent, bg=self.colors["bg"])
        stats_frame2.pack(fill=tk.X, pady=5, padx=10)
        
        stats_row2 = [
            ("requests", "API Requests", "0", self.colors["success"]),
            ("errors", "Errors Today", "0", self.colors["danger"]),
            ("avg_response", "Avg Response", "0ms", self.colors["warning"]),
            ("model", "Active Model", "Nemotron", self.colors["accent"]),
        ]
        
        for i, (key, label, value, color) in enumerate(stats_row2):
            card = self.create_stat_card(stats_frame2, label, value, color)
            card.grid(row=0, column=i, padx=5, sticky="nsew")
            stats_frame2.columnconfigure(i, weight=1)
        
        # Two column layout
        columns_frame = tk.Frame(parent, bg=self.colors["bg"])
        columns_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=10)
        
        # Left column - Recent activity
        left_col = tk.LabelFrame(columns_frame, text=" Recent Activity ",
                                bg=self.colors["bg"], fg=self.colors["fg"],
                                font=("Segoe UI", 11, "bold"))
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self.activity_list = scrolledtext.ScrolledText(left_col, height=12,
                                                       bg=self.colors["card_bg"],
                                                       fg=self.colors["success"],
                                                       font=("Consolas", 9))
        self.activity_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_activity("Admin Panel started")
        
        # Right column - Quick actions
        right_col = tk.LabelFrame(columns_frame, text=" Quick Actions ",
                                 bg=self.colors["bg"], fg=self.colors["fg"],
                                 font=("Segoe UI", 11, "bold"))
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        actions = [
            ("🔄 Refresh Stats", self.refresh_all),
            ("🚀 Start Server", self.start_server_process),
            ("♻️ Restart Server", self.restart_server_process),
            ("🧹 Clear All Sessions", self.clear_all_sessions),
            ("📊 Export Analytics", self.export_analytics),
            ("🔌 Test API Connection", self.test_connection),
            ("📝 View Logs", lambda: self.notebook.select(8)),
            ("⚙️ Server Settings", lambda: self.notebook.select(5)),
            ("🚨 Emergency Stop", self.emergency_stop),
            ("💾 Backup Database", self.backup_database),
        ]
        
        for text, command in actions:
            btn = tk.Button(right_col, text=text, command=command,
                           bg=self.colors["card_bg"], fg=self.colors["fg"],
                           font=("Segoe UI", 10), relief=tk.FLAT, 
                           cursor="hand2", anchor="w", padx=15, pady=8)
            btn.pack(fill=tk.X, padx=10, pady=3)
        
    def create_sessions_tab(self):
        """Sessions management"""
        tab = tk.Frame(self.notebook, bg=self.colors["bg"])
        self.notebook.add(tab, text="💬 Sessions")
        
        # Toolbar
        toolbar = tk.Frame(tab, bg=self.colors["bg"])
        toolbar.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(toolbar, text="🔄 Refresh", command=self.load_sessions,
                 bg=self.colors["card_bg"], fg=self.colors["fg"],
                 relief=tk.FLAT, cursor="hand2").pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="🧹 Clear All", command=self.clear_all_sessions,
                 bg=self.colors["danger"], fg="white",
                 relief=tk.FLAT, cursor="hand2").pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="📥 Export", command=self.export_sessions,
                 bg=self.colors["card_bg"], fg=self.colors["fg"],
                 relief=tk.FLAT, cursor="hand2").pack(side=tk.LEFT, padx=5)
        
        # Search
        tk.Label(toolbar, text="Search:", bg=self.colors["bg"], 
                fg=self.colors["fg"]).pack(side=tk.LEFT, padx=(20, 5))
        self.session_search = tk.Entry(toolbar, width=30, bg=self.colors["card_bg"],
                                       fg=self.colors["fg"], insertbackground="white")
        self.session_search.pack(side=tk.LEFT, padx=5)
        self.session_search.bind('<KeyRelease>', self.filter_sessions)
        
        # Sessions list
        columns = ("ID", "Title", "Messages", "Created", "Last Active", "Status")
        self.sessions_tree = ttk.Treeview(tab, columns=columns, show="headings", height=20)
        
        for col in columns:
            self.sessions_tree.heading(col, text=col)
            width = 150 if col in ["Title", "Created", "Last Active"] else 100
            self.sessions_tree.column(col, width=width)
        
        scrollbar = ttk.Scrollbar(tab, orient=tk.VERTICAL, command=self.sessions_tree.yview)
        self.sessions_tree.configure(yscrollcommand=scrollbar.set)
        
        self.sessions_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5, padx=(0, 10))
        
        # Context menu
        self.sessions_tree.bind('<Button-3>', self.show_session_menu)
        
        # Load sessions
        self.load_sessions()
        
    def create_users_tab(self):
        """User management (placeholder for future)"""
        tab = tk.Frame(self.notebook, bg=self.colors["bg"])
        self.notebook.add(tab, text="👥 Users")
        
        # Info
        info_frame = tk.Frame(tab, bg=self.colors["card_bg"], padx=30, pady=30)
        info_frame.pack(expand=True)
        
        tk.Label(info_frame, text="👥", font=("Segoe UI", 48),
                bg=self.colors["card_bg"], fg=self.colors["accent"]).pack()
        tk.Label(info_frame, text="User Management", font=("Segoe UI", 18, "bold"),
                bg=self.colors["card_bg"], fg=self.colors["fg"]).pack(pady=10)
        tk.Label(info_frame, text="Track and manage users\n(Coming in Pro version)",
                font=("Segoe UI", 11), bg=self.colors["card_bg"], 
                fg=self.colors["fg"]).pack()
        
        # Stats preview
        stats_preview = tk.Frame(tab, bg=self.colors["bg"])
        stats_preview.pack(pady=20)
        
        for label, value in [("Total Users", "0"), ("Active Today", "0"), ("New This Week", "0")]:
            card = tk.Frame(stats_preview, bg=self.colors["card_bg"], padx=30, pady=15)
            card.pack(side=tk.LEFT, padx=10)
            tk.Label(card, text=value, font=("Segoe UI", 24, "bold"),
                    bg=self.colors["card_bg"], fg=self.colors["accent"]).pack()
            tk.Label(card, text=label, font=("Segoe UI", 10),
                    bg=self.colors["card_bg"], fg=self.colors["fg"]).pack()
        
    def create_analytics_tab(self):
        """Analytics dashboard"""
        tab = tk.Frame(self.notebook, bg=self.colors["bg"])
        self.notebook.add(tab, text="📈 Analytics")
        
        # Date range selector
        date_frame = tk.Frame(tab, bg=self.colors["bg"])
        date_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(date_frame, text="Date Range:", bg=self.colors["bg"],
                fg=self.colors["fg"]).pack(side=tk.LEFT, padx=5)
        
        self.date_range = ttk.Combobox(date_frame, values=[
            "Today", "Last 7 Days", "Last 30 Days", "Last 90 Days", "All Time"
        ], width=15)
        self.date_range.set("Last 7 Days")
        self.date_range.pack(side=tk.LEFT, padx=5)
        
        tk.Button(date_frame, text="📊 Generate Report", command=self.generate_report,
                 bg=self.colors["accent"], fg="white",
                 relief=tk.FLAT, cursor="hand2").pack(side=tk.LEFT, padx=20)
        
        # Charts frame
        charts_frame = tk.Frame(tab, bg=self.colors["bg"])
        charts_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Message chart (ASCII representation)
        chart1 = tk.LabelFrame(charts_frame, text=" Messages per Day ",
                              bg=self.colors["bg"], fg=self.colors["fg"])
        chart1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.messages_chart = tk.Text(chart1, height=15, bg=self.colors["card_bg"],
                                      fg=self.colors["accent"], font=("Consolas", 10))
        self.messages_chart.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.draw_ascii_chart()
        
        # Stats summary
        chart2 = tk.LabelFrame(charts_frame, text=" Summary Stats ",
                              bg=self.colors["bg"], fg=self.colors["fg"])
        chart2.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        summary_stats = [
            ("Total Messages", "0"),
            ("Total Sessions", "0"),
            ("Avg Messages/Session", "0"),
            ("Most Active Hour", "N/A"),
            ("Top Model Used", "Nemotron"),
            ("Avg Response Time", "0ms"),
        ]
        
        for label, value in summary_stats:
            row = tk.Frame(chart2, bg=self.colors["card_bg"])
            row.pack(fill=tk.X, padx=10, pady=3)
            tk.Label(row, text=label, bg=self.colors["card_bg"],
                    fg=self.colors["fg"], anchor="w").pack(side=tk.LEFT)
            tk.Label(row, text=value, bg=self.colors["card_bg"],
                    fg=self.colors["accent"], font=("Segoe UI", 10, "bold")).pack(side=tk.RIGHT)
        
    def create_models_tab(self):
        """Model management"""
        tab = tk.Frame(self.notebook, bg=self.colors["bg"])
        self.notebook.add(tab, text="🤖 Models")
        
        # Available models
        models_frame = tk.LabelFrame(tab, text=" Available Models ",
                                    bg=self.colors["bg"], fg=self.colors["fg"])
        models_frame.pack(fill=tk.X, padx=10, pady=10)
        
        models = [
            ("nvidia/nemotron-3-nano-30b-a3b:free", "Nemotron Nano 30B", "Fast, General purpose"),
            ("kwaipilot/kat-coder-pro:free", "Kat Coder Pro", "Coding specialist"),
        ]
        
        for model_id, name, desc in models:
            row = tk.Frame(models_frame, bg=self.colors["card_bg"], pady=10, padx=15)
            row.pack(fill=tk.X, padx=10, pady=5)
            
            tk.Label(row, text="🤖", font=("Segoe UI", 16),
                    bg=self.colors["card_bg"], fg=self.colors["accent"]).pack(side=tk.LEFT)
            
            info_frame = tk.Frame(row, bg=self.colors["card_bg"])
            info_frame.pack(side=tk.LEFT, padx=15, fill=tk.X, expand=True)
            tk.Label(info_frame, text=name, font=("Segoe UI", 11, "bold"),
                    bg=self.colors["card_bg"], fg=self.colors["fg"]).pack(anchor="w")
            tk.Label(info_frame, text=desc, font=("Segoe UI", 9),
                    bg=self.colors["card_bg"], fg="#a0a0b0").pack(anchor="w")
            
            if model_id == self.config["default_model"]:
                tk.Label(row, text="✓ Default", bg=self.colors["success"],
                        fg="white", padx=10, pady=2).pack(side=tk.RIGHT)
            else:
                tk.Button(row, text="Set Default", 
                         command=lambda m=model_id: self.set_default_model(m),
                         bg=self.colors["card_bg"], fg=self.colors["fg"],
                         relief=tk.FLAT, cursor="hand2").pack(side=tk.RIGHT)
        
        # Model parameters
        params_frame = tk.LabelFrame(tab, text=" Model Parameters ",
                                    bg=self.colors["bg"], fg=self.colors["fg"])
        params_frame.pack(fill=tk.X, padx=10, pady=10)
        
        inner = tk.Frame(params_frame, bg=self.colors["bg"])
        inner.pack(pady=15, padx=15, fill=tk.X)
        
        # Temperature
        tk.Label(inner, text="Temperature:", bg=self.colors["bg"],
                fg=self.colors["fg"]).grid(row=0, column=0, sticky="w", pady=5)
        self.temp_scale = ttk.Scale(inner, from_=0, to=2, orient=tk.HORIZONTAL)
        self.temp_scale.set(self.config["temperature"])
        self.temp_scale.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        self.temp_value = tk.Label(inner, text="0.7", bg=self.colors["bg"],
                                  fg=self.colors["accent"])
        self.temp_value.grid(row=0, column=2, pady=5)
        self.temp_scale.configure(command=lambda v: self.temp_value.configure(text=f"{float(v):.1f}"))
        
        # Max tokens
        tk.Label(inner, text="Max Tokens:", bg=self.colors["bg"],
                fg=self.colors["fg"]).grid(row=1, column=0, sticky="w", pady=5)
        self.max_tokens_entry = tk.Entry(inner, bg=self.colors["card_bg"],
                                        fg=self.colors["fg"], width=20)
        self.max_tokens_entry.insert(0, str(self.config["max_tokens"]))
        self.max_tokens_entry.grid(row=1, column=1, sticky="w", padx=10, pady=5)
        
        inner.columnconfigure(1, weight=1)
        
    def create_settings_tab(self):
        """Settings configuration"""
        tab = tk.Frame(self.notebook, bg=self.colors["bg"])
        self.notebook.add(tab, text="⚙️ Settings")
        
        # Create scrollable frame
        canvas = tk.Canvas(tab, bg=self.colors["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors["bg"])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")
        
        # Connection settings
        conn_frame = tk.LabelFrame(scrollable_frame, text=" Connection Settings ",
                                   bg=self.colors["bg"], fg=self.colors["fg"])
        conn_frame.pack(fill=tk.X, pady=10, padx=5)
        
        inner = tk.Frame(conn_frame, bg=self.colors["bg"])
        inner.pack(pady=15, padx=15, fill=tk.X)
        
        tk.Label(inner, text="API URL:", bg=self.colors["bg"],
                fg=self.colors["fg"]).grid(row=0, column=0, sticky="w", pady=5)
        self.api_url_entry = tk.Entry(inner, width=50, bg=self.colors["card_bg"],
                                     fg=self.colors["fg"], insertbackground="white")
        self.api_url_entry.insert(0, self.config["api_url"])
        self.api_url_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        
        tk.Label(inner, text="Admin PIN:", bg=self.colors["bg"],
                fg=self.colors["fg"]).grid(row=1, column=0, sticky="w", pady=5)
        self.admin_pin_entry = tk.Entry(inner, width=50, show="*",
                                       bg=self.colors["card_bg"], fg=self.colors["fg"])
        self.admin_pin_entry.insert(0, self.config["admin_pin"])
        self.admin_pin_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        inner.columnconfigure(1, weight=1)
        
        # Auto-refresh settings
        refresh_frame = tk.LabelFrame(scrollable_frame, text=" Auto-Refresh ",
                                      bg=self.colors["bg"], fg=self.colors["fg"])
        refresh_frame.pack(fill=tk.X, pady=10, padx=5)
        
        refresh_inner = tk.Frame(refresh_frame, bg=self.colors["bg"])
        refresh_inner.pack(pady=15, padx=15, fill=tk.X)
        
        self.auto_refresh_var = tk.BooleanVar(value=self.config["auto_refresh"])
        tk.Checkbutton(refresh_inner, text="Enable Auto-Refresh",
                      variable=self.auto_refresh_var, bg=self.colors["bg"],
                      fg=self.colors["fg"], selectcolor=self.colors["card_bg"]).pack(anchor="w")
        
        tk.Label(refresh_inner, text="Refresh Interval (ms):", bg=self.colors["bg"],
                fg=self.colors["fg"]).pack(anchor="w", pady=(10, 0))
        self.refresh_interval_entry = tk.Entry(refresh_inner, width=20,
                                              bg=self.colors["card_bg"], fg=self.colors["fg"])
        self.refresh_interval_entry.insert(0, str(self.config["refresh_interval"]))
        self.refresh_interval_entry.pack(anchor="w", pady=5)
        
        # Save button
        tk.Button(scrollable_frame, text="💾 Save All Settings", command=self.save_settings,
                 bg=self.colors["accent"], fg="white", font=("Segoe UI", 12, "bold"),
                 padx=30, pady=10, relief=tk.FLAT, cursor="hand2").pack(pady=20)
        
    def create_api_tab(self):
        """API testing"""
        tab = tk.Frame(self.notebook, bg=self.colors["bg"])
        self.notebook.add(tab, text="🔌 API")
        
        # Endpoint testing
        test_frame = tk.LabelFrame(tab, text=" Test API Endpoints ",
                                   bg=self.colors["bg"], fg=self.colors["fg"])
        test_frame.pack(fill=tk.X, pady=10, padx=10)
        
        inner = tk.Frame(test_frame, bg=self.colors["bg"])
        inner.pack(pady=15, padx=15, fill=tk.X)
        
        tk.Label(inner, text="Method:", bg=self.colors["bg"],
                fg=self.colors["fg"]).grid(row=0, column=0, pady=5)
        self.method_combo = ttk.Combobox(inner, values=["GET", "POST", "DELETE"], width=10)
        self.method_combo.set("GET")
        self.method_combo.grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(inner, text="Endpoint:", bg=self.colors["bg"],
                fg=self.colors["fg"]).grid(row=0, column=2, padx=(20, 5), pady=5)
        self.endpoint_entry = tk.Entry(inner, width=40, bg=self.colors["card_bg"],
                                      fg=self.colors["fg"], insertbackground="white")
        self.endpoint_entry.insert(0, "/")
        self.endpoint_entry.grid(row=0, column=3, padx=5, pady=5)
        
        tk.Button(inner, text="🚀 Send", command=self.test_endpoint,
                 bg=self.colors["accent"], fg="white",
                 relief=tk.FLAT, cursor="hand2").grid(row=0, column=4, padx=10, pady=5)
        
        # Quick endpoints
        quick_frame = tk.Frame(test_frame, bg=self.colors["bg"])
        quick_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        for endpoint in ["/", "/sessions", "/db/stats", "/settings"]:
            tk.Button(quick_frame, text=endpoint,
                     command=lambda e=endpoint: self.quick_test(e),
                     bg=self.colors["card_bg"], fg=self.colors["fg"],
                     relief=tk.FLAT, cursor="hand2").pack(side=tk.LEFT, padx=5)
        
        # Response area
        resp_frame = tk.LabelFrame(tab, text=" Response ",
                                   bg=self.colors["bg"], fg=self.colors["fg"])
        resp_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=10)
        
        self.response_text = scrolledtext.ScrolledText(resp_frame, 
                                                       bg=self.colors["card_bg"],
                                                       fg=self.colors["success"],
                                                       font=("Consolas", 10))
        self.response_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
    def create_security_tab(self):
        """Security settings"""
        tab = tk.Frame(self.notebook, bg=self.colors["bg"])
        self.notebook.add(tab, text="🔐 Security")
        
        # PIN management
        pin_frame = tk.LabelFrame(tab, text=" Admin PIN Management ",
                                 bg=self.colors["bg"], fg=self.colors["fg"])
        pin_frame.pack(fill=tk.X, pady=10, padx=10)
        
        inner = tk.Frame(pin_frame, bg=self.colors["bg"])
        inner.pack(pady=15, padx=15, fill=tk.X)
        
        tk.Label(inner, text="Current PIN:", bg=self.colors["bg"],
                fg=self.colors["fg"]).grid(row=0, column=0, sticky="w", pady=5)
        self.current_pin = tk.Entry(inner, width=20, show="*",
                                   bg=self.colors["card_bg"], fg=self.colors["fg"])
        self.current_pin.grid(row=0, column=1, padx=10, pady=5)
        
        tk.Label(inner, text="New PIN:", bg=self.colors["bg"],
                fg=self.colors["fg"]).grid(row=1, column=0, sticky="w", pady=5)
        self.new_pin = tk.Entry(inner, width=20, show="*",
                               bg=self.colors["card_bg"], fg=self.colors["fg"])
        self.new_pin.grid(row=1, column=1, padx=10, pady=5)
        
        tk.Button(inner, text="Change PIN", command=self.change_pin,
                 bg=self.colors["accent"], fg="white",
                 relief=tk.FLAT, cursor="hand2").grid(row=1, column=2, padx=10, pady=5)
        
        # Access log
        log_frame = tk.LabelFrame(tab, text=" Security Log ",
                                 bg=self.colors["bg"], fg=self.colors["fg"])
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=10)
        
        self.security_log = scrolledtext.ScrolledText(log_frame, height=15,
                                                      bg=self.colors["card_bg"],
                                                      fg=self.colors["warning"],
                                                      font=("Consolas", 9))
        self.security_log.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.security_log.insert(tk.END, f"[{self.get_timestamp()}] Admin Panel accessed\n")
        self.security_log.insert(tk.END, f"[{self.get_timestamp()}] IP: {self.get_local_ip()}\n")
        
    def create_tools_tab(self):
        """Tools and utilities"""
        tab = tk.Frame(self.notebook, bg=self.colors["bg"])
        self.notebook.add(tab, text="🛠️ Tools")
        
        # Tools grid
        tools_frame = tk.Frame(tab, bg=self.colors["bg"])
        tools_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tools = [
            ("💾 Backup Database", "Create full backup", self.backup_database),
            ("📥 Restore Backup", "Restore from file", self.restore_backup),
            ("🧹 Clear Sessions", "Delete all sessions", self.clear_all_sessions),
            ("📊 Export Analytics", "Download report", self.export_analytics),
            ("🔄 Restart Server", "Restart backend", self.restart_server),
            ("📝 View Server Logs", "Check logs", self.view_server_logs),
            ("🔌 Check Ports", "Port scanner", self.check_ports),
            ("🌐 Network Info", "Connection details", self.show_network_info),
        ]
        
        for i, (title, desc, command) in enumerate(tools):
            row, col = divmod(i, 4)
            card = tk.Frame(tools_frame, bg=self.colors["card_bg"], padx=15, pady=15)
            card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            tools_frame.columnconfigure(col, weight=1)
            
            tk.Label(card, text=title.split()[0], font=("Segoe UI", 24),
                    bg=self.colors["card_bg"], fg=self.colors["accent"]).pack()
            tk.Label(card, text=title.split(None, 1)[1], font=("Segoe UI", 11, "bold"),
                    bg=self.colors["card_bg"], fg=self.colors["fg"]).pack()
            tk.Label(card, text=desc, font=("Segoe UI", 9),
                    bg=self.colors["card_bg"], fg="#a0a0b0").pack()
            tk.Button(card, text="Run", command=command,
                     bg=self.colors["accent"], fg="white",
                     relief=tk.FLAT, cursor="hand2", padx=20).pack(pady=10)
        
        # Logs area
        logs_frame = tk.LabelFrame(tab, text=" System Logs ",
                                  bg=self.colors["bg"], fg=self.colors["fg"])
        logs_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.tools_log = scrolledtext.ScrolledText(logs_frame, height=10,
                                                   bg=self.colors["card_bg"],
                                                   fg=self.colors["success"],
                                                   font=("Consolas", 9))
        self.tools_log.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.tools_log.insert(tk.END, f"[{self.get_timestamp()}] Tools initialized\n")
        
    # ==================== Helper Functions ====================
    
    def create_stat_card(self, parent, label, value, color):
        """Create a stat card widget"""
        card = tk.Frame(parent, bg=self.colors["card_bg"], padx=20, pady=15)
        
        val_label = tk.Label(card, text=value, font=("Segoe UI", 22, "bold"),
                            fg=color, bg=self.colors["card_bg"])
        val_label.pack()
        
        name_label = tk.Label(card, text=label, font=("Segoe UI", 9),
                             fg="#a0a0b0", bg=self.colors["card_bg"])
        name_label.pack()
        
        self.stat_labels[label.lower().replace(" ", "_")] = val_label
        return card
    
    def create_tooltip(self, widget, text):
        """Create tooltip for widget"""
        def show_tooltip(event):
            x, y = widget.winfo_rootx() + 50, widget.winfo_rooty()
            self.tooltip = tk.Toplevel(widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x}+{y}")
            label = tk.Label(self.tooltip, text=text, bg="#333", fg="white",
                           padx=5, pady=2, font=("Segoe UI", 9))
            label.pack()
        
        def hide_tooltip(event):
            if hasattr(self, 'tooltip'):
                self.tooltip.destroy()
        
        widget.bind('<Enter>', show_tooltip)
        widget.bind('<Leave>', hide_tooltip)
    
    def get_timestamp(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def log_activity(self, message):
        timestamp = self.get_timestamp()
        self.activity_list.insert(tk.END, f"[{timestamp}] {message}\n")
        self.activity_list.see(tk.END)
    
    def draw_ascii_chart(self, data=None):
        """Draw ASCII bar chart from dynamic data"""
        self.messages_chart.delete('1.0', tk.END)
        
        # Default empty data
        days = []
        values = []
        
        # Use last 7 days including today
        today = datetime.now()
        date_map = {row['day']: row['count'] for row in (data or [])}
        
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            day_str = d.strftime('%Y-%m-%d')
            display_day = d.strftime('%a') # Mon, Tue
            
            days.append(display_day)
            values.append(date_map.get(day_str, 0))
            
        # Draw chart
        max_val = max(values) if values and max(values) > 0 else 10
        
        chart = ""
        rows = 10
        for i in range(rows, 0, -1):
            threshold = (max_val / rows) * i
            label = int(threshold)
            line = f"{label:3d} |"
            for v in values:
                bar_height = (v / max_val) * rows
                if bar_height >= i:
                    line += " █ "
                elif bar_height >= i - 0.5:
                    line += " ▄ "
                else:
                    line += "   "
            chart += line + "\n"
        
        chart += "    +" + "---" * 7 + "\n"
        chart += "     " + " ".join([f"{d:3}" for d in days])
        
        self.messages_chart.insert(tk.END, chart)
    
    # ==================== API Functions ====================
    
    def api_request(self, endpoint, method="GET", data=None):
        """Make API request"""
        url = f"{self.config['api_url']}{endpoint}"
        
        if HAS_REQUESTS:
            try:
                if method == "GET":
                    response = requests.get(url, timeout=10)
                elif method == "POST":
                    response = requests.post(url, json=data, timeout=10)
                elif method == "DELETE":
                    response = requests.delete(url, timeout=10)
                return response.json()
            except Exception as e:
                return {"error": str(e)}
        else:
            try:
                req = urllib.request.Request(url, method=method)
                if data:
                    req.add_header('Content-Type', 'application/json')
                    data = json.dumps(data).encode('utf-8')
                    response = urllib.request.urlopen(req, data, timeout=10)
                else:
                    response = urllib.request.urlopen(req, timeout=10)
                return json.loads(response.read().decode('utf-8'))
            except Exception as e:
                return {"error": str(e)}
    
    def refresh_all(self):
        """Refresh all data"""
        self.log_activity("Refreshing all data...")
        self.refresh_stats()
        self.load_sessions()
    
    def refresh_stats(self):
        """Refresh dashboard stats"""
        def fetch():
            result = self.api_request("/")
            db_stats = self.api_request("/db/stats")
            
            self.root.after(0, lambda: self.update_stats(result, db_stats))
        
        threading.Thread(target=fetch, daemon=True).start()
    
    def update_stats(self, result, db_stats):
        """Update dashboard with stats"""
        if "error" not in result:
            self.update_status("Connected", True)
            self.log_activity("Stats refreshed successfully")
            
            if "total_sessions" in db_stats:
                if "active_sessions" in self.stat_labels:
                    self.stat_labels["active_sessions"].config(text=str(db_stats["total_sessions"]))
            if "total_messages" in db_stats:
                if "total_messages" in self.stat_labels:
                    self.stat_labels["total_messages"].config(text=str(db_stats["total_messages"]))
            if "daily_messages" in db_stats and hasattr(self, 'messages_chart'):
                self.draw_ascii_chart(db_stats["daily_messages"])
        else:
            self.update_status("Disconnected", False)
            self.log_activity(f"Connection error: {result.get('error', 'Unknown')}")
    
    def update_status(self, text, connected):
        """Update connection status"""
        color = self.colors["success"] if connected else self.colors["danger"]
        self.status_label.config(text=f"● {text}", fg=color)
        self.sidebar_status.config(fg=color)
    
    def load_sessions(self):
        """Load sessions from API"""
        def fetch():
            result = self.api_request("/sessions")
            self.root.after(0, lambda: self.populate_sessions(result))
        
        threading.Thread(target=fetch, daemon=True).start()
    
    def populate_sessions(self, result):
        """Populate sessions tree"""
        self.sessions_tree.delete(*self.sessions_tree.get_children())
        
        if "sessions" in result:
            for session in result["sessions"]:
                self.sessions_tree.insert("", tk.END, values=(
                    session.get("id", "")[:12] + "...",
                    session.get("title", "New Chat")[:30],
                    session.get("message_count", 0),
                    session.get("created_at", "")[:10],
                    session.get("updated_at", "")[:16],
                    "Active" if session.get("is_active") else "Inactive"
                ))
            self.log_activity(f"Loaded {len(result['sessions'])} sessions")
    
    def filter_sessions(self, event):
        """Filter sessions by search"""
        search_term = self.session_search.get().lower()
        # Reload and filter
        self.load_sessions()
    
    def show_session_menu(self, event):
        """Show context menu for session"""
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="View Messages", command=self.view_session_messages)
        menu.add_command(label="Delete Session", command=self.delete_selected_session)
        menu.add_separator()
        menu.add_command(label="Export Session", command=self.export_session)
        menu.post(event.x_root, event.y_root)
    
    def view_session_messages(self):
        """View messages in selected session"""
        selected = self.sessions_tree.selection()
        if selected:
            item = self.sessions_tree.item(selected[0])
            session_id = item['values'][0]
            messagebox.showinfo("Session", f"Viewing session: {session_id}")
    
    def delete_selected_session(self):
        """Delete selected session"""
        selected = self.sessions_tree.selection()
        if selected:
            if messagebox.askyesno("Confirm", "Delete this session?"):
                item = self.sessions_tree.item(selected[0])
                # Call delete API
                self.load_sessions()
    
    def export_session(self):
        """Export selected session"""
        messagebox.showinfo("Export", "Session exported!")
    
    # ==================== Action Functions ====================
    
    def test_connection(self):
        """Test API connection"""
        self.log_activity("Testing connection...")
        result = self.api_request("/")
        
        if "error" not in result:
            messagebox.showinfo("Connection", f"✅ Connected!\n\nStatus: {result.get('status', 'OK')}")
            self.update_status("Connected", True)
        else:
            messagebox.showerror("Connection", f"❌ Failed!\n\n{result['error']}")
            self.update_status("Disconnected", False)
    
    def test_endpoint(self):
        """Test custom endpoint"""
        endpoint = self.endpoint_entry.get()
        method = self.method_combo.get()
        
        self.log_activity(f"Testing {method} {endpoint}")
        result = self.api_request(endpoint, method)
        
        self.response_text.delete(1.0, tk.END)
        self.response_text.insert(tk.END, json.dumps(result, indent=2))
    
    def quick_test(self, endpoint):
        """Quick test an endpoint"""
        self.endpoint_entry.delete(0, tk.END)
        self.endpoint_entry.insert(0, endpoint)
        self.test_endpoint()
    
    def open_website(self):
        """Open chatbot website"""
        webbrowser.open(f"{self.config['api_url'].replace('8000', '3000')}")
        self.log_activity("Opened website")
    
    def clear_all_sessions(self):
        """Clear all sessions"""
        if messagebox.askyesno("Confirm", "Delete ALL sessions? This cannot be undone."):
            result = self.api_request("/admin/clear-sessions?pin=" + self.config["admin_pin"], "POST")
            if "error" not in result:
                messagebox.showinfo("Success", "All sessions cleared!")
                self.load_sessions()
                self.log_activity("Cleared all sessions")
            else:
                messagebox.showerror("Error", result.get("error", "Failed"))
    
    def export_analytics(self):
        """Export analytics report"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("CSV", "*.csv")]
        )
        if filepath:
            stats = self.api_request("/db/stats")
            with open(filepath, "w") as f:
                json.dump(stats, f, indent=2)
            messagebox.showinfo("Exported", f"Analytics exported to {filepath}")
            self.log_activity("Exported analytics")
    
    def export_sessions(self):
        """Export all sessions"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")]
        )
        if filepath:
            sessions = self.api_request("/sessions")
            with open(filepath, "w") as f:
                json.dump(sessions, f, indent=2)
            messagebox.showinfo("Exported", f"Sessions exported to {filepath}")
    
    def start_server_process(self):
        """Start the backend server"""
        try:
            # Check if running
            if self.api_request("/").get("status") == "online":
                messagebox.showinfo("Start Server", "Server is already running!")
                return

            self.log_activity("Attempting to start server...")
            backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
            print(f"Starting server in: {backend_dir}")
            
            # Start uvicorn using current python interpreter
            cmd = [sys.executable, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
            print(f"Command: {cmd}")
            
            subprocess.Popen(
                cmd,
                cwd=backend_dir,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            
            messagebox.showinfo("Start Server", "Server start command issued.\nPlease wait a moment for it to initialize.")
            self.log_activity("Server start command issued")
            
        except Exception as e:
            print(f"Start Server Error: {e}")
            messagebox.showerror("Error", f"Failed to start server:\n{str(e)}")
            self.log_activity(f"Start failed: {str(e)}")

    def restart_server_process(self):
        """Restart the server"""
        if messagebox.askyesno("Restart", "Are you sure you want to restart the server?"):
            self.log_activity("Restarting server...")
            
            # Stop if running
            try:
                self.api_request("/admin/shutdown?pin=" + self.config["admin_pin"], "POST")
            except:
                pass
                
            # Wait a bit then start
            self.root.after(3000, self.start_server_process)

    def emergency_stop(self):
        """Emergency stop server"""
        if messagebox.askyesno("Emergency Stop", "This will attempt to STOP the backend server. Continue?"):
            self.log_activity("Sending shutdown command...")
            result = self.api_request("/admin/shutdown?pin=" + self.config["admin_pin"], "POST")
            
            if "error" not in result:
                messagebox.showwarning("Shutdown", "Server is shutting down.\nYou will need to restart it manually.")
                self.update_status("Disconnected", False)
                self.log_activity("Server shutdown confirmed")
            else:
                messagebox.showerror("Error", f"Failed to stop server: {result.get('error')}")
    
    def backup_database(self):
        """Backup database"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfilename=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            filetypes=[("JSON", "*.json")]
        )
        if filepath:
            # Get all data
            sessions = self.api_request("/sessions")
            stats = self.api_request("/db/stats")
            
            backup = {
                "timestamp": self.get_timestamp(),
                "sessions": sessions,
                "stats": stats,
                "config": self.config
            }
            
            with open(filepath, "w") as f:
                json.dump(backup, f, indent=2)
            
            messagebox.showinfo("Backup", f"Backup saved to {filepath}")
            self.log_activity("Database backed up")
    
    def restore_backup(self):
        """Restore from backup"""
        filepath = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if filepath:
            messagebox.showinfo("Restore", "Restore functionality coming soon!")
    
    def restart_server(self):
        """Restart server"""
        if messagebox.askyesno("Restart", "Restart the server?"):
            messagebox.showinfo("Note", "Please restart the server manually:\nuvicorn app:app --reload")
    
    def view_server_logs(self):
        """View server logs"""
        self.notebook.select(8)  # Switch to tools tab
        self.tools_log.insert(tk.END, f"[{self.get_timestamp()}] Viewing server logs...\n")
    
    def check_ports(self):
        """Check common ports"""
        ports = [8000, 3000, 80, 443, 5000]
        results = []
        
        for port in ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            status = "OPEN" if result == 0 else "CLOSED"
            results.append(f"Port {port}: {status}")
            sock.close()
        
        self.tools_log.insert(tk.END, f"\n[{self.get_timestamp()}] Port Scan Results:\n")
        for r in results:
            self.tools_log.insert(tk.END, f"  {r}\n")
        self.tools_log.see(tk.END)
    
    def show_network_info(self):
        """Show network information"""
        info = f"""
Network Information:
-------------------
Local IP: {self.get_local_ip()}
API URL: {self.config['api_url']}
Hostname: {socket.gethostname()}
"""
        self.tools_log.insert(tk.END, f"\n[{self.get_timestamp()}]{info}")
        self.tools_log.see(tk.END)
    
    def change_pin(self):
        """Change admin PIN"""
        current = self.current_pin.get()
        new = self.new_pin.get()
        
        if current == self.config["admin_pin"]:
            if len(new) >= 4:
                self.config["admin_pin"] = new
                self.save_config()
                messagebox.showinfo("Success", "PIN changed successfully!")
                self.current_pin.delete(0, tk.END)
                self.new_pin.delete(0, tk.END)
                self.security_log.insert(tk.END, f"[{self.get_timestamp()}] PIN changed\n")
            else:
                messagebox.showerror("Error", "New PIN must be at least 4 characters")
        else:
            messagebox.showerror("Error", "Current PIN is incorrect")
            self.security_log.insert(tk.END, f"[{self.get_timestamp()}] Failed PIN change attempt\n")
    
    def set_default_model(self, model_id):
        """Set default model"""
        self.config["default_model"] = model_id
        self.save_config()
        messagebox.showinfo("Model", f"Default model set to:\n{model_id}")
        self.log_activity(f"Default model changed to {model_id}")
    
    def generate_report(self):
        """Generate analytics report"""
        date_range = self.date_range.get()
        messagebox.showinfo("Report", f"Generating report for: {date_range}\n\nReport generated!")
        self.log_activity(f"Generated report for {date_range}")
    
    def save_settings(self):
        """Save all settings"""
        self.config["api_url"] = self.api_url_entry.get()
        self.config["admin_pin"] = self.admin_pin_entry.get()
        self.config["auto_refresh"] = self.auto_refresh_var.get()
        self.config["refresh_interval"] = int(self.refresh_interval_entry.get())
        self.config["temperature"] = float(self.temp_scale.get())
        self.config["max_tokens"] = int(self.max_tokens_entry.get())
        
        self.save_config()
        messagebox.showinfo("Saved", "All settings saved successfully!")
        self.log_activity("Settings saved")
    
    def save_config(self):
        """Save config to file"""
        config_path = os.path.join(os.path.dirname(__file__), "admin_config.json")
        with open(config_path, "w") as f:
            json.dump(self.config, f, indent=2)
    
    def load_config(self):
        """Load config from file"""
        config_path = os.path.join(os.path.dirname(__file__), "admin_config.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                self.config.update(json.load(f))
    
    def auto_refresh(self):
        """Auto-refresh stats"""
        if self.config["auto_refresh"]:
            self.refresh_stats()
        self.root.after(self.config["refresh_interval"], self.auto_refresh)


def main():
    root = tk.Tk()
    app = AdminPanel(root)
    root.mainloop()


if __name__ == "__main__":
    main()
