import customtkinter as ctk
import pyodbc
from PIL import Image
import os
import shutil
from tkinter import messagebox, filedialog
from tkinter import ttk
import datetime
import webbrowser

# ==========================================
# 1. SQL Queries Repository
# ==========================================
class SQLQueries:
    GET_ALL_WATCHES = "SELECT * FROM vw_WatchFullDetails"
    
    GET_DASHBOARD_STATS = """
        SELECT 
            COUNT(*) as TotalWatches,
            ISNULL(SUM(CASE WHEN Status = 'Available' THEN PurchasePrice ELSE 0 END), 0) as TotalValue,
            SUM(CASE WHEN Status = 'Sold' THEN 1 ELSE 0 END) as SoldWatches
        FROM Watch
    """
    
    INSERT_WATCH = """
        INSERT INTO Watch (SerialNumber, ModelName, ProductionYear, WatchImage, PurchasePrice, Status, BrandID, MovementID) 
        VALUES (?, ?, ?, ?, ?, 'Available', ?, ?)
    """
    
    GET_REPORTS = "SELECT * FROM AuthenticationReport"

    @staticmethod
    def build_insert(table_name, columns_list):
        cols_joined = ", ".join(columns_list)
        placeholders = ", ".join(["?"] * len(columns_list))
        return f"INSERT INTO {table_name} ({cols_joined}) VALUES ({placeholders})"

    @staticmethod
    def build_update(table_name, columns_list, pk_col):
        set_clause = ", ".join([f"{col} = ?" for col in columns_list])
        return f"UPDATE {table_name} SET {set_clause} WHERE {pk_col} = ?"

    @staticmethod
    def build_delete(table_name, pk_col):
        return f"DELETE FROM {table_name} WHERE {pk_col} = ?"

    @staticmethod
    def build_select_all(table_name):
        return f"SELECT * FROM {table_name}"

# ==========================================
# 2. Database Connection & Operations Layer
# ==========================================
class DatabaseManager:
    def __init__(self):
        self.server = r'.\WORK'
        self.database = 'MNU_Watches'

    def connect(self):
        try:
            return pyodbc.connect(
                r'DRIVER={SQL Server};'
                f'SERVER={self.server};'
                f'DATABASE={self.database};'
                r'Trusted_Connection=yes;'
            )
        except pyodbc.Error as e:
            print("Database Error:", e)
            return None

    def get_watches_full(self):
        conn = self.connect()
        if not conn: 
            return []
        cursor = conn.cursor()
        cursor.execute(SQLQueries.GET_ALL_WATCHES)
        columns = [column[0] for column in cursor.description]
        data = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return data

    def get_dashboard_stats(self):
        conn = self.connect()
        if not conn: 
            return {"total": 0, "value": 0, "sold": 0}
        cursor = conn.cursor()
        cursor.execute(SQLQueries.GET_DASHBOARD_STATS)
        row = cursor.fetchone()
        conn.close()
        return {"total": row[0] or 0, "value": row[1] or 0, "sold": row[2] or 0}

    def add_watch(self, serial, model, year, image_path, price, brand_id, move_id):
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute(SQLQueries.INSERT_WATCH, (serial, model, year, image_path, price, brand_id, move_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print("Insert Watch Error:", e)
            return False

    def insert_generic(self, table_name, data_dict):
        try:
            conn = self.connect()
            cursor = conn.cursor()
            columns_list = list(data_dict.keys())
            values = list(data_dict.values())
            query = SQLQueries.build_insert(table_name, columns_list)
            cursor.execute(query, values)
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Generic Insert Error for {table_name}:", e)
            return False

    def update_generic(self, table_name, pk_col, pk_val, data_dict):
        try:
            conn = self.connect()
            cursor = conn.cursor()
            columns_list = list(data_dict.keys())
            values = list(data_dict.values())
            values.append(pk_val)
            query = SQLQueries.build_update(table_name, columns_list, pk_col)
            cursor.execute(query, values)
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Update Error:", e)
            return False

    def delete_generic(self, table_name, pk_col, pk_val):
        try:
            conn = self.connect()
            cursor = conn.cursor()
            query = SQLQueries.build_delete(table_name, pk_col)
            cursor.execute(query, (pk_val,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Delete Error:", e)
            return False

    def get_table_data(self, table_name):
        conn = self.connect()
        if not conn: 
            return [], []
        try:
            cursor = conn.cursor()
            query = SQLQueries.build_select_all(table_name)
            cursor.execute(query)
            columns = [column[0] for column in cursor.description]
            data = cursor.fetchall()
            conn.close()
            return columns, data
        except Exception as e:
            print(f"Error fetching {table_name}:", e)
            return [], []

    def update_watch_status(self, watch_id, new_status):
        return self.update_generic("Watch", "WatchID", watch_id, {"Status": new_status})

    def get_reports(self):
        conn = self.connect()
        if not conn: 
            return []
        cursor = conn.cursor()
        cursor.execute(SQLQueries.GET_REPORTS)
        data = cursor.fetchall()
        conn.close()
        return data

# ==========================================
# 3. GUI Layer
# ==========================================
class WatchApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.selected_image_path = None
        
        self.filter_visible = False
        self.current_max_price = 500000
        self.current_selected_brands = []
        self.current_filtered_watches = None
        
        self.table_schemas = {
            "Brand": ["Name", "Country", "FoundedYear"],
            "Movement": ["CaliberName", "VibrationsPerHour", "BrandID"],
            "Feature": ["FeatureName"],
            "Part": ["WatchID", "PartName", "Material", "Condition", "OriginalityStatus"],
            "AuctionRecord": ["AuctionHouse", "AuctionDate", "SalePrice", "CommissionFee", "WatchID"],
            "AuthenticationReport": ["AuthenticatorName", "ResultStatus", "ReportDate", "WatchID"]
        }
        self.current_dynamic_entries = {}
        self.current_report_data = None 

        self.title("MNU Watches - Enterprise Management System")
        self.geometry("1400x900")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.setup_styles()
        self.setup_sidebar()
        self.setup_main_frames()
        self.show_dashboard()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#2b2b2b", foreground="white", rowheight=30, fieldbackground="#2b2b2b", borderwidth=0)
        style.map('Treeview', background=[('selected', '#4a4a4a')])
        style.configure("Treeview.Heading", background="#1f1f1f", foreground="#deff9a", relief="flat", font=("Arial", 12, "bold"))
        style.map("Treeview.Heading", background=[('active', '#333333')])

    def setup_sidebar(self):
        self.sidebar = ctk.CTkScrollableFrame(self, width=220, corner_radius=0, fg_color="#111")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.logo = ctk.CTkLabel(self.sidebar, text="MNU\nWATCHES", font=ctk.CTkFont(size=28, weight="bold"), text_color="#deff9a")
        self.logo.pack(pady=40)

        # 1. Main Functions
        self.btn_dash = ctk.CTkButton(self.sidebar, text="🏠 Dashboard", height=40, font=ctk.CTkFont(size=15), fg_color="transparent", anchor="w", command=self.show_dashboard)
        self.btn_dash.pack(pady=5, padx=20, fill="x")
        
        self.btn_add = ctk.CTkButton(self.sidebar, text="➕ Add Data", height=40, font=ctk.CTkFont(size=15), fg_color="transparent", anchor="w", command=self.show_add_form)
        self.btn_add.pack(pady=5, padx=20, fill="x")
        
        # 2. Database Tables
        ctk.CTkLabel(self.sidebar, text="DATABASE TABLES", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray").pack(pady=(20, 5), padx=20, anchor="w")

        tables_info = [
            ("⌚ Watches", "Watch"),
            ("🏢 Brands", "Brand"),
            ("⚙️ Movements", "Movement"),
            ("🧩 Parts", "Part"),
            ("✨ Features", "Feature"),
            ("🔨 Auctions", "AuctionRecord"),
            ("🛡️ Auth Reports", "AuthenticationReport")
        ]

        for text, table_name in tables_info:
            btn = ctk.CTkButton(self.sidebar, text=text, height=35, font=ctk.CTkFont(size=14), fg_color="transparent", anchor="w", 
                                command=lambda t=table_name: self.show_tables_view(t))
            btn.pack(pady=2, padx=20, fill="x")
            
        # 3. Reports
        ctk.CTkLabel(self.sidebar, text="DOCUMENTATION", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray").pack(pady=(20, 5), padx=20, anchor="w")
        self.btn_rep = ctk.CTkButton(self.sidebar, text="📄 Certificates & Reports", height=40, font=ctk.CTkFont(size=15), fg_color="transparent", anchor="w", command=self.show_reports)
        self.btn_rep.pack(pady=5, padx=20, fill="x")

        # Footer Name
        self.footer = ctk.CTkLabel(self.sidebar, text="Ultimate Edition V23", font=ctk.CTkFont(size=11), text_color="gray")
        self.footer.pack(side="bottom", pady=30)

    def setup_main_frames(self):
        self.dash_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.add_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.tables_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.report_frame = ctk.CTkFrame(self, fg_color="transparent")

    def hide_all_frames(self):
        self.dash_frame.grid_forget()
        self.add_frame.grid_forget()
        self.tables_frame.grid_forget()
        self.report_frame.grid_forget()

    # ------------------ 1. Dashboard View (With Filters) ------------------
    def show_dashboard(self, keep_filters=False):
        self.hide_all_frames()
        self.dash_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        for child in self.dash_frame.winfo_children(): 
            child.destroy()
        
        header_container = ctk.CTkFrame(self.dash_frame, fg_color="transparent")
        header_container.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(header_container, text="Executive Dashboard", font=ctk.CTkFont(size=30, weight="bold")).pack(side="left")
        
        btn_filter_text = "🔺 Hide Filters" if self.filter_visible else "🔍 Advanced Filters"
        ctk.CTkButton(header_container, text=btn_filter_text, width=150, fg_color="#333", hover_color="#555", command=self.toggle_filters).pack(side="right")

        if self.filter_visible:
            filter_panel = ctk.CTkFrame(self.dash_frame, fg_color="#1a1a1a", corner_radius=10)
            filter_panel.pack(fill="x", padx=5, pady=(0, 20), ipadx=10, ipady=15)
            
            price_frame = ctk.CTkFrame(filter_panel, fg_color="transparent")
            price_frame.pack(side="left", padx=20)
            
            ctk.CTkLabel(price_frame, text="Max Price Limit:", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
            
            self.lbl_price_val = ctk.CTkLabel(price_frame, text=f"${int(self.current_max_price):,}", text_color="#deff9a", font=ctk.CTkFont(size=16, weight="bold"))
            self.lbl_price_val.pack(anchor="w", pady=5)
            
            self.price_slider = ctk.CTkSlider(price_frame, from_=0, to=500000, width=200, command=self.update_price_label)
            self.price_slider.set(self.current_max_price)
            self.price_slider.pack(pady=5)
            
            brand_frame = ctk.CTkFrame(filter_panel, fg_color="transparent")
            brand_frame.pack(side="left", padx=40)
            
            ctk.CTkLabel(brand_frame, text="Filter by Brand:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0,5))
            
            self.brand_vars = {}
            brands_data = self.db.get_table_data("Brand")[1] 
            chk_container = ctk.CTkFrame(brand_frame, fg_color="transparent")
            chk_container.pack()
            
            if brands_data:
                for i, row in enumerate(brands_data):
                    b_name = row[1] 
                    var = ctk.IntVar(value=1 if b_name in self.current_selected_brands else 0)
                    self.brand_vars[b_name] = var
                    chk = ctk.CTkCheckBox(chk_container, text=b_name, variable=var, width=120)
                    chk.grid(row=i//3, column=i%3, padx=5, pady=5, sticky="w")
            else:
                ctk.CTkLabel(chk_container, text="No brands found.", text_color="gray").pack()
                
            btn_frame = ctk.CTkFrame(filter_panel, fg_color="transparent")
            btn_frame.pack(side="right", padx=20)
            
            ctk.CTkButton(btn_frame, text="✔️ Apply Filters", fg_color="#4CAF50", hover_color="#388E3C", command=self.apply_filters).pack(pady=5)
            ctk.CTkButton(btn_frame, text="✖️ Reset", fg_color="#F44336", hover_color="#D32F2F", command=self.reset_filters).pack(pady=5)

        stats = self.db.get_dashboard_stats()
        stats_frame = ctk.CTkFrame(self.dash_frame, fg_color="transparent")
        stats_frame.pack(fill="x", padx=15, pady=(0, 20))

        self.create_stat_card(stats_frame, "Total Inventory", str(stats['total']), "#1a1a1a", "left")
        self.create_stat_card(stats_frame, "Available Value", f"${stats['value']:,.2f}", "#1a1a1a", "left")
        self.create_stat_card(stats_frame, "Sold Items", str(stats['sold']), "#1a1a1a", "right")
        
        grid_container = ctk.CTkFrame(self.dash_frame, fg_color="transparent")
        grid_container.pack(fill="both", expand=True)

        grid_container.grid_columnconfigure(0, weight=1)
        grid_container.grid_columnconfigure(1, weight=1)
        grid_container.grid_columnconfigure(2, weight=1)
        
        if self.current_filtered_watches is not None:
            watches = self.current_filtered_watches
        else:
            watches = self.db.get_watches_full()

        if not watches:
            ctk.CTkLabel(grid_container, text="No matches found matching your criteria.", font=ctk.CTkFont(size=18), text_color="gray").grid(row=0, column=0, columnspan=3, pady=50)

        row = 0
        col = 0
        for watch in watches:
            self.create_watch_card(grid_container, watch, row, col)
            col += 1
            if col > 2: 
                col = 0
                row += 1

    def toggle_filters(self):
        self.filter_visible = not getattr(self, 'filter_visible', False)
        self.show_dashboard(keep_filters=True)

    def update_price_label(self, val):
        self.lbl_price_val.configure(text=f"${int(val):,}")

    def apply_filters(self):
        self.current_max_price = self.price_slider.get()
        self.current_selected_brands = []
        for b_name, var in self.brand_vars.items():
            if var.get() == 1:
                self.current_selected_brands.append(b_name)
        
        all_watches = self.db.get_watches_full()
        filtered = []
        
        for w in all_watches:
            if w['PurchasePrice'] <= self.current_max_price:
                if not self.current_selected_brands or w['BrandName'] in self.current_selected_brands:
                    filtered.append(w)
                    
        self.current_filtered_watches = filtered
        self.show_dashboard(keep_filters=True)

    def reset_filters(self):
        self.current_max_price = 500000
        self.current_selected_brands = []
        self.current_filtered_watches = None
        self.show_dashboard(keep_filters=True)

    def create_stat_card(self, parent, title, value, color, side):
        card = ctk.CTkFrame(parent, fg_color=color, corner_radius=15, height=100)
        card.pack(side=side, fill="x", expand=True, padx=10)
        card.pack_propagate(False)
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=14, weight="bold"), text_color="gray").pack(pady=(15, 5))
        ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=28, weight="bold"), text_color="#deff9a").pack()

    def create_watch_card(self, parent, watch, r, c):
        card = ctk.CTkFrame(parent, width=320, height=450, corner_radius=15, border_width=1, border_color="#333")
        card.grid(row=r, column=c, padx=15, pady=15)
        card.grid_propagate(False)

        script_dir = os.path.dirname(os.path.abspath(__file__))
        img_path = os.path.join(script_dir, watch.get('WatchImage', 'images/placeholder.png'))
        
        try:
            if not os.path.exists(img_path): 
                img_path = os.path.join(script_dir, "images/placeholder.png")
            raw_img = Image.open(img_path)
            ctk_img = ctk.CTkImage(light_image=raw_img, dark_image=raw_img, size=(280, 200))
            ctk.CTkLabel(card, image=ctk_img, text="").pack(pady=15)
        except:
            ctk.CTkLabel(card, text="🖼️ No Image", height=200, fg_color="#222").pack(pady=15, fill="x", padx=20)

        ctk.CTkLabel(card, text=f"{watch['BrandName']}", font=ctk.CTkFont(size=14, weight="bold"), text_color="#deff9a").pack()
        ctk.CTkLabel(card, text=f"{watch['ModelName']}", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=5)
        
        price_status = ctk.CTkFrame(card, fg_color="transparent")
        price_status.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(price_status, text=f"${watch['PurchasePrice']:,.2f}", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")
        
        status_color = "#4CAF50" if watch['Status'] == "Available" else "#F44336" if watch['Status'] == "Sold" else "#FF9800"
        ctk.CTkLabel(price_status, text=watch['Status'], font=ctk.CTkFont(size=14, weight="bold"), text_color=status_color).pack(side="right")

        ctk.CTkButton(card, text="View Details & Actions", height=35, fg_color="#333", hover_color="#555", command=lambda w=watch: self.show_details(w)).pack(side="bottom", pady=20, padx=20, fill="x")

    def show_details(self, watch):
        self.popup = ctk.CTkToplevel(self)
        self.popup.title(f"Watch Details - {watch['ModelName']}")
        self.popup.geometry("450x680")
        self.popup.attributes("-topmost", True)
        
        ctk.CTkLabel(self.popup, text="Inspection & Specifications", font=ctk.CTkFont(size=22, weight="bold"), text_color="#deff9a").pack(pady=(20, 10))
        details_frame = ctk.CTkFrame(self.popup, corner_radius=10)
        details_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        info = [
            ("Watch ID:", str(watch['WatchID'])), 
            ("Brand:", watch['BrandName']), 
            ("Model:", watch['ModelName']), 
            ("Caliber:", watch['CaliberName']), 
            ("Year:", str(watch['ProductionYear'])), 
            ("Serial:", watch['SerialNumber']),
            ("Price:", f"${watch['PurchasePrice']:,.2f}"), 
            ("Status:", watch['Status'])
        ]
        
        for label, value in info:
            row_frame = ctk.CTkFrame(details_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=10, padx=15)
            ctk.CTkLabel(row_frame, text=label, font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
            ctk.CTkLabel(row_frame, text=str(value), font=ctk.CTkFont(size=16)).pack(side="right")

        actions_frame = ctk.CTkFrame(self.popup, fg_color="transparent")
        actions_frame.pack(fill="x", padx=20, pady=20)

        if watch['Status'] == 'Sold':
            ctk.CTkButton(actions_frame, text="🔄 Restock Item", fg_color="#4CAF50", hover_color="#388E3C", height=40, command=lambda: self.restock_popup(watch)).pack(side="left", expand=True, padx=5)
        else:
            ctk.CTkButton(actions_frame, text="🏷️ Mark as Sold", fg_color="#2196F3", hover_color="#1976D2", height=40, command=lambda: self.mark_sold(watch['WatchID'])).pack(side="left", expand=True, padx=5)

        ctk.CTkButton(actions_frame, text="🗑️ Delete Record", fg_color="#F44336", hover_color="#D32F2F", height=40, command=lambda: self.delete_watch_record(watch['WatchID'])).pack(side="right", expand=True, padx=5)

    def restock_popup(self, watch):
        restock_win = ctk.CTkToplevel(self)
        restock_win.title("Restock Watch")
        restock_win.geometry("400x300")
        restock_win.attributes("-topmost", True)

        ctk.CTkLabel(restock_win, text=f"Restocking: {watch['ModelName']}", font=ctk.CTkFont(size=18, weight="bold"), text_color="#deff9a").pack(pady=20)
        
        ctk.CTkLabel(restock_win, text="Enter New Purchase Price ($):", font=ctk.CTkFont(size=14)).pack(pady=5)
        new_price_entry = ctk.CTkEntry(restock_win, width=250, placeholder_text=str(watch['PurchasePrice']))
        new_price_entry.pack(pady=10)

        def confirm_restock():
            price = new_price_entry.get()
            if not price:
                messagebox.showwarning("Warning", "Please enter a valid price!")
                return
            
            if self.db.update_generic("Watch", "WatchID", watch['WatchID'], {"PurchasePrice": price, "Status": "Available"}):
                messagebox.showinfo("Success", "Watch restocked successfully!")
                restock_win.destroy()
                self.popup.destroy()
                self.current_filtered_watches = None
                self.show_dashboard()
            else:
                messagebox.showerror("Error", "Failed to update database. Ensure price is a valid number.")

        ctk.CTkButton(restock_win, text="Confirm Restock", fg_color="#4CAF50", height=40, command=confirm_restock).pack(pady=30)

    def mark_sold(self, watch_id):
        if messagebox.askyesno("Confirm Update", "Are you sure you want to mark this watch as Sold?", parent=self.popup):
            if self.db.update_watch_status(watch_id, 'Sold'):
                messagebox.showinfo("Success", "Status updated successfully!", parent=self.popup)
                self.popup.destroy()
                self.current_filtered_watches = None
                self.show_dashboard()
            else:
                messagebox.showerror("Update Error", "Failed to update watch status.", parent=self.popup)

    def delete_watch_record(self, watch_id):
        if messagebox.askyesno("Confirm Deletion", "WARNING: Are you sure you want to PERMANENTLY delete this record?", icon='warning', parent=self.popup):
            if self.db.delete_generic("Watch", "WatchID", watch_id):
                messagebox.showinfo("Deleted", "Watch record removed successfully.", parent=self.popup)
                self.popup.destroy()
                self.current_filtered_watches = None
                self.show_dashboard()
            else:
                messagebox.showerror("Action Denied", "Cannot delete this Watch!\n\nIt is linked to related records (like Authentication Reports, Parts, or Auctions). Please delete those related records first to maintain data integrity.", parent=self.popup)

    # ------------------ 2. Database Explorer View ------------------
    def show_tables_view(self, table_name="Watch"):
        self.hide_all_frames()
        self.tables_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        for child in self.tables_frame.winfo_children(): 
            child.destroy()
            
        self.current_table = ctk.StringVar(value=table_name)
        
        ctk.CTkLabel(self.tables_frame, text=f"{table_name} Data Explorer", font=ctk.CTkFont(size=30, weight="bold")).pack(anchor="w", pady=(0, 10), padx=15)
        
        controls = ctk.CTkFrame(self.tables_frame, fg_color="transparent")
        controls.pack(fill="x", padx=15, pady=10)
        
        self.search_entry = ctk.CTkEntry(controls, placeholder_text=f"Search in {table_name}...", width=250)
        self.search_entry.pack(side="left", padx=(0, 10))
        
        ctk.CTkButton(controls, text="🔍 Search", width=100, command=self.filter_table).pack(side="left")

        self.tree_container = ctk.CTkFrame(self.tables_frame)
        self.tree_container.pack(fill="both", expand=True, padx=15, pady=10)

        actions_frame = ctk.CTkFrame(self.tables_frame, fg_color="transparent")
        actions_frame.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkButton(actions_frame, text="✏️ Edit Selected", height=40, command=self.edit_selected_row).pack(side="left", padx=(0, 10))
        ctk.CTkButton(actions_frame, text="🗑️ Delete Selected", height=40, fg_color="#F44336", hover_color="#D32F2F", command=self.delete_selected_row).pack(side="left", padx=10)

        self.load_selected_table(self.current_table.get())

    def load_selected_table(self, table_name):
        for widget in self.tree_container.winfo_children(): 
            widget.destroy()
            
        self.current_columns, self.current_data = self.db.get_table_data(table_name)
        if not self.current_columns: 
            return
        
        self.tree = ttk.Treeview(self.tree_container, columns=self.current_columns, show="headings", selectmode="browse")
        vsb = ttk.Scrollbar(self.tree_container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self.tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)
        
        for col in self.current_columns:
            self.tree.heading(col, text=col, command=lambda _col=col: self.sort_treeview(_col, False))
            self.tree.column(col, width=150, anchor="center")
            
        self.populate_tree(self.current_data)
        
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

    def populate_tree(self, data):
        for item in self.tree.get_children(): 
            self.tree.delete(item)
        for row in data: 
            self.tree.insert("", "end", values=[str(x) if x is not None else "NULL" for x in row])

    # ✨ دالة الـ Pop-up مع ميزة إعادة طباعة التقارير القديمة ✨
    def on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected: 
            return
            
        values = self.tree.item(selected[0])['values']
        table_name = self.current_table.get()
        
        preview_win = ctk.CTkToplevel(self)
        preview_win.title(f"{table_name} Record Preview")
        preview_win.geometry("500x700")
        preview_win.attributes("-topmost", True)
        
        scroll_frame = ctk.CTkScrollableFrame(preview_win, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(scroll_frame, text=f"{table_name} Details", font=ctk.CTkFont(size=22, weight="bold"), text_color="#deff9a").pack(pady=(10, 20))

        # 1. عرض الصورة لو الجدول ساعة
        if table_name == "Watch":
            img_filename = values[4] if len(values) > 4 else "" 
            script_dir = os.path.dirname(os.path.abspath(__file__))
            img_path = os.path.join(script_dir, str(img_filename))
            
            try:
                if not os.path.exists(img_path): 
                    img_path = os.path.join(script_dir, "images/placeholder.png")
                raw_img = Image.open(img_path)
                ctk_img = ctk.CTkImage(light_image=raw_img, dark_image=raw_img, size=(300, 220))
                ctk.CTkLabel(scroll_frame, image=ctk_img, text="").pack(pady=10)
            except Exception as e: 
                print("Image load error:", e)

        # 2. زرار إعادة طباعة الشهادة لو الجدول تقارير (الميزة الجديدة)
        if table_name == "AuthenticationReport":
            try:
                watch_id_idx = self.current_columns.index("WatchID")
                expert_idx = self.current_columns.index("AuthenticatorName")
                result_idx = self.current_columns.index("ResultStatus")
                date_idx = self.current_columns.index("ReportDate")
                
                old_watch_id = int(values[watch_id_idx])
                old_expert = values[expert_idx]
                old_result = values[result_idx]
                old_date = values[date_idx]
                
                def reprint_old_cert():
                    watch = None
                    for w in self.db.get_watches_full():
                        if w['WatchID'] == old_watch_id:
                            watch = w
                            break
                            
                    if watch:
                        self.current_report_data = {
                            "watch": watch,
                            "expert": old_expert,
                            "result": old_result,
                            "date": old_date
                        }
                        self.print_certificate()
                    else:
                        messagebox.showwarning("Not Found", "Cannot generate certificate. The original watch record might have been deleted.", parent=preview_win)
                        
                ctk.CTkButton(scroll_frame, text="🖨️ View / Re-Print Certificate", fg_color="#deff9a", text_color="black", hover_color="#c8e68e", height=45, font=ctk.CTkFont(weight="bold"), command=reprint_old_cert).pack(pady=(0, 20), fill="x", padx=20)
                
            except Exception as e:
                print("Reprint Error:", e)

        # 3. عرض باقي البيانات كالمعتاد
        details_frame = ctk.CTkFrame(scroll_frame, corner_radius=10)
        details_frame.pack(fill="both", expand=True, pady=10)

        for i, col in enumerate(self.current_columns):
            row_frame = ctk.CTkFrame(details_frame, fg_color="transparent")
            row_frame.pack(fill="x", padx=15, pady=10)
            
            ctk.CTkLabel(row_frame, text=f"{col}:", font=ctk.CTkFont(size=14, weight="bold"), text_color="gray", width=150, anchor="w").pack(side="left")
            ctk.CTkLabel(row_frame, text=str(values[i]), font=ctk.CTkFont(size=14), wraplength=250, justify="left").pack(side="left", padx=10)

        ctk.CTkButton(preview_win, text="Close Preview", fg_color="#333", hover_color="#555", height=40, command=preview_win.destroy).pack(pady=20)

    def filter_table(self):
        search_term = self.search_entry.get().lower()
        if not search_term: 
            self.populate_tree(self.current_data)
            return
            
        filtered_rows = []
        for row in self.current_data:
            if any(search_term in str(cell).lower() for cell in row):
                filtered_rows.append(row)
        self.populate_tree(filtered_rows)

    def sort_treeview(self, col, reverse):
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        try: 
            l.sort(key=lambda t: float(t[0]), reverse=reverse)
        except ValueError: 
            l.sort(reverse=reverse)
            
        for index, (val, k) in enumerate(l): 
            self.tree.move(k, '', index)
            
        self.tree.heading(col, command=lambda _col=col: self.sort_treeview(_col, not reverse))

    def edit_selected_row(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a row to edit first.")
            return
            
        values = self.tree.item(selected[0])['values']
        table_name = self.current_table.get()
        pk_col = self.current_columns[0] 
        pk_val = values[0]

        edit_win = ctk.CTkToplevel(self)
        edit_win.title(f"Edit Record - {table_name}")
        edit_win.geometry("500x600")
        edit_win.attributes("-topmost", True)

        ctk.CTkLabel(edit_win, text=f"Update {table_name} Data", font=ctk.CTkFont(size=22, weight="bold"), text_color="#deff9a").pack(pady=20)
        
        entries = {}
        for i, col in enumerate(self.current_columns):
            row_frame = ctk.CTkFrame(edit_win, fg_color="transparent")
            row_frame.pack(fill="x", padx=30, pady=5)
            
            ctk.CTkLabel(row_frame, text=f"{col}:", width=120, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left")
            
            entry = ctk.CTkEntry(row_frame, width=250)
            entry.pack(side="left", padx=10)
            entry.insert(0, values[i] if values[i] != "NULL" else "")
            
            if i == 0: 
                entry.configure(state="disabled") 
            else: 
                entries[col] = entry

        def save_updates():
            update_data = {}
            for col, ent in entries.items():
                update_data[col] = ent.get()
                
            if self.db.update_generic(table_name, pk_col, pk_val, update_data):
                messagebox.showinfo("Success", "Record updated successfully!", parent=edit_win)
                edit_win.destroy()
                self.load_selected_table(table_name)
            else:
                messagebox.showerror("Database Error", "Failed to update record. Please check data types.", parent=edit_win)

        ctk.CTkButton(edit_win, text="💾 Save Changes", height=40, font=ctk.CTkFont(weight="bold"), fg_color="#deff9a", text_color="black", command=save_updates).pack(pady=30)

    def delete_selected_row(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a row to delete first.")
            return

        table_name = self.current_table.get()
        pk_col = self.current_columns[0]
        pk_val = self.tree.item(selected[0])['values'][0]

        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete {pk_col} = {pk_val} from {table_name}?", icon='warning'):
            if self.db.delete_generic(table_name, pk_col, pk_val):
                messagebox.showinfo("Deleted", "Record has been deleted successfully.")
                self.load_selected_table(table_name)
            else:
                if table_name == "Brand":
                    msg = "Cannot delete this Brand!\n\nThere are watches in the inventory linked to this brand. Please remove or reassign those watches first."
                elif table_name == "Movement":
                    msg = "Cannot delete this Movement!\n\nIt is currently powering watches in the inventory. Please remove it from those watches first."
                elif table_name == "Watch":
                    msg = "Cannot delete this Watch!\n\nIt has related data like Authentication Reports, Auction Records, or Parts. Please delete those first."
                else:
                    msg = "Cannot delete!\n\nThis record is linked to other data in the system and is required to maintain database integrity."
                
                messagebox.showerror("Action Denied", msg)

    # ------------------ 3. Add Data View ------------------
    def show_add_form(self):
        self.hide_all_frames()
        self.add_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        for child in self.add_frame.winfo_children(): 
            child.destroy()
        
        header_frame = ctk.CTkFrame(self.add_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 20), padx=15)
        
        ctk.CTkLabel(header_frame, text="Insert New Record", font=ctk.CTkFont(size=30, weight="bold")).pack(side="left")
        ctk.CTkLabel(header_frame, text="Target Table:", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left", padx=(40, 10))
        
        self.combo_add_table = ctk.CTkOptionMenu(header_frame, values=["Watch"] + list(self.table_schemas.keys()), command=self.build_dynamic_form)
        self.combo_add_table.pack(side="left")
        
        self.dynamic_form_container = ctk.CTkFrame(self.add_frame, width=700, height=600, corner_radius=15, fg_color="#1a1a1a")
        self.dynamic_form_container.pack(pady=10, anchor="center")
        self.dynamic_form_container.pack_propagate(False)
        
        self.build_dynamic_form("Watch")

    def build_dynamic_form(self, table_name):
        for child in self.dynamic_form_container.winfo_children(): 
            child.destroy()
            
        self.current_dynamic_entries.clear()
        self.selected_image_path = None
        
        if table_name == "Watch": 
            self.build_watch_form()
        else: 
            self.build_generic_form(table_name)

    def build_generic_form(self, table_name):
        ctk.CTkLabel(self.dynamic_form_container, text=f"{table_name} Data Entry", font=ctk.CTkFont(size=22, weight="bold"), text_color="#deff9a").pack(pady=20)
        
        for field in self.table_schemas[table_name]:
            row = ctk.CTkFrame(self.dynamic_form_container, fg_color="transparent")
            row.pack(fill="x", padx=50, pady=10)
            
            ctk.CTkLabel(row, text=f"{field}:", width=150, anchor="w", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
            
            entry = ctk.CTkEntry(row, placeholder_text=f"Enter {field}...", width=300, height=35)
            entry.pack(side="left", padx=10)
            self.current_dynamic_entries[field] = entry
            
        ctk.CTkButton(self.dynamic_form_container, text=f"💾 Save to {table_name}", height=45, font=ctk.CTkFont(size=16, weight="bold"), fg_color="#deff9a", text_color="black", hover_color="#c8e68e", command=lambda: self.save_generic(table_name)).pack(side="bottom", pady=30, padx=50, fill="x")

    def build_watch_form(self):
        left_col = ctk.CTkFrame(self.dynamic_form_container, fg_color="transparent")
        left_col.pack(side="left", fill="both", expand=True, padx=20, pady=20)
        
        right_col = ctk.CTkFrame(self.dynamic_form_container, fg_color="transparent")
        right_col.pack(side="right", fill="both", expand=True, padx=20, pady=20)
        
        self.ent_serial = ctk.CTkEntry(left_col, placeholder_text="Serial Number (e.g., RX-999)", height=40)
        self.ent_serial.pack(pady=15, fill="x")
        
        self.ent_model = ctk.CTkEntry(left_col, placeholder_text="Model Name", height=40)
        self.ent_model.pack(pady=15, fill="x")
        
        self.ent_year = ctk.CTkEntry(left_col, placeholder_text="Production Year", height=40)
        self.ent_year.pack(pady=15, fill="x")
        
        self.ent_price = ctk.CTkEntry(left_col, placeholder_text="Purchase Price ($)", height=40)
        self.ent_price.pack(pady=15, fill="x")
        
        row_ids = ctk.CTkFrame(left_col, fg_color="transparent")
        row_ids.pack(pady=10, fill="x")
        
        self.ent_brand = ctk.CTkEntry(row_ids, placeholder_text="Brand ID", width=120, height=40)
        self.ent_brand.pack(side="left")
        
        self.ent_move = ctk.CTkEntry(row_ids, placeholder_text="Movement ID", width=120, height=40)
        self.ent_move.pack(side="right")
        
        ctk.CTkLabel(right_col, text="Watch Image:", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(10, 5))
        
        self.lbl_image_status = ctk.CTkLabel(right_col, text="No image selected", text_color="gray", fg_color="#222", height=150, corner_radius=10)
        self.lbl_image_status.pack(fill="x", pady=10)
        
        ctk.CTkButton(right_col, text="📁 Browse Image...", height=40, fg_color="#333", hover_color="#555", command=self.browse_image).pack(fill="x", pady=10)
        
        ctk.CTkButton(self.dynamic_form_container, text="💾 Save Watch to Database", height=50, font=ctk.CTkFont(size=18, weight="bold"), fg_color="#deff9a", text_color="black", hover_color="#c8e68e", command=self.save_watch).pack(side="bottom", fill="x", padx=20, pady=20)

    def browse_image(self):
        file_path = filedialog.askopenfilename(title="Select Watch Image", filetypes=[("Image Files", "*.png *.jpg *.jpeg")])
        if file_path:
            self.selected_image_path = file_path
            self.lbl_image_status.configure(text=f"Selected:\n{os.path.basename(file_path)}", text_color="#deff9a")

    def save_watch(self):
        if not all([self.ent_serial.get(), self.ent_model.get(), self.ent_year.get(), self.ent_price.get(), self.ent_brand.get(), self.ent_move.get()]): 
            messagebox.showwarning("Warning", "Please fill in all required fields!")
            return
            
        final_db_image_path = 'images/placeholder.png'
        if self.selected_image_path:
            images_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'images')
            os.makedirs(images_dir, exist_ok=True)
            ext = os.path.splitext(self.selected_image_path)[1]
            new_filename = f"{self.ent_serial.get()}_{self.ent_model.get().replace(' ', '_')}{ext}"
            
            try: 
                shutil.copy(self.selected_image_path, os.path.join(images_dir, new_filename))
                final_db_image_path = f"images/{new_filename}"
            except Exception as e: 
                print("Error copying image:", e)
                
        success = self.db.add_watch(
            self.ent_serial.get(), 
            self.ent_model.get(), 
            self.ent_year.get(), 
            final_db_image_path, 
            self.ent_price.get(), 
            self.ent_brand.get(), 
            self.ent_move.get()
        )
        
        if success:
            messagebox.showinfo("Success", "Watch added successfully to the database!")
            self.show_dashboard()
        else:
            messagebox.showerror("Database Error", "Failed to save! Please check if Brand ID and Movement ID exist, and ensure data types are correct.")

    def save_generic(self, table_name):
        data_dict = {}
        for field, entry in self.current_dynamic_entries.items():
            data_dict[field] = entry.get()
            
        if not all(data_dict.values()): 
            messagebox.showwarning("Warning", "Please fill in all fields!")
            return
            
        if self.db.insert_generic(table_name, data_dict): 
            messagebox.showinfo("Success", f"Record added successfully to {table_name}!")
            for entry in self.current_dynamic_entries.values(): 
                entry.delete(0, 'end')
        else:
            messagebox.showerror("Database Error", f"Failed to insert into {table_name}. Check Foreign Keys and Data Types.")

    # ------------------ 4. Reports & Print View ------------------
    def show_reports(self):
        self.hide_all_frames()
        self.report_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        for child in self.report_frame.winfo_children(): 
            child.destroy()
        
        ctk.CTkLabel(self.report_frame, text="Generate Certificate of Authenticity", font=ctk.CTkFont(size=30, weight="bold")).pack(anchor="w", pady=(0, 20), padx=15)
        
        main_container = ctk.CTkFrame(self.report_frame, fg_color="transparent")
        main_container.pack(fill="both", expand=True)

        left_panel = ctk.CTkFrame(main_container, width=400, fg_color="#1a1a1a", corner_radius=15)
        left_panel.pack(side="left", fill="y", padx=15, pady=10)
        left_panel.pack_propagate(False)

        self.right_panel = ctk.CTkFrame(main_container, fg_color="#f0f0f0", corner_radius=5)
        self.right_panel.pack(side="right", fill="both", expand=True, padx=15, pady=10)

        ctk.CTkLabel(left_panel, text="Report Details", font=ctk.CTkFont(size=20, weight="bold"), text_color="#deff9a").pack(pady=20)

        self.watches_data = self.db.get_watches_full()
        watch_options = []
        for w in self.watches_data:
            watch_options.append(f"{w['WatchID']} - {w['BrandName']} {w['ModelName']}")
            
        if not watch_options: 
            watch_options = ["No watches found"]

        ctk.CTkLabel(left_panel, text="Select Watch:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(10,0))
        self.combo_rep_watch = ctk.CTkOptionMenu(left_panel, values=watch_options, width=350)
        self.combo_rep_watch.pack(padx=20, pady=5)

        ctk.CTkLabel(left_panel, text="Authenticator Name:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(15,0))
        self.ent_expert = ctk.CTkEntry(left_panel, placeholder_text="e.g., Eng. Hazem", width=350)
        self.ent_expert.pack(padx=20, pady=5)

        ctk.CTkLabel(left_panel, text="Inspection Result:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(15,0))
        result_options = ["100% Authentic", "Authentic (Parts Replaced)", "Needs Maintenance", "Counterfeit / Fake"]
        self.combo_result = ctk.CTkOptionMenu(left_panel, values=result_options, width=350)
        self.combo_result.pack(padx=20, pady=5)

        ctk.CTkButton(left_panel, text="⚙️ Generate & Save Report", height=45, fg_color="#333", hover_color="#555", font=ctk.CTkFont(weight="bold"), command=self.generate_report_preview).pack(fill="x", padx=20, pady=30)
        
        self.btn_print = ctk.CTkButton(left_panel, text="🖨️ Print Certificate (PDF)", height=50, fg_color="#deff9a", text_color="black", hover_color="#c8e68e", font=ctk.CTkFont(size=16, weight="bold"), state="disabled", command=self.print_certificate)
        self.btn_print.pack(fill="x", padx=20, side="bottom", pady=20)

        self.lbl_preview = ctk.CTkLabel(self.right_panel, text="Select a watch and click Generate\nto preview the certificate.", font=ctk.CTkFont(size=16), text_color="gray")
        self.lbl_preview.pack(expand=True)

    def generate_report_preview(self):
        selection = self.combo_rep_watch.get()
        expert = self.ent_expert.get()
        result = self.combo_result.get()

        if selection == "No watches found" or not expert:
            messagebox.showwarning("Warning", "Please select a watch and enter the expert name.")
            return

        watch_id = int(selection.split(" - ")[0])
        watch = None
        for w in self.watches_data:
            if w['WatchID'] == watch_id:
                watch = w
                break
                
        if not watch: 
            return

        today = datetime.date.today().strftime("%Y-%m-%d")
        
        report_data = {
            "AuthenticatorName": expert, 
            "ResultStatus": result, 
            "ReportDate": today, 
            "WatchID": str(watch_id)
        }
        
        success = self.db.insert_generic("AuthenticationReport", report_data)

        if not success:
            messagebox.showerror("Database Error", "Failed to save report to database.")
            return
            
        messagebox.showinfo("Success", "Report saved to Database successfully!")

        for child in self.right_panel.winfo_children(): 
            child.destroy()

        cert_frame = ctk.CTkFrame(self.right_panel, fg_color="white", corner_radius=0)
        cert_frame.pack(fill="both", expand=True, padx=40, pady=40)

        ctk.CTkLabel(cert_frame, text="MNU WATCHES", font=("Georgia", 32, "bold"), text_color="#1a1a1a").pack(pady=(30, 0))
        ctk.CTkLabel(cert_frame, text="CERTIFICATE OF AUTHENTICITY", font=("Arial", 16, "bold"), text_color="#b89742").pack(pady=(0, 30))

        content_frame = ctk.CTkFrame(cert_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=50)

        info = [
            ("Date of Inspection:", today), 
            ("Reference / Watch ID:", str(watch['WatchID'])), 
            ("Brand:", watch['BrandName']),
            ("Model:", watch['ModelName']), 
            ("Caliber:", watch['CaliberName']), 
            ("Serial Number:", watch['SerialNumber']),
            ("Production Year:", str(watch['ProductionYear'])), 
            ("------------------------", "------------------------"),
            ("Inspection Result:", result), 
            ("Certified By:", expert)
        ]

        for label, val in info:
            row = ctk.CTkFrame(content_frame, fg_color="transparent")
            row.pack(fill="x", pady=8)
            
            ctk.CTkLabel(row, text=label, font=("Arial", 14, "bold"), text_color="#333", width=200, anchor="w").pack(side="left")
            
            val_color = "#b89742" if label == "Inspection Result:" else "#555"
            val_font = ("Arial", 14, "bold") if label == "Inspection Result:" else ("Arial", 14)
            
            ctk.CTkLabel(row, text=val, font=val_font, text_color=val_color, anchor="w").pack(side="left")

        ctk.CTkLabel(cert_frame, text="Official MNU Document - Verifiable in Database", font=("Arial", 10), text_color="gray").pack(side="bottom", pady=20)

        self.current_report_data = {
            "watch": watch, 
            "expert": expert, 
            "result": result, 
            "date": today
        }
        self.btn_print.configure(state="normal")

    def print_certificate(self):
        if not self.current_report_data: 
            return
            
        d = self.current_report_data
        w = d['watch']
        
        html_content = f"""
        <html>
        <head>
            <title>MNU Certificate - {w['SerialNumber']}</title>
            <style>
                body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #333; line-height: 1.6; padding: 40px; background: #fff; }}
                .container {{ max-width: 800px; margin: auto; padding: 50px; border: 10px solid #1a1a1a; outline: 2px solid #b89742; outline-offset: -16px; position: relative; }}
                .header {{ text-align: center; border-bottom: 2px solid #b89742; padding-bottom: 20px; margin-bottom: 40px; }}
                .logo {{ font-size: 48px; font-weight: bold; letter-spacing: 5px; margin: 0; color: #1a1a1a; }}
                .subtitle {{ font-size: 20px; color: #b89742; letter-spacing: 3px; margin-top: 5px; }}
                .details-table {{ width: 100%; border-collapse: collapse; margin-bottom: 40px; }}
                .details-table td {{ padding: 15px 10px; border-bottom: 1px solid #eee; font-size: 16px; }}
                .label {{ font-weight: bold; width: 40%; color: #555; }}
                .result-box {{ background: #f9f9f9; border-left: 5px solid #b89742; padding: 20px; margin-bottom: 40px; }}
                .result-title {{ font-size: 14px; color: #777; text-transform: uppercase; margin-bottom: 5px; }}
                .result-value {{ font-size: 24px; font-weight: bold; color: #1a1a1a; }}
                .footer {{ display: flex; justify-content: space-between; align-items: flex-end; margin-top: 60px; }}
                .signature-box {{ width: 250px; text-align: center; border-top: 1px solid #333; padding-top: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 class="logo">MNU</h1>
                    <div class="subtitle">CERTIFICATE OF AUTHENTICITY</div>
                </div>
                <table class="details-table">
                    <tr><td class="label">Date of Inspection:</td><td>{d['date']}</td></tr>
                    <tr><td class="label">Watch ID:</td><td>{w['WatchID']}</td></tr>
                    <tr><td class="label">Brand:</td><td>{w['BrandName']}</td></tr>
                    <tr><td class="label">Model:</td><td>{w['ModelName']}</td></tr>
                    <tr><td class="label">Serial Number:</td><td>{w['SerialNumber']}</td></tr>
                </table>
                <div class="result-box">
                    <div class="result-title">Official Inspection Result</div>
                    <div class="result-value">{d['result']}</div>
                </div>
                <div class="footer">
                    <div>
                        <p style="font-size: 12px; color: #777;">Document ID: MNU-CERT-{w['WatchID']}</p>
                    </div>
                    <div class="signature-box">
                        <strong>{d['expert']}</strong><br>
                        <span style="font-size: 12px; color: #777;">Master Horologist</span>
                    </div>
                </div>
            </div>
            <script>window.onload = function() {{ window.print(); }}</script>
        </body>
        </html>
        """
        
        file_path = os.path.abspath(f"MNU_Certificate_{w['SerialNumber']}.html")
        with open(file_path, "w", encoding="utf-8") as f: 
            f.write(html_content)
            
        webbrowser.open(f"file:///{file_path}")

if __name__ == "__main__":
    app = WatchApp()
    app.mainloop()