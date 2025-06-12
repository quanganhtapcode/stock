# app.py
import pandas as pd
import numpy as np
from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
from datetime import datetime, timedelta
from vnstock import Vnstock
from vnstock.explorer.vci import Company

app = Flask(__name__)
CORS(app)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class StockDataProvider:
    def __init__(self):
        self.sources = ["VCI"]  # Only use VCI source as requested
        self.vnstock = Vnstock()
        self._all_symbols = None  # Lazy-load symbols list
        logger.info("StockDataProvider initialized with VCI source only (symbols will be loaded on first request)")

    def _get_all_symbols(self):
        """Lazy-load symbols list only when needed"""
        if self._all_symbols is not None:
            return self._all_symbols
            
        logger.info("Loading symbols list for the first time...")
        try:
            stock = self.vnstock.stock(symbol="ACB", source="VCI")
            symbols_df = stock.listing.all_symbols()
            self._all_symbols = symbols_df["symbol"].str.upper().values
            logger.info(f"Successfully loaded {len(self._all_symbols)} symbols from VCI")
            return self._all_symbols
        except Exception as e:
            logger.warning(f"Failed to get symbols list from VCI: {e}")
        
        logger.error("Failed to fetch symbols from VCI source.")
        self._all_symbols = []
        return self._all_symbols

    def validate_symbol(self, symbol: str) -> bool:
        symbols = self._get_all_symbols()  # This will load symbols if needed
        if symbols is None or len(symbols) == 0:
            # If we can't load symbols list, assume symbol is valid
            logger.warning(f"Cannot validate symbol {symbol} - symbols list unavailable")
            return True
        return symbol.upper() in symbols

    def get_stock_data(self, symbol: str, period: str = "annual") -> dict:
        symbol = symbol.upper()
        if not self.validate_symbol(symbol):
            raise ValueError(f"Symbol {symbol} is not valid.")
        
        # First try to get comprehensive data from VCI
        logger.info(f"Attempting to get comprehensive data from VCI for {symbol}")
        vci_data = self._get_vci_data(symbol)
        if vci_data and vci_data.get('success'):
            # Enrich VCI data with additional info if needed
            vci_data.update({
                "symbol": symbol,
                "name": symbol,  # We'll try to get this from company overview if possible
                "exchange": "HOSE",  # Default
                "sector": "Unknown",  # Default
                "data_period": period,
                "price_change": np.nan  # VCI doesn't provide this directly
            })
            
            # Try to get current price from trading board using improved method
            try:
                stock = self.vnstock.stock(symbol=symbol, source="VCI")
                current_price = self._get_market_price_vci(stock, symbol)
                if pd.notna(current_price):
                    vci_data["current_price"] = current_price
            except Exception as e:
                logger.debug(f"Could not get current price from VCI: {e}")
                
            # Calculate market cap if we have price and shares
            if pd.notna(vci_data.get("current_price")) and pd.notna(vci_data.get("shares_outstanding")):
                vci_data["market_cap"] = vci_data["current_price"] * vci_data["shares_outstanding"]
                
            return vci_data
        
        # Fallback to original method only if VCI completely fails
        logger.warning(f"VCI comprehensive data failed, trying basic VCI fallback for {symbol}")
        try:
            stock = self.vnstock.stock(symbol=symbol, source="VCI")  # Only use VCI, no TCBS fallback
            company = self._get_company_overview(stock, symbol)
            financials = self._get_financial_statements(stock, period)
            market = self._get_price_data(stock, company["shares_outstanding"], symbol)
            return {
                **company,
                **financials,
                **market,
                "data_source": "VCI",
                "data_period": period,
                "success": True
            }
        except Exception as exc:
            logger.error(f"All VCI methods failed for {symbol}: {exc}")
            raise RuntimeError(f"All VCI data sources failed for {symbol}")

    def _get_company_overview(self, stock, symbol: str) -> dict:
        """Get company overview using improved VCI listing methods"""
        try:
            # Try to get company info using listing methods first (like test.ipynb)
            symbols_df = stock.listing.symbols_by_exchange()
            industries_df = stock.listing.symbols_by_industries()
            
            # Find company info
            company_info = symbols_df[symbols_df['symbol'] == symbol] if not symbols_df.empty else pd.DataFrame()
            industry_info = industries_df[industries_df['symbol'] == symbol] if not industries_df.empty else pd.DataFrame()
            
            name = symbol
            exchange = "HOSE"
            sector = "Unknown"
            shares = np.nan
            
            if not company_info.empty:
                # Get company name
                name_fields = ["organ_short_name", "organ_name", "short_name", "company_name"]
                for f in name_fields:
                    if f in company_info.columns and pd.notna(company_info[f].iloc[0]) and str(company_info[f].iloc[0]).strip():
                        name = str(company_info[f].iloc[0])
                        break
                
                # Get exchange
                exchange_fields = ["exchange", "comGroupCode", "type"]
                for f in exchange_fields:
                    if f in company_info.columns and pd.notna(company_info[f].iloc[0]):
                        exchange = str(company_info[f].iloc[0])
                        break
                
                # Get shares outstanding
                share_fields = ["listed_share", "issue_share", "outstanding_share", "sharesOutstanding", "totalShares"]
                for f in share_fields:
                    if f in company_info.columns and pd.notna(company_info[f].iloc[0]):
                        shares = float(company_info[f].iloc[0])
                        break
            
            if not industry_info.empty:
                # Get industry info
                sector_fields = ["icb_name2", "icb_name3", "icb_name4", "industry", "industryName"]
                for f in sector_fields:
                    if f in industry_info.columns and pd.notna(industry_info[f].iloc[0]) and str(industry_info[f].iloc[0]).strip():
                        sector = str(industry_info[f].iloc[0])
                        break
            
            # Fallback to company.overview if listing methods didn't work
            if shares == np.nan or name == symbol:
                try:
                    overview = stock.company.overview()
                    if overview is not None and not overview.empty:
                        row = overview.iloc[0]
                        
                        # Get shares if not found above
                        if pd.isna(shares):
                            share_fields = ["issue_share", "listed_share", "outstanding_share", "sharesOutstanding", "totalShares"]
                            for f in share_fields:
                                if f in row and pd.notna(row[f]):
                                    shares = float(row[f])
                                    break
                        
                        # Get name if not found above
                        if name == symbol:
                            name_fields = ["organ_name", "short_name", "company_name", "shortName"]
                            for f in name_fields:
                                if f in row and pd.notna(row[f]) and str(row[f]).strip():
                                    name = str(row[f])
                                    break
                except Exception as e:
                    logger.debug(f"Company overview fallback failed: {e}")
            
            return {
                "symbol": symbol,
                "name": name,
                "exchange": exchange,
                "sector": sector,
                "shares_outstanding": shares
            }
            
        except Exception as e:
            logger.warning(f"Company overview failed for {symbol}: {e}")
            return {
                "symbol": symbol,
                "name": symbol,
                "exchange": "HOSE",
                "sector": "Unknown",
                "shares_outstanding": np.nan
            }

    def _get_financial_statements(self, stock, period: str) -> dict:
        is_quarter = (period == "quarterly")
        freq = "quarter" if is_quarter else "year"
        try:
            income = stock.finance.income_statement(period=freq, lang="vi", dropna=True)
            balance = stock.finance.balance_sheet(period=freq, lang="vi", dropna=True)
            cashfl = stock.finance.cash_flow(period=freq, lang="vi", dropna=True)
            if income.empty and balance.empty:
                income = stock.finance.income_statement(period=freq, lang="en", dropna=True)
                balance = stock.finance.balance_sheet(period=freq, lang="en", dropna=True)
                cashfl = stock.finance.cash_flow(period=freq, lang="en", dropna=True)
            return self._extract_financial_metrics(income, balance, cashfl, is_quarter)
        except Exception as e:
            logger.warning(f"Financial statements failed: {e}")
            return self._get_empty_financials(is_quarter)

    def _get_empty_financials(self, is_quarter: bool) -> dict:
        return {
            "revenue_ttm": np.nan,
            "net_income_ttm": np.nan,
            "ebit": np.nan,
            "ebitda": np.nan,
            "total_assets": np.nan,
            "total_debt": np.nan,
            "total_liabilities": np.nan,
            "cash": np.nan,
            "depreciation": np.nan,
            "fcfe": np.nan,
            "capex": np.nan,
            "is_quarterly_data": is_quarter
        }

    def _extract_financial_metrics(self, income, balance, cashfl, is_quarter):
        mult = 4 if is_quarter else 1
        def _pick(df, candidates):
            if df.empty:
                return np.nan
            row = df.iloc[0]
            for c in candidates:
                if c in row and pd.notna(row[c]):
                    val = row[c]
                    if isinstance(val, str):
                        try:
                            val = float(val.replace(',', ''))
                        except:
                            continue
                    return float(val)
            return np.nan
        net_income = _pick(income, ["Lợi nhuận sau thuế", "Net income", "net_income", "netIncome", "profit"])
        revenue = _pick(income, ["Doanh thu thuần", "Revenue", "revenue", "netRevenue", "totalRevenue"])
        total_assets = _pick(balance, ["TỔNG CỘNG TÀI SẢN", "Total assets", "totalAsset", "totalAssets"])
        total_liabilities = _pick(balance, ["TỔNG CỘNG NỢ PHẢI TRẢ", "Total liabilities", "totalLiabilities", "totalDebt"])
        cash = _pick(balance, ["Tiền và tương đương tiền", "Cash", "cash", "cashAndEquivalents"])
        ebit = _pick(income, ["Lợi nhuận từ hoạt động kinh doanh", "Operating income", "EBIT", "Operating profit", "operationProfit"])
        ebitda = _pick(income, ["EBITDA", "ebitda"])
        depreciation = _pick(cashfl, ["Khấu hao tài sản cố định", "Depreciation", "depreciation"])
        fcfe = _pick(cashfl, ["Lưu chuyển tiền thuần từ hoạt động kinh doanh", "Operating cash flow", "Cash from operations"])
        capex = _pick(cashfl, ["Chi để mua sắm tài sản cố định", "Capital expenditure", "Capex", "capex"])
        return {
            "revenue_ttm": revenue * mult if pd.notna(revenue) else np.nan,
            "net_income_ttm": net_income * mult if pd.notna(net_income) else np.nan,
            "ebit": ebit * mult if pd.notna(ebit) else np.nan,
            "ebitda": ebitda * mult if pd.notna(ebitda) else np.nan,
            "total_assets": total_assets,
            "total_debt": total_liabilities,
            "total_liabilities": total_liabilities,
            "cash": cash,
            "depreciation": depreciation * mult if pd.notna(depreciation) else np.nan,
            "fcfe": fcfe * mult if pd.notna(fcfe) else np.nan,
            "capex": capex * mult if pd.notna(capex) else np.nan,
            "is_quarterly_data": is_quarter
        }

    def _get_price_data(self, stock, shares_outstanding, symbol) -> dict:
        """Get price data using improved VCI method with bid_1_price priority"""
        current_price = self._get_market_price_vci(stock, symbol)
        
        # Get EPS and book value for ratios
        eps = book_value = np.nan
        try:
            ratios = stock.company.ratio_summary()
            if not ratios.empty:
                r = ratios.iloc[0]
                eps_fields = ["eps", "earningsPerShare", "earnings_per_share"]
                for field in eps_fields:
                    if field in r and pd.notna(r[field]):
                        eps = float(r[field])
                        break
                bv_fields = ["book_value", "bookValue", "book_value_per_share"]
                for field in bv_fields:
                    if field in r and pd.notna(r[field]):
                        book_value = float(r[field])
                        break
        except Exception as e:
            logger.debug(f"Ratio summary failed: {e}")
            
        # Calculate derived metrics
        market_cap = (
            current_price * shares_outstanding
            if pd.notna(current_price) and pd.notna(shares_outstanding)
            else np.nan
        )
        pe = (
            current_price / eps
            if pd.notna(current_price) and pd.notna(eps) and eps > 0
            else np.nan
        )
        pb = (
            current_price / book_value
            if pd.notna(current_price) and pd.notna(book_value) and book_value > 0
            else np.nan
        )
        
        return {
            "current_price": current_price,
            "market_cap": market_cap,
            "pe_ratio": pe,
            "pb_ratio": pb
        }

    def _get_vci_data(self, symbol: str) -> dict:
        """Get comprehensive financial data from VCI source"""
        try:
            company = Company(symbol)
            
            # Get ratio summary which contains most financial metrics
            ratio_data = company.ratio_summary().T
            if ratio_data.empty:
                return {}
            
            # Extract data from the first row (most recent data)
            data = ratio_data.iloc[:, 0]  # First column contains the values
            
            # Extract key financial metrics with proper handling
            def safe_get(key, default=np.nan):
                try:
                    if key in data.index and pd.notna(data[key]):
                        return float(data[key])
                    return default
                except:
                    return default
            
            # Map VCI data to our standard format
            financial_data = {
                # Revenue and profit
                'revenue_ttm': safe_get('revenue', 0),
                'net_income_ttm': safe_get('net_profit', 0),
                'revenue_growth': safe_get('revenue_growth', 0) * 100,  # Convert to percentage
                'net_profit_margin': safe_get('net_profit_margin', 0) * 100,
                'gross_margin': safe_get('gross_margin', 0) * 100,
                
                # Profitability ratios
                'roe': safe_get('roe', 0) * 100,  # Convert to percentage
                'roa': safe_get('roa', 0) * 100,
                'roic': safe_get('roic', 0) * 100,
                
                # Valuation metrics
                'pe_ratio': safe_get('pe'),
                'pb_ratio': safe_get('pb'),
                'ps_ratio': safe_get('ps'),
                'pcf_ratio': safe_get('pcf'),
                'ev_ebitda': safe_get('ev_per_ebitda'),
                
                # Per share data
                'eps': safe_get('eps'),
                'eps_ttm': safe_get('eps_ttm'),
                'bvps': safe_get('bvps'),
                
                # Balance sheet - calculated from ratios
                'debt_to_equity': safe_get('de', 0),
                'current_ratio': safe_get('current_ratio'),
                'quick_ratio': safe_get('quick_ratio'),
                'cash_ratio': safe_get('cash_ratio'),
                
                # Market data
                'enterprise_value': safe_get('ev'),
                'shares_outstanding': safe_get('issue_share'),
                'charter_capital': safe_get('charter_capital'),
                
                # Additional metrics
                'ebitda': safe_get('ebitda', 0),
                'ebit': safe_get('ebit', 0),
                'ebit_margin': safe_get('ebit_margin', 0) * 100,
                'dividend_per_share': safe_get('dividend', 0),
                
                # Quality indicators
                'data_source': 'VCI',
                'year_report': safe_get('year_report'),
                'update_date': safe_get('update_date'),
                'success': True
            }
            
            # Calculate derived values from VCI ratios
            shares = safe_get('issue_share', np.nan)
            equity_value = shares * safe_get('bvps', np.nan) if pd.notna(shares) and pd.notna(safe_get('bvps', np.nan)) else np.nan
            
            # Use AE ratio to estimate total assets: AE = Assets/Equity, so Assets = AE * Equity
            ae_ratio = safe_get('ae', np.nan)
            if pd.notna(ae_ratio) and pd.notna(equity_value) and ae_ratio > 0:
                financial_data['total_assets'] = ae_ratio * equity_value
                # DE ratio = Debt/Equity, so Debt = DE * Equity
                de_ratio = safe_get('de', np.nan)
                if pd.notna(de_ratio) and pd.notna(equity_value):
                    financial_data['total_debt'] = de_ratio * equity_value
                    financial_data['total_liabilities'] = financial_data['total_debt']  # Simplified assumption
            else:
                financial_data['total_assets'] = np.nan
                financial_data['total_debt'] = np.nan
                financial_data['total_liabilities'] = np.nan
            
            logger.info(f"Successfully extracted VCI data for {symbol}")
            return financial_data
            
        except Exception as e:
            logger.warning(f"VCI data extraction failed for {symbol}: {e}")
            return {}

    def _get_market_price_vci(self, stock, symbol: str) -> float:
        """
        Get market price using improved VCI method with multi-index column support
        and bid_1_price priority as per working test.ipynb implementation
        """
        try:
            # Method 1: Try VCI stock.trading.price_board first
            price_board_df = stock.trading.price_board([symbol])
            
            if not price_board_df.empty:
                logger.debug("✓ VCI price board data retrieved successfully")
                logger.debug(f"Available columns: {list(price_board_df.columns)}")
                
                # Check price fields with multi-index tuple names (priority order from test.ipynb)
                price_fields = [
                    ('match', 'match_price'),      # Prioritize matched price
                    ('listing', 'ref_price'),      # Reference price as fallback
                    ('bid_ask', 'bid_1_price'),    # Bid price - KEY IMPROVEMENT
                    ('match', 'close_price'),      # Close price fallback
                    ('match', 'last_price')        # Last price fallback
                ]
                
                for field in price_fields:
                    if field in price_board_df.columns:
                        price_val = price_board_df[field].iloc[0]
                        if pd.notna(price_val) and price_val > 0:
                            logger.info(f"✓ Found market price using {field}: {price_val:,.0f} VND")
                            return float(price_val)
                
                logger.debug("⚠️ No valid price found in prioritized multi-index fields")
            else:
                logger.debug("❌ VCI price board returned empty DataFrame")

        except Exception as e:
            logger.debug(f"❌ VCI price_board failed: {e}")

        # Method 2: Fallback to Trading class if VCI stock.trading fails
        try:
            from vnstock.explorer.vci import Trading
            trading = Trading(symbol)
            price_board_df = trading.price_board([symbol])
            
            if not price_board_df.empty:
                logger.debug("✓ Trading class price board retrieved successfully")
                
                # Try same multi-index price fields with Trading class
                price_fields = [
                    ('match', 'match_price'),
                    ('listing', 'ref_price'),
                    ('bid_ask', 'bid_1_price'),
                    ('match', 'close_price'),
                    ('match', 'last_price')
                ]
                
                for field in price_fields:
                    if field in price_board_df.columns:
                        price_val = price_board_df[field].iloc[0]
                        if pd.notna(price_val) and price_val > 0:
                            logger.info(f"✓ Found market price using Trading class {field}: {price_val:,.0f} VND")
                            return float(price_val)
                
                logger.debug("⚠️ No valid price found in Trading class")
            else:
                logger.debug("❌ Trading class price board returned empty")
                
        except Exception as e:
            logger.debug(f"❌ Trading class fallback failed: {e}")

        logger.warning(f"Could not retrieve market price for {symbol}")
        return np.nan

