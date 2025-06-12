// Application State
class StockValuationApp {
    constructor() {
        this.currentStock = null;
        this.stockData = null;
        this.assumptions = {
            revenueGrowth: 8.0,
            terminalGrowth: 3.0,
            wacc: 10.5,
            requiredReturn: 12.0,
            taxRate: 20.0,
            projectionYears: 5
        };
        this.modelWeights = {
            dcf: 50,
            fcfe: 50
        };
        this.valuationResults = null;
        this.apiBaseUrl = 'http://localhost:5000';
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadDefaultAssumptions();
        this.setupThemeToggle();
    }

    setupEventListeners() {
        // Tab navigation
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });

        // Stock search
        document.getElementById('load-data-btn').addEventListener('click', () => this.loadStockData());
        document.getElementById('stock-symbol').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.loadStockData();
        });

        // Assumptions form
        document.getElementById('calculate-btn').addEventListener('click', () => this.calculateValuation());
        document.getElementById('reset-assumptions-btn').addEventListener('click', () => this.resetAssumptions());

        // Real-time updates on assumption changes
        document.querySelectorAll('#assumptions-form input').forEach(input => {
            input.addEventListener('input', () => this.updateAssumptions());
        });

        // Model weights sliders
        document.getElementById('dcf-weight').addEventListener('input', (e) => this.updateModelWeights(e));
        document.getElementById('fcfe-weight').addEventListener('input', (e) => this.updateModelWeights(e));
        document.getElementById('normalize-weights-btn').addEventListener('click', () => this.normalizeWeights());

        // Export functionality
        document.getElementById('export-report-btn').addEventListener('click', () => this.exportReport());
    }

    setupThemeToggle() {
        const themeToggle = document.getElementById('theme-toggle-btn');
        const currentTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-color-scheme', currentTheme);

        themeToggle.addEventListener('click', () => {
            const current = document.documentElement.getAttribute('data-color-scheme');
            const newTheme = current === 'light' ? 'dark' : 'light';
            document.documentElement.setAttribute('data-color-scheme', newTheme);
            localStorage.setItem('theme', newTheme);
        });
    }

    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Update tab content
        document.querySelectorAll('.tab-pane').forEach(pane => {
            pane.classList.remove('active');
        });
        document.getElementById(tabName).classList.add('active');
    }

    loadDefaultAssumptions() {
        document.getElementById('revenue-growth').value = this.assumptions.revenueGrowth;
        document.getElementById('terminal-growth').value = this.assumptions.terminalGrowth;
        document.getElementById('wacc').value = this.assumptions.wacc;
        document.getElementById('required-return').value = this.assumptions.requiredReturn;
        document.getElementById('tax-rate').value = this.assumptions.taxRate;
        document.getElementById('projection-years').value = this.assumptions.projectionYears;

        this.updateWeightDisplay();
    }

    updateAssumptions() {
        // Update assumptions from form values
        this.assumptions.revenueGrowth = parseFloat(document.getElementById('revenue-growth').value);
        this.assumptions.terminalGrowth = parseFloat(document.getElementById('terminal-growth').value);
        this.assumptions.wacc = parseFloat(document.getElementById('wacc').value);
        this.assumptions.requiredReturn = parseFloat(document.getElementById('required-return').value);
        this.assumptions.taxRate = parseFloat(document.getElementById('tax-rate').value);
        this.assumptions.projectionYears = parseInt(document.getElementById('projection-years').value);
    }

    updateModelWeights(event) {
        const sliderId = event.target.id;
        const value = parseInt(event.target.value);
        
        if (sliderId === 'dcf-weight') {
            this.modelWeights.dcf = value;
            this.modelWeights.fcfe = 100 - value;
            document.getElementById('fcfe-weight').value = 100 - value;
        } else if (sliderId === 'fcfe-weight') {
            this.modelWeights.fcfe = value;
            this.modelWeights.dcf = 100 - value;
            document.getElementById('dcf-weight').value = 100 - value;
        }
        
        this.updateWeightDisplay();
        
        // Update weighted results if valuation is already calculated
        if (this.valuationResults) {
            this.updateWeightedResults();
            this.updateRecommendation();
        }
    }

    updateWeightDisplay() {
        document.getElementById('dcf-weight-value').textContent = `${this.modelWeights.dcf}%`;
        document.getElementById('fcfe-weight-value').textContent = `${this.modelWeights.fcfe}%`;
    }

    normalizeWeights() {
        // Reset to 50-50 split
        this.modelWeights.dcf = 50;
        this.modelWeights.fcfe = 50;
        
        document.getElementById('dcf-weight').value = 50;
        document.getElementById('fcfe-weight').value = 50;
        
        this.updateWeightDisplay();
        
        // Update weighted results if valuation is already calculated
        if (this.valuationResults) {
            this.updateWeightedResults();
            this.updateRecommendation();
        }
    }

    resetAssumptions() {
        // Reset to default values
        this.assumptions = {
            revenueGrowth: 8.0,
            terminalGrowth: 3.0,
            wacc: 10.5,
            requiredReturn: 12.0,
            taxRate: 20.0,
            projectionYears: 5
        };
        
        this.loadDefaultAssumptions();
    }

    async loadStockData() {
        const symbol = document.getElementById('stock-symbol').value.trim().toUpperCase();
        const period = document.getElementById('period-select').value;

        if (!symbol) {
            this.showStatus('Please enter a stock symbol', 'error');
            return;
        }

        this.showLoading(true);
        this.showStatus('Loading data...', 'info');

        try {
            // Increase timeout to 15 seconds for real data fetching
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 15000);

            const response = await fetch(`${this.apiBaseUrl}/api/app-data/${symbol}?period=${period}`, {
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                if (response.status === 404) {
                    throw new Error('No data found for this stock symbol');
                } else if (response.status === 500) {
                    throw new Error('Server error while loading data');
                } else {
                    throw new Error('Unable to connect to server');
                }
            }

            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'Unable to load data from server');
            }
            
            this.stockData = data;
            this.currentStock = symbol;
            
            this.updateOverviewDisplay(data);
            this.showStatus('Data loaded successfully', 'success');
            
        } catch (error) {
            console.error('Error loading stock data:', error);
            
            if (error.name === 'AbortError') {
                this.showStatus('Timeout - Please try again later. Server may be initializing data.', 'error');
            } else {
                this.showStatus(`Data loading error: ${error.message}`, 'error');
            }
            
            // Clear any previous data
            this.stockData = null;
            this.currentStock = null;
            this.clearDisplay();
            
        } finally {
            this.showLoading(false);
        }
    }

    calculateValuation() {
        if (!this.stockData) {
            this.showStatus('Please load company data first', 'error');
            return;
        }

        try {
            // DCF (FCFF) Calculation
            const dcfResult = this.calculateDCF();
            
            // FCFE Calculation  
            const fcfeResult = this.calculateFCFE();

            this.valuationResults = {
                dcf: dcfResult,
                fcfe: fcfeResult
            };

            this.updateValuationDisplay();
            this.updateWeightedResults();
            this.updateRecommendation();
            
            // Enable export button
            document.getElementById('export-report-btn').disabled = false;
            
            this.showStatus('Valuation calculation completed', 'success');
            
        } catch (error) {
            console.error('Error calculating valuation:', error);
            this.showStatus('Error calculating valuation', 'error');
        }
    }

    calculateDCF() {
        const revenue = this.stockData.revenue_ttm || 0;
        const ebitda = this.stockData.ebitda || 0;
        const sharesOutstanding = this.stockData.shares_outstanding || (this.stockData.market_cap / this.stockData.current_price);

        // Use EBITDA as proxy for FCFF (simplified approach)
        const fcff = ebitda * (1 - this.assumptions.taxRate / 100);
        const growthRate = this.assumptions.revenueGrowth / 100;
        const terminalGrowthRate = this.assumptions.terminalGrowth / 100;
        const discountRate = this.assumptions.wacc / 100;

        // Verify WACC > terminal growth rate
        if (discountRate <= terminalGrowthRate) {
            console.warn('WACC must be greater than terminal growth rate');
            return {
                enterpriseValue: 0,
                equityValue: 0,
                shareValue: 0,
                terminalValue: 0,
                projectedCashFlows: 0
            };
        }

        let totalPV = 0;
        let projectedFCFF = fcff;

        // Calculate present value of projected cash flows
        for (let year = 1; year <= this.assumptions.projectionYears; year++) {
            projectedFCFF = projectedFCFF * (1 + growthRate);
            const pv = projectedFCFF / Math.pow(1 + discountRate, year);
            totalPV += pv;
        }

        // Terminal value
        const terminalFCFF = projectedFCFF * (1 + terminalGrowthRate);
        const terminalValue = terminalFCFF / (discountRate - terminalGrowthRate);
        const terminalPV = terminalValue / Math.pow(1 + discountRate, this.assumptions.projectionYears);

        const enterpriseValue = totalPV + terminalPV;
        const debt = this.stockData.total_debt || 0;
        const equityValue = Math.max(0, enterpriseValue - debt);
        const shareValue = equityValue / sharesOutstanding;

        return {
            enterpriseValue,
            equityValue,
            shareValue,
            terminalValue,
            projectedCashFlows: totalPV
        };
    }

    calculateFCFE() {
        const netIncome = this.stockData.net_income_ttm || 0;
        const depreciation = this.stockData.depreciation || 0;
        const capex = Math.abs(this.stockData.capex || 0);
        const sharesOutstanding = this.stockData.shares_outstanding || (this.stockData.market_cap / this.stockData.current_price);

        // Better FCFE calculation
        let fcfe = this.stockData.fcfe || 0;
        
        // If no FCFE data available, estimate from net income
        if (fcfe <= 0) {
            fcfe = netIncome + depreciation - capex;
            
            // If still no good estimate, use 70% of net income
            if (fcfe <= 0 && netIncome > 0) {
                fcfe = netIncome * 0.7;
            }
        }
        
        const growthRate = this.assumptions.revenueGrowth / 100;
        const terminalGrowthRate = this.assumptions.terminalGrowth / 100;
        const discountRate = this.assumptions.requiredReturn / 100;

        // Verify discount rate > terminal growth rate
        if (discountRate <= terminalGrowthRate) {
            console.warn('Required return must be greater than terminal growth rate');
            return {
                equityValue: 0,
                shareValue: 0,
                terminalValue: 0,
                projectedCashFlows: 0
            };
        }

        let totalPV = 0;
        let projectedFCFE = fcfe;

        // Calculate present value of projected cash flows
        for (let year = 1; year <= this.assumptions.projectionYears; year++) {
            projectedFCFE = projectedFCFE * (1 + growthRate);
            const pv = projectedFCFE / Math.pow(1 + discountRate, year);
            totalPV += pv;
        }

        // Terminal value
        const terminalFCFE = projectedFCFE * (1 + terminalGrowthRate);
        const terminalValue = terminalFCFE / (discountRate - terminalGrowthRate);
        const terminalPV = terminalValue / Math.pow(1 + discountRate, this.assumptions.projectionYears);

        const equityValue = totalPV + terminalPV;
        const shareValue = equityValue / sharesOutstanding;

        return {
            equityValue,
            shareValue,
            terminalValue,
            projectedCashFlows: totalPV
        };
    }

    updateValuationDisplay() {
        const currentPrice = this.stockData.current_price;

        // DCF Results
        document.getElementById('dcf-result').textContent = this.formatCurrency(this.valuationResults.dcf.shareValue);
        const dcfDiff = ((this.valuationResults.dcf.shareValue - currentPrice) / currentPrice) * 100;
        const dcfDiffElement = document.getElementById('dcf-diff');
        dcfDiffElement.textContent = `${dcfDiff > 0 ? '+' : ''}${dcfDiff.toFixed(1)}%`;
        dcfDiffElement.className = `result-diff ${dcfDiff > 0 ? 'positive' : 'negative'}`;

        // FCFE Results
        document.getElementById('fcfe-result').textContent = this.formatCurrency(this.valuationResults.fcfe.shareValue);
        const fcfeDiff = ((this.valuationResults.fcfe.shareValue - currentPrice) / currentPrice) * 100;
        const fcfeDiffElement = document.getElementById('fcfe-diff');
        fcfeDiffElement.textContent = `${fcfeDiff > 0 ? '+' : ''}${fcfeDiff.toFixed(1)}%`;
        fcfeDiffElement.className = `result-diff ${fcfeDiff > 0 ? 'positive' : 'negative'}`;

        // Update detailed results in summary tab
        document.getElementById('dcf-ev').textContent = this.formatLargeNumber(this.valuationResults.dcf.enterpriseValue);
        document.getElementById('dcf-equity').textContent = this.formatLargeNumber(this.valuationResults.dcf.equityValue);
        document.getElementById('dcf-share-value').textContent = this.formatCurrency(this.valuationResults.dcf.shareValue);
        document.getElementById('dcf-market-diff').textContent = `${dcfDiff.toFixed(1)}%`;

        document.getElementById('fcfe-equity').textContent = this.formatLargeNumber(this.valuationResults.fcfe.equityValue);
        document.getElementById('fcfe-share-value').textContent = this.formatCurrency(this.valuationResults.fcfe.shareValue);
        document.getElementById('fcfe-market-diff').textContent = `${fcfeDiff.toFixed(1)}%`;
    }

    updateWeightedResults() {
        const dcfValue = this.valuationResults.dcf.shareValue;
        const fcfeValue = this.valuationResults.fcfe.shareValue;
        const dcfWeight = this.modelWeights.dcf / 100;
        const fcfeWeight = this.modelWeights.fcfe / 100;

        const weightedValue = (dcfValue * dcfWeight) + (fcfeValue * fcfeWeight);
        const currentPrice = this.stockData.current_price;
        const weightedDiff = ((weightedValue - currentPrice) / currentPrice) * 100;

        // Update weighted result display
        document.getElementById('weighted-result').textContent = this.formatCurrency(weightedValue);
        const weightedDiffElement = document.getElementById('weighted-diff');
        weightedDiffElement.textContent = `${weightedDiff > 0 ? '+' : ''}${weightedDiff.toFixed(1)}%`;
        weightedDiffElement.className = `result-diff ${weightedDiff > 0 ? 'positive' : 'negative'}`;

        // Update summary
        document.getElementById('target-price').textContent = this.formatCurrency(weightedValue);
        document.getElementById('summary-potential').textContent = `${weightedDiff.toFixed(1)}%`;
        document.getElementById('return-value').textContent = `${weightedDiff.toFixed(1)}%`;
    }

    updateRecommendation() {
        const dcfValue = this.valuationResults.dcf.shareValue;
        const fcfeValue = this.valuationResults.fcfe.shareValue;
        const dcfWeight = this.modelWeights.dcf / 100;
        const fcfeWeight = this.modelWeights.fcfe / 100;
        const weightedValue = (dcfValue * dcfWeight) + (fcfeValue * fcfeWeight);
        const currentPrice = this.stockData.current_price;
        const upside = ((weightedValue - currentPrice) / currentPrice) * 100;

        let recommendation, status, reasoning;

        if (upside > 15) {
            recommendation = 'BUY';
            status = 'success';
            reasoning = `Stock is undervalued with ${upside.toFixed(1)}% upside potential. Recommend buy with target price ${this.formatCurrency(weightedValue)}.`;
        } else if (upside > -15) {
            recommendation = 'HOLD';
            status = 'warning';
            reasoning = `Stock is fairly valued with ${upside.toFixed(1)}% difference. Recommend hold and monitor.`;
        } else {
            recommendation = 'SELL';
            status = 'error';
            reasoning = `Stock is overvalued with ${Math.abs(upside).toFixed(1)}% downside potential. Recommend sell.`;
        }

        // Update recommendation displays
        const recommendationElements = [
            document.getElementById('recommendation'),
            document.getElementById('final-recommendation')
        ];

        recommendationElements.forEach(element => {
            element.innerHTML = `<span class="status status--${status}">${recommendation}</span>`;
        });

        document.getElementById('recommendation-reasoning').textContent = reasoning;

        // Update confidence level
        const confidence = Math.min(100, Math.abs(upside) * 2 + 60);
        document.getElementById('confidence-level').textContent = `${confidence.toFixed(0)}%`;
    }

    exportReport() {
        if (!this.stockData || !this.valuationResults) {
            this.showStatus('No data available to export report', 'error');
            return;
        }

        // Simple HTML export (in a real app, this would generate a PDF)
        const reportContent = this.generateReportHTML();
        const blob = new Blob([reportContent], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${this.currentStock}_valuation_report_${new Date().toISOString().split('T')[0]}.html`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        this.showStatus('Report exported successfully', 'success');
    }

    generateReportHTML() {
        const dcfValue = this.valuationResults.dcf.shareValue;
        const fcfeValue = this.valuationResults.fcfe.shareValue;
        const weightedValue = (dcfValue * this.modelWeights.dcf / 100) + (fcfeValue * this.modelWeights.fcfe / 100);
        const upside = ((weightedValue - this.stockData.current_price) / this.stockData.current_price) * 100;

        return `
        <!DOCTYPE html>
        <html>
        <head>
            <title>Stock Valuation Report ${this.currentStock}</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .header { text-align: center; margin-bottom: 30px; }
                .section { margin-bottom: 20px; }
                .table { width: 100%; border-collapse: collapse; }
                .table th, .table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                .table th { background-color: #f2f2f2; }
                .highlight { background-color: #e8f5e8; font-weight: bold; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>STOCK VALUATION REPORT</h1>
                <h2>${this.stockData.name} (${this.currentStock})</h2>
                <p>Date: ${new Date().toLocaleDateString('en-US')}</p>
            </div>
            
            <div class="section">
                <h3>Company Information</h3>
                <table class="table">
                    <tr><th>Stock Symbol</th><td>${this.stockData.symbol}</td></tr>
                    <tr><th>Company Name</th><td>${this.stockData.name}</td></tr>
                    <tr><th>Industry</th><td>${this.stockData.sector}</td></tr>
                    <tr><th>Exchange</th><td>${this.stockData.exchange}</td></tr>
                </table>
            </div>

            <div class="section">
                <h3>Valuation Results</h3>
                <table class="table">
                    <tr><th>Model</th><th>Value (VND)</th><th>Weight</th></tr>
                    <tr><td>DCF (FCFF)</td><td>${this.formatCurrency(dcfValue)}</td><td>${this.modelWeights.dcf}%</td></tr>
                    <tr><td>FCFE</td><td>${this.formatCurrency(fcfeValue)}</td><td>${this.modelWeights.fcfe}%</td></tr>
                    <tr class="highlight"><td>Weighted Average</td><td>${this.formatCurrency(weightedValue)}</td><td>100%</td></tr>
                </table>
            </div>

            <div class="section">
                <h3>Market Comparison</h3>
                <table class="table">
                    <tr><th>Metric</th><th>Value</th></tr>
                    <tr><td>Current Price</td><td>${this.formatCurrency(this.stockData.current_price)}</td></tr>
                    <tr><td>Target Price</td><td>${this.formatCurrency(weightedValue)}</td></tr>
                    <tr><td>Upside/Downside Potential</td><td>${upside.toFixed(1)}%</td></tr>
                </table>
            </div>

            <div class="section">
                <h3>Assumptions Used</h3>
                <table class="table">
                    <tr><th>Parameter</th><th>Value</th></tr>
                    <tr><td>Revenue Growth</td><td>${this.assumptions.revenueGrowth}%</td></tr>
                    <tr><td>Terminal Growth</td><td>${this.assumptions.terminalGrowth}%</td></tr>
                    <tr><td>WACC</td><td>${this.assumptions.wacc}%</td></tr>
                    <tr><td>Required Return</td><td>${this.assumptions.requiredReturn}%</td></tr>
                    <tr><td>Tax Rate</td><td>${this.assumptions.taxRate}%</td></tr>
                </table>
            </div>
        </body>
        </html>`;
    }

    showStatus(message, type) {
        const statusElement = document.getElementById('status-message');
        statusElement.textContent = message;
        statusElement.className = `status-message ${type}`;
        statusElement.classList.remove('hidden');

        // Auto-hide after 5 seconds
        setTimeout(() => {
            statusElement.classList.add('hidden');
        }, 5000);
    }

    showLoading(show) {
        const loadBtn = document.getElementById('load-data-btn');
        if (show) {
            loadBtn.textContent = 'Loading...';
            loadBtn.disabled = true;
        } else {
            loadBtn.textContent = 'Load Company Data';
            loadBtn.disabled = false;
        }
    }

    clearDisplay() {
        // Clear company info
        document.getElementById('company-name').textContent = '--';
        document.getElementById('company-symbol').textContent = '--';
        document.getElementById('company-sector').textContent = '--';
        document.getElementById('company-exchange').textContent = '--';

        // Clear market data
        document.getElementById('current-price').textContent = '--';
        document.getElementById('market-cap').textContent = '--';
        document.getElementById('pe-ratio').textContent = '--';
        document.getElementById('pb-ratio').textContent = '--';
        document.getElementById('ps-ratio').textContent = '--';
        document.getElementById('eps').textContent = '--';

        // Clear financial metrics
        document.getElementById('revenue').textContent = '--';
        document.getElementById('net-income').textContent = '--';
        document.getElementById('ebitda').textContent = '--';
        document.getElementById('roe').textContent = '--';
        document.getElementById('roa').textContent = '--';
        document.getElementById('debt-equity').textContent = '--';

        // Clear valuation results
        document.getElementById('dcf-result').textContent = '--';
        document.getElementById('fcfe-result').textContent = '--';
        document.getElementById('weighted-result').textContent = '--';
        document.getElementById('dcf-diff').textContent = '--';
        document.getElementById('fcfe-diff').textContent = '--';
        document.getElementById('weighted-diff').textContent = '--';

        // Clear summary tab
        document.getElementById('summary-symbol').textContent = '--';
        document.getElementById('summary-name').textContent = '--';
        document.getElementById('summary-sector').textContent = '--';
        document.getElementById('summary-exchange').textContent = '--';
        document.getElementById('summary-price').textContent = '--';
        document.getElementById('summary-market-cap').textContent = '--';
        document.getElementById('summary-pe').textContent = '--';
        document.getElementById('summary-pb').textContent = '--';
        document.getElementById('target-price').textContent = '--';
        document.getElementById('summary-potential').textContent = '--';
        document.getElementById('return-value').textContent = '--';

        // Clear recommendation
        document.getElementById('recommendation').innerHTML = '<span class="status status--warning">--</span>';
        document.getElementById('final-recommendation').innerHTML = '<span class="status status--warning">--</span>';
        document.getElementById('recommendation-reasoning').textContent = 'Please load company data to receive investment recommendations.';
        document.getElementById('confidence-level').textContent = '--';

        // Disable export button
        document.getElementById('export-report-btn').disabled = true;

        // Clear valuation results
        this.valuationResults = null;
    }

    // Utility functions for formatting
    formatCurrency(value) {
        if (!value || isNaN(value)) return '--';
        return new Intl.NumberFormat('vi-VN', {
            style: 'currency',
            currency: 'VND',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(value);
    }

    formatLargeNumber(value) {
        if (!value || isNaN(value)) return '--';
        
        if (value >= 1e12) {
            return `${(value / 1e12).toFixed(1)} trillion`;
        } else if (value >= 1e9) {
            return `${(value / 1e9).toFixed(1)} billion`;
        } else if (value >= 1e6) {
            return `${(value / 1e6).toFixed(1)} million`;
        } else {
            return this.formatCurrency(value);
        }
    }

    formatNumber(value) {
        if (!value || isNaN(value)) return '--';
        return value.toFixed(2);
    }

    formatPercent(value) {
        if (!value || isNaN(value)) return '--';
        return `${value.toFixed(1)}%`;
    }

    updateOverviewDisplay(data) {
        // Update company info
        document.getElementById('company-name').textContent = data.name || '--';
        document.getElementById('company-symbol').textContent = data.symbol || '--';
        document.getElementById('company-sector').textContent = data.sector || '--';
        document.getElementById('company-exchange').textContent = data.exchange || '--';

        // Update market data
        document.getElementById('current-price').textContent = this.formatCurrency(data.current_price);
        document.getElementById('market-cap').textContent = this.formatLargeNumber(data.market_cap);
        document.getElementById('pe-ratio').textContent = this.formatNumber(data.pe_ratio);
        document.getElementById('pb-ratio').textContent = this.formatNumber(data.pb_ratio);
        document.getElementById('ps-ratio').textContent = this.formatNumber(data.ps_ratio);
        document.getElementById('eps').textContent = this.formatCurrency(data.eps);

        // Update financial metrics
        document.getElementById('revenue').textContent = this.formatLargeNumber(data.revenue_ttm);
        document.getElementById('net-income').textContent = this.formatLargeNumber(data.net_income_ttm);
        document.getElementById('ebitda').textContent = this.formatLargeNumber(data.ebitda);
        document.getElementById('roe').textContent = this.formatPercent(data.roe);
        document.getElementById('roa').textContent = this.formatPercent(data.roa);
        document.getElementById('debt-equity').textContent = this.formatNumber(data.debt_to_equity);

        // Update summary tab with the same data
        document.getElementById('summary-symbol').textContent = data.symbol || '--';
        document.getElementById('summary-name').textContent = data.name || '--';
        document.getElementById('summary-sector').textContent = data.sector || '--';
        document.getElementById('summary-exchange').textContent = data.exchange || '--';
        document.getElementById('summary-price').textContent = this.formatCurrency(data.current_price);
        document.getElementById('summary-market-cap').textContent = this.formatLargeNumber(data.market_cap);
        document.getElementById('summary-pe').textContent = this.formatNumber(data.pe_ratio);
        document.getElementById('summary-pb').textContent = this.formatNumber(data.pb_ratio);
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    new StockValuationApp();
});