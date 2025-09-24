# FundFlow

**FundFlow** is a Django-based web application designed to analyze and visualize profit and loss from brokerage transactions, including stocks and options trades. By parsing CSV files from platforms like Interactive Brokers (IBKR), it provides users with insights into their trading performance.

![FundFlow Dashboard](https://example.com/screenshot.png) <!-- Replace with an actual screenshot URL -->

---

## Features

- **CSV Parsing**: Upload and parse brokerage transaction files (e.g., IBKR CSV exports).
- **Profit & Loss Calculation**: Automatically computes gains and losses for each trade.
- **Data Visualization**: Visualize trading performance over time with interactive charts.
- **Transaction Tracking**: Maintain a detailed record of all trades for analysis.

---

## Installation

### Prerequisites

- Python 3.8+
- Django 3.2+
- PostgreSQL (or SQLite for development)

### Steps

1. Clone the repository:

     ```bash
     git clone https://github.com/jhinger2121/FundFlow.git
     cd FundFlow
2. Create a virtual environment:
      ```bash
      python -m venv venv
      source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

4. Install dependencies:
      ```bash
       pip install -r requirements.txt
      
5. Apply migrations:
      ```bash
      python manage.py migrate
      
6. Create a superuser to access the admin panel:
      ```bash
      python manage.py createsuperuser
      
8. Run the development server:
      ```bash
      python manage.py runserver
      
Access the application at http://127.0.0.1:8000/.

## Usage
  Upload Transactions: Navigate to the upload section and submit your IBKR CSV files.
  View Analysis: After processing, view detailed reports and visualizations of your trading performance.

## Contributing
Contributions are welcome! Please fork the repository, create a new branch, and submit a pull request with your proposed changes.