provider = StockDataProvider()

@app.route("/api/stock/<symbol>")
def api_stock(symbol):
    try:
        period = request.args.get("period", "annual")
        data = provider.get_stock_data(symbol, period)
        
        # Convert NaN values to None for JSON serialization
        def convert_nan_to_none(obj):
            if isinstance(obj, dict):
                return {k: convert_nan_to_none(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_nan_to_none(v) for v in obj]
            elif pd.isna(obj):
                return None
            else:
                return obj
        
        clean_data = convert_nan_to_none(data)
        return jsonify(clean_data)
    except Exception as exc:
        logger.error(f"API /stock error {symbol}: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 500

@app.route("/api/app-data/<symbol>")
def api_app(symbol):
    try:
        period = request.args.get("period", "annual")
        data = provider.get_stock_data(symbol, period)
        if data.get("success"):
            # Get key values
            shp = data.get("shares_outstanding", np.nan)
            total_assets = data.get("total_assets", np.nan)
            total_liabilities = data.get("total_debt", np.nan)  # VCI uses total_debt
            net_income = data.get("net_income_ttm", np.nan)
            current_price = data.get("current_price", np.nan)
            
            # Calculate equity
            equity = (
                total_assets - total_liabilities
                if pd.notna(total_assets) and pd.notna(total_liabilities)
                else np.nan
            )
            
            # Calculate missing per-share metrics if not already provided by VCI
            if pd.isna(data.get("earnings_per_share", np.nan)):
                data["earnings_per_share"] = (
                    net_income / shp
                    if pd.notna(net_income) and pd.notna(shp) and shp > 0
                    else data.get("eps", np.nan)  # Use VCI EPS if available
                )
            else:
                data["earnings_per_share"] = data.get("eps", np.nan)
                
            if pd.isna(data.get("book_value_per_share", np.nan)):
                data["book_value_per_share"] = (
                    equity / shp
                    if pd.notna(equity) and pd.notna(shp) and shp > 0
                    else data.get("bvps", np.nan)  # Use VCI BVPS if available
                )
            else:
                data["book_value_per_share"] = data.get("bvps", np.nan)
            
            # Set dividend per share from VCI data
            data["dividend_per_share"] = data.get("dividend_per_share", np.nan)
            
            # ROE and ROA - use VCI values if available, otherwise calculate
            if pd.isna(data.get("roe", np.nan)):
                data["roe"] = (
                    (net_income / equity) * 100
                    if pd.notna(net_income) and pd.notna(equity) and equity != 0
                    else np.nan
                )
                
            if pd.isna(data.get("roa", np.nan)):
                data["roa"] = (
                    (net_income / total_assets) * 100
                    if pd.notna(net_income) and pd.notna(total_assets) and total_assets != 0
                    else np.nan
                )
            
            # Debt to equity ratio
            if pd.isna(data.get("debt_to_equity", np.nan)):
                data["debt_to_equity"] = (
                    total_liabilities / equity
                    if pd.notna(total_liabilities) and pd.notna(equity) and equity != 0
                    else np.nan
                )
            
            # PE and PB ratios - use VCI values if available, otherwise calculate
            if pd.isna(data.get("pe_ratio", np.nan)) and pd.notna(data.get("earnings_per_share")) and data["earnings_per_share"] > 0:
                data["pe_ratio"] = current_price / data["earnings_per_share"]
                
            if pd.isna(data.get("pb_ratio", np.nan)) and pd.notna(data.get("book_value_per_share")) and data["book_value_per_share"] > 0:
                data["pb_ratio"] = current_price / data["book_value_per_share"]
            
            # Add data quality indicators
            data["data_quality"] = {
                "has_real_price": pd.notna(current_price),
                "has_financials": pd.notna(net_income),
                "pe_reliable": pd.notna(data.get("pe_ratio")),
                "pb_reliable": pd.notna(data.get("pb_ratio")),
                "vci_data": data.get("data_source") == "VCI"
            }
            
        # Convert NaN values to None for JSON serialization
        def convert_nan_to_none(obj):
            if isinstance(obj, dict):
                return {k: convert_nan_to_none(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_nan_to_none(v) for v in obj]
            elif pd.isna(obj):
                return None
            else:
                return obj
        
        clean_data = convert_nan_to_none(data)
        return jsonify(clean_data)
    except Exception as exc:
        logger.error(f"API /app-data error {symbol}: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 500

@app.route("/health")
def health():
    return jsonify({"status": "healthy", "vnstock_available": True})

if __name__ == "__main__":
    print("Vietnamese Stock Valuation Backend – running on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)