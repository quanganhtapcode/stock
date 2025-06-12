# Vietnam Stock Valuation Tool

A comprehensive web-based application for analyzing and valuing Vietnamese stocks using DCF (Discounted Cash Flow) and FCFE (Free Cash Flow to Equity) models. Built with Python Flask backend and vanilla JavaScript frontend.

## Features

### 📊 Financial Analysis
- **Real-time Stock Data**: Fetches live data from Vietnamese stock exchanges (HOSE, HNX)
- **Company Overview**: Displays key company information, market data, and financial metrics
- **Financial Statements**: Automatically processes income statements, balance sheets, and cash flow statements

### 💰 Valuation Models
- **DCF (FCFF)**: Discounted Cash Flow using Free Cash Flow to Firm
- **FCFE**: Free Cash Flow to Equity model
- **Weighted Valuation**: Combines multiple models with customizable weights
- **Step-by-step Calculations**: Detailed breakdown of valuation process

### 🎯 Investment Analysis
- **Price Target**: Fair value estimation based on financial models
- **Investment Recommendation**: Buy/Hold/Sell recommendations
- **Upside/Downside Analysis**: Potential return calculations
- **Risk Assessment**: Confidence levels and data quality indicators

### 📱 User Interface
- **Responsive Design**: Works on desktop and mobile devices
- **Dark/Light Theme**: User preference toggle
- **Interactive Forms**: Real-time assumption adjustments
- **Export Functionality**: Generate PDF reports (HTML format)

## Installation

### Prerequisites
- Python 3.8+
- Node.js (for development, optional)

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/vietnam-stock-valuation.git
   cd vietnam-stock-valuation
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install required packages manually if needed**
   ```bash
   pip install flask flask-cors pandas numpy vnstock logging
   ```

### Frontend Setup

The frontend uses vanilla JavaScript and requires no build process. Simply serve the static files.

## Usage

### Starting the Application

1. **Start the backend server**
   ```bash
   python backend_server.py
   ```
   The server will start on `http://localhost:5000`

2. **Open the frontend**
   Open `index.html` in your web browser or serve it using a local server:
   ```bash
   # Using Python's built-in server
   python -m http.server 8000
   ```
   Then navigate to `http://localhost:8000`

### Using the Tool

1. **Load Stock Data**
   - Enter a Vietnamese stock symbol (e.g., VCB, FPT, VNM)
   - Select data period (Annual/Quarterly)
   - Click "Load Company Data"

2. **Review Company Information**
   - Check the Overview tab for company details
   - Review financial metrics and market data

3. **Set Valuation Assumptions**
   - Navigate to "Valuation & Assumptions" tab
   - Adjust parameters:
     - Revenue Growth Rate
     - Terminal Growth Rate
     - WACC (Weighted Average Cost of Capital)
     - Required Return on Equity
     - Tax Rate
     - Projection Years

4. **Calculate Valuation**
   - Click "Calculate Valuation"
   - View results for both DCF and FCFE models
   - Adjust model weights if needed

5. **Review Results**
   - Check the Summary Report tab
   - View investment recommendation
   - Export report if needed

## API Endpoints

### GET `/api/stock/<symbol>`
Returns comprehensive stock data for the given symbol.

**Parameters:**
- `symbol`: Stock symbol (e.g., VCB)
- `period`: Data period (`annual` or `quarterly`)

**Response:**
```json
{
  "symbol": "VCB",
  "name": "Vietcombank",
  "current_price": 85000,
  "market_cap": 850000000000,
  "revenue_ttm": 45000000000000,
  "net_income_ttm": 25000000000000,
  "pe_ratio": 12.5,
  "pb_ratio": 2.1,
  "success": true
}
```

### GET `/api/app-data/<symbol>`
Returns processed data optimized for the frontend application.

### GET `/health`
Health check endpoint.

## File Structure

```
vietnam-stock-valuation/
├── backend_server.py          # Flask backend server
├── valuation_models.py        # DCF and FCFE calculation models
├── app.js                     # Frontend JavaScript application
├── index.html                 # Main HTML file
├── style.css                  # Stylesheet with dark/light themes
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Valuation Models

### DCF (Discounted Cash Flow) Model
- Projects future Free Cash Flow to Firm (FCFF)
- Calculates terminal value using perpetual growth
- Discounts cash flows using WACC
- Subtracts net debt to get equity value

**Formula:**
```
Enterprise Value = Σ(FCFF_t / (1 + WACC)^t) + Terminal Value
Equity Value = Enterprise Value - Net Debt
Share Value = Equity Value / Shares Outstanding
```

### FCFE (Free Cash Flow to Equity) Model
- Projects Free Cash Flow to Equity directly
- Uses required return on equity as discount rate
- No need to subtract debt (already equity cash flow)

**Formula:**
```
Equity Value = Σ(FCFE_t / (1 + Required Return)^t) + Terminal Value
Share Value = Equity Value / Shares Outstanding
```

## Data Sources

- **VCI (Vietnam Capital Investment)**: Primary data source for Vietnamese stocks
- **Real-time Pricing**: Live market data from Vietnamese exchanges
- **Financial Statements**: Annual and quarterly reports

## Supported Exchanges

- **HOSE** (Ho Chi Minh Stock Exchange)
- **HNX** (Hanoi Stock Exchange)

## Debugging and Step-by-Step Calculations

The application provides detailed calculation steps when running the DCF model. To see the step-by-step breakdown:

1. Open browser Developer Tools (F12)
2. Go to Console tab
3. Load a stock and run valuation
4. View detailed calculation logs in the console

Example output:
```
=== DCF CALCULATION STEPS ===
Assumptions:
  Revenue Growth: 8.0%
  Terminal Growth: 3.0%
  WACC: 10.5%
  ...
Year-by-Year Projections:
  Year 1:
    Revenue: 2,160,000,000,000
    EBIT: 324,000,000,000
    FCFF: 259,200,000,000
  ...
=== END DCF CALCULATION ===
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is for educational and research purposes only. The valuations provided should not be considered as investment advice. Always consult with qualified financial professionals before making investment decisions.

## Support

For issues, questions, or contributions, please:
1. Check existing [Issues](https://github.com/yourusername/vietnam-stock-valuation/issues)
2. Create a new issue with detailed description
3. Include error logs and steps to reproduce

## Acknowledgments

- **vnstock**: Python library for Vietnamese stock data
- **Flask**: Web framework for Python
- **VCI**: Data provider for Vietnamese stock market

---

**Made with ❤️ for Vietnamese stock market analysis**
