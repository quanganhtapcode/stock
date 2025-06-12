import numpy as np
import pandas as pd

class ValuationModels:
    """
    Financial valuation models for Vietnamese stocks
    Implements DCF (FCFF) and FCFE models with proper calculations
    """
    def __init__(self, stock_data=None):
        """Initialize with stock data from API"""
        self.stock_data = stock_data or {}

    def calculate_all_models(self, assumptions):
        """Calculate all valuation models with given assumptions"""
        if not self.stock_data:
            return {'error': 'No stock data available'}

        results = {
            'dcf': self.calculate_dcf(assumptions),
            'fcfe': self.calculate_fcfe(assumptions),
            'weighted_average': 0
        }

        # Calculate weighted average
        model_weights = assumptions.get('model_weights', {'dcf': 0.5, 'fcfe': 0.5})
        valid_models = {k: v for k, v in results.items() if k in model_weights and v > 0}

        if valid_models:
            total_weight = sum(model_weights[k] for k in valid_models.keys())
            if total_weight > 0:
                results['weighted_average'] = sum(
                    valid_models[k] * model_weights[k] for k in valid_models.keys()
                ) / total_weight

        return results
    def calculate_dcf(self, assumptions):
        try:
            data = self.stock_data
            print("\n=== DCF CALCULATION STEPS ===")
            
            # Get assumptions
            revenue_growth = assumptions.get('revenue_growth', 0.08)
            terminal_growth = assumptions.get('terminal_growth', 0.03)
            wacc = assumptions.get('wacc', 0.10)
            tax_rate = assumptions.get('tax_rate', 0.20)
            projection_years = assumptions.get('projection_years', 5)
            
            print(f"Assumptions:")
            print(f"  Revenue Growth: {revenue_growth:.1%}")
            print(f"  Terminal Growth: {terminal_growth:.1%}")
            print(f"  WACC: {wacc:.1%}")
            print(f"  Tax Rate: {tax_rate:.1%}")
            print(f"  Projection Years: {projection_years}")

            # Get financial data from stock_data
            current_revenue = data.get('revenue_ttm', 0)
            current_ebit = data.get('ebit', 0)
            current_depreciation = data.get('depreciation', 0)
            shares_outstanding = data.get('shares_outstanding', 1000000000)
            
            print(f"\nBase Financial Data:")
            print(f"  Current Revenue: {current_revenue:,.0f} VND")
            print(f"  Current EBIT: {current_ebit:,.0f} VND")
            print(f"  Current Depreciation: {current_depreciation:,.0f} VND")
            print(f"  Shares Outstanding: {shares_outstanding:,.0f}")

            # Calculate margins
            ebit_margin = current_ebit / current_revenue if current_revenue > 0 else 0.15
            depreciation_rate = current_depreciation / current_revenue if current_revenue > 0 else 0.04
            
            print(f"\nCalculated Margins:")
            print(f"  EBIT Margin: {ebit_margin:.1%}")
            print(f"  Depreciation Rate: {depreciation_rate:.1%}")

            # Project cash flows
            fcff_projections = []
            projected_revenue = current_revenue
            
            print(f"\nYear-by-Year Projections:")
            for year in range(1, projection_years + 1):
                projected_revenue *= (1 + revenue_growth)
                projected_ebit = projected_revenue * ebit_margin
                ebit_after_tax = projected_ebit * (1 - tax_rate)
                projected_depreciation = projected_revenue * depreciation_rate
                projected_capex = projected_revenue * 0.04  # 4% of revenue
                working_capital_change = projected_revenue * revenue_growth * 0.02  # 2% of revenue

                fcff = ebit_after_tax + projected_depreciation - projected_capex - working_capital_change
                fcff_projections.append(fcff)
                
                print(f"  Year {year}:")
                print(f"    Revenue: {projected_revenue:,.0f}")
                print(f"    EBIT: {projected_ebit:,.0f}")
                print(f"    EBIT After Tax: {ebit_after_tax:,.0f}")
                print(f"    Depreciation: {projected_depreciation:,.0f}")
                print(f"    CapEx: {projected_capex:,.0f}")
                print(f"    WC Change: {working_capital_change:,.0f}")
                print(f"    FCFF: {fcff:,.0f}")

            # Calculate present values
            print(f"\nPresent Value Calculations:")
            pv_fcffs = []
            for year, fcff in enumerate(fcff_projections, 1):
                pv = fcff / (1 + wacc) ** year
                pv_fcffs.append(pv)
                print(f"  Year {year} PV: {pv:,.0f} VND")
                
            present_value_fcff = sum(pv_fcffs)
            print(f"  Total PV of FCFFs: {present_value_fcff:,.0f} VND")

            # Terminal value calculation
            terminal_revenue = projected_revenue * (1 + terminal_growth)
            terminal_ebit = terminal_revenue * ebit_margin
            terminal_ebit_after_tax = terminal_ebit * (1 - tax_rate)
            terminal_depreciation = terminal_revenue * depreciation_rate
            terminal_capex = terminal_revenue * 0.04
            terminal_fcff = terminal_ebit_after_tax + terminal_depreciation - terminal_capex

            terminal_value = terminal_fcff / (wacc - terminal_growth)
            present_value_terminal = terminal_value / (1 + wacc) ** projection_years
            
            print(f"\nTerminal Value:")
            print(f"  Terminal FCFF: {terminal_fcff:,.0f} VND")
            print(f"  Terminal Value: {terminal_value:,.0f} VND")
            print(f"  PV of Terminal: {present_value_terminal:,.0f} VND")

            # Enterprise and equity value
            enterprise_value = present_value_fcff + present_value_terminal
            net_debt = data.get('total_debt', 0) - data.get('cash', 0)
            equity_value = enterprise_value - net_debt
            value_per_share = max(0, equity_value / shares_outstanding)
            
            print(f"\nFinal Calculations:")
            print(f"  Enterprise Value: {enterprise_value:,.0f} VND")
            print(f"  Net Debt: {net_debt:,.0f} VND")
            print(f"  Equity Value: {equity_value:,.0f} VND")
            print(f"  Value Per Share: {value_per_share:,.0f} VND")
            print("=== END DCF CALCULATION ===\n")

            return value_per_share

        except Exception as e:
            print(f"DCF calculation error: {e}")
            return 0
    
        
    def calculate_fcfe(self, assumptions):
        """
        Calculate FCFE (Free Cash Flow to Equity) model
        Returns: value per share in VND
        """
        try:
            data = self.stock_data

            # Get assumptions
            revenue_growth = assumptions.get('revenue_growth', 0.08)
            terminal_growth = assumptions.get('terminal_growth', 0.03)
            # Support both 'required_return_equity' and 'requiredReturn' for compatibility
            required_return = assumptions.get('required_return_equity', assumptions.get('requiredReturn', 0.12))
            projection_years = assumptions.get('projection_years', 5)

            # Verify required return > terminal growth
            if required_return <= terminal_growth:
                print("Warning: Required return must be greater than terminal growth rate")
                return 0

            # Get financial data from stock_data
            current_fcfe = data.get('fcfe', 0)
            shares_outstanding = data.get('shares_outstanding', 1000000000)

            # Use calculated FCFE if available, otherwise estimate from net income
            if current_fcfe <= 0:
                net_income = data.get('net_income_ttm', 0)
                depreciation = data.get('depreciation', 0)
                capex = abs(data.get('capex', 0))
                
                # Improved FCFE estimation: Net Income + Depreciation - CapEx - Working Capital Change
                # For simplicity, assume working capital change is small
                current_fcfe = net_income + depreciation - capex
                
                # If still no good FCFE estimate, use 70% of net income as conservative estimate
                if current_fcfe <= 0 and net_income > 0:
                    current_fcfe = net_income * 0.7

            # Project FCFE growth
            fcfe_projections = []
            projected_fcfe = current_fcfe

            for _ in range(projection_years):
                projected_fcfe *= (1 + revenue_growth)
                fcfe_projections.append(projected_fcfe)

            # Calculate present value of projected FCFEs
            present_value_fcfe = sum(
                fcfe / (1 + required_return) ** year for year, fcfe in enumerate(fcfe_projections, 1)
            )

            # Calculate terminal value and its present value
            terminal_fcfe = projected_fcfe * (1 + terminal_growth)
            terminal_value = terminal_fcfe / (required_return - terminal_growth)
            present_value_terminal = terminal_value / (1 + required_return) ** projection_years

            # Calculate equity value
            equity_value = present_value_fcfe + present_value_terminal

            # Calculate value per share
            value_per_share = max(0, equity_value / shares_outstanding)

            return value_per_share

        except Exception as e:
            print(f"FCFE calculation error: {e}")
            return 0

    def calculate_dividend_discount(self, assumptions):
        """
        Calculate Dividend Discount Model
        Not currently used but kept for future implementation
        """
        try:
            data = self.stock_data

            # Get assumptions
            growth_rate = assumptions.get('revenue_growth', 0.08)
            terminal_growth = assumptions.get('terminal_growth', 0.03)
            required_return = assumptions.get('required_return_equity', 0.12)

            # Get financial data
            eps = data.get('earnings_per_share', 0)
            dividend_payout_ratio = 0.3  # Assume 30% payout

            # Calculate dividend per share
            dividend_per_share = eps * dividend_payout_ratio

            # Apply Gordon Growth Model
            if required_return <= terminal_growth:
                return 0

            value_per_share = dividend_per_share * (1 + terminal_growth) / (required_return - terminal_growth)

            return value_per_share

        except Exception as e:
            print(f"DDM calculation error: {e}")
            return 0

# Export the class
if __name__ == "__main__":
    # Testing
    mock_data = {
        'revenue_ttm': 2000000000000,    # 2T VND
        'net_income_ttm': 200000000000,  # 200B VND
        'ebit': 300000000000,            # 300B VND
        'ebitda': 400000000000,          # 400B VND
        'total_assets': 10000000000000,  # 10T VND
        'total_debt': 3000000000000,     # 3T VND
        'total_liabilities': 6000000000000, # 6T VND
        'cash': 1000000000000,           # 1T VND
        'depreciation': 100000000000,    # 100B VND
        'fcfe': 150000000000,            # 150B VND
        'capex': -200000000000,          # -200B VND
        'shares_outstanding': 1000000000,
    }

    default_assumptions = {
        'revenue_growth': 0.08,
        'terminal_growth': 0.03,
        'wacc': 0.10,
        'required_return_equity': 0.12,
        'tax_rate': 0.20,
        'projection_years': 5,
        'model_weights': {'dcf': 0.5, 'fcfe': 0.5}
    }

    models = ValuationModels(mock_data)
    results = models.calculate_all_models(default_assumptions)

    print("Testing Valuation Models with mock data:")
    for model, value in results.items():
        print(f"{model.upper()}: {value:,.2f} VND per share")