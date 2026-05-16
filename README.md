# ⌚ MNU Watches Studio
**Sophisticated Luxury Watch Inventory & Enterprise Management System**

A robust, object-oriented desktop application designed for high-end horology boutiques. This studio provides a modern GUI to streamline watch inventory tracking, authentication processing, and auction record management, backed by a powerful Microsoft SQL Server database. Built with a focus on data integrity, OOP architectures, and seamless full-stack integration.

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Microsoft SQL Server](https://img.shields.io/badge/Microsoft%20SQL%20Server-CC2927?style=for-the-badge&logo=microsoft-sql-server&logoColor=white)
![CustomTkinter](https://img.shields.io/badge/Tkinter-Modern%20UI-FFD43B?style=for-the-badge&logo=python&logoColor=black)

---

## 💎 Core Features

* 📊 **Smart Dashboard Analytics:** A dynamic statistical reporting tool that analyzes inventory to provide real-time metrics on total available watches, boutique valuation, and total sold items.
* 🎛️ **Dynamic Form Generation:** A sophisticated UI builder that algorithmically generates data entry forms on-the-fly, reading table schemas directly from SQL Server to create appropriate input fields dynamically.
* 🛡️ **Enterprise-Grade Integrity:** Strictly enforces Database Normalization (3NF) principles through the rigid application of Primary Key, Foreign Key (M:N, 1:M), and data type constraints, ensuring reliable data flow.
* 📄 **Automated HTML Reporting:** Dynamic generation of official "Certificates of Authenticity" by injecting SQL data into custom HTML/CSS templates, ready for professional printing as PDFs via the default web browser.
* 🖼️ **Smart Image Management:** Optimized system that stores local file paths in SQL Server rather than bulky binary data (BLOBs), utilizing dynamic rendering to visualize watch images within the GUI.
* 🔄 **Lifecycle Management:** Dedicated business logic engine for transactional operations, allowing items to be marked as 'Sold', restocked with updated pricing, and updated through an interactive view.
* 🛡️ **Defensive Database Connectivity:** All Backend operations are protected by advanced `try...except` exception handling and parameterized queries to prevent SQL Injection attacks.

## 🛠️ Tech Stack

* **Microsoft SQL Server (T-SQL):** Handling complex relational schema design, views, and data integrity constraints.
* **CustomTkinter:** For a sleek, modern, and responsive Dark Mode user interface.
* **`pyodbc`:** Driving the core Backend communication and transactional filtering logic.
* **Pillow (PIL):** Bridging database file paths with high-performance GUI image rendering.
* **`webbrowser`:** Handling the output and preview of dynamically generated HTML reports.

## 🚀 Quick Start Guide

**1. Create the Database:**
Open Microsoft SQL Server Management Studio (SSMS) and run the provided SQL setup script:
```sql
-- Execute this file in SSMS
MNU_Watches_Setup.sql
```

This script will automatically create the MNU_Watches database, generate all tables, apply constraints, and insert essential seed data.

2. Configure and Run:
Make sure you have Python installed, then install dependencies:
```Python
pip install customtkinter pyodbc Pillow
```
Open main.py and verify that the self.server variable in the DatabaseManager class points to your local SQL Server instance. Then launch the studio:
```
python main.py
```


📸 Interface Preview
1-
<img width="1920" height="1030" alt="Screenshot 2026-05-17 011304" src="https://github.com/user-attachments/assets/d03b3432-f704-41a1-8aa5-0853dca7ba34" />

2-
<img width="1920" height="1030" alt="Screenshot 2026-05-17 011336" src="https://github.com/user-attachments/assets/001262df-ce9e-49b8-9e6b-05bb1ff17985" />


👨‍💻 About The Developer
Hazem Mohamed Hafez Elhefnawy
Computer Engineering | Menoufia National University (Class of 2028)

Developed as a comprehensive showcase of integrating complex Relational Database Systems (RDBMS) architectures with modern object-oriented Python architectures, full-stack connectivity principles, and dynamic GUI generation.

Building the future, one byte at a time. — Half Engineer. 🔧
