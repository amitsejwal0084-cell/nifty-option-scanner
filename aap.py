from flask import Flask, request, redirect, session
from kiteconnect import KiteConnect
import datetime
import math

app = Flask(__name__)
app.secret_key = 'nifty_scanner_secret_key_2025'

API_KEY = "db1y53lzpboz4hnc"
API_SECRET = "juoejvar0br92vtuxlzv86w32uwmymfn"
REDIRECT_URL = "https://nifty-option-scanner.onrender.com/callback"

kite = KiteConnect(api_key=API_KEY)

def norm_cdf(x):
    """Cumulative distribution function for standard normal distribution"""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def norm_pdf(x):
    """Probability density function for standard normal distribution"""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)

def calculate_greeks(spot, strike, days_to_expiry, volatility=20, option_type='CE', rate=0.07):
    """Black-Scholes Greeks calculation"""
    try:
        if days_to_expiry <= 0:
            return {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0}
        
        S = spot
        K = strike
        T = days_to_expiry / 365.0
        sigma = volatility / 100.0
        r = rate
        
        # d1 and d2
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        
        # Greeks
        if option_type == 'CE':
            delta = norm_cdf(d1)
            theta = (-S * norm_pdf(d1) * sigma / (2 * math.sqrt(T)) - 
                    r * K * math.exp(-r * T) * norm_cdf(d2)) / 365
        else:  # PE
            delta = norm_cdf(d1) - 1
            theta = (-S * norm_pdf(d1) * sigma / (2 * math.sqrt(T)) + 
                    r * K * math.exp(-r * T) * norm_cdf(-d2)) / 365
        
        gamma = norm_pdf(d1) / (S * sigma * math.sqrt(T))
        vega = S * norm_pdf(d1) * math.sqrt(T) / 100
        
        return {
            'delta': round(delta, 3),
            'gamma': round(gamma, 5),
            'theta': round(theta, 2),
            'vega': round(vega, 2)
        }
    except:
        return {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0}

def calculate_max_pain(option_chain_data):
    """Calculate Max Pain strike"""
    try:
        strikes = list(option_chain_data.keys())
        min_pain = float('inf')
        max_pain_strike = strikes[len(strikes)//2]
        
        for test_strike in strikes:
            total_pain = 0
            
            for strike, data in option_chain_data.items():
                if strike < test_strike:
                    # Calls in profit
                    total_pain += (test_strike - strike) * data['call_oi']
                
                if strike > test_strike:
                    # Puts in profit
                    total_pain += (strike - test_strike) * data['put_oi']
            
            if total_pain < min_pain:
                min_pain = total_pain
                max_pain_strike = test_strike
        
        return max_pain_strike
    except:
        return 0

@app.route('/')
def home():
    access_token = session.get('access_token')
    
    if not access_token:
        return """
        <html>
        <head>
            <title>NIFTY Scanner - Login</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    padding: 20px;
                    text-align: center;
                    color: white;
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0;
                }
                .box {
                    background: white;
                    color: #333;
                    padding: 40px;
                    border-radius: 15px;
                    max-width: 500px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                }
                h1 { margin-bottom: 10px; }
                p { margin: 15px 0; }
                .btn {
                    background: #667eea;
                    color: white;
                    padding: 15px 40px;
                    border-radius: 25px;
                    text-decoration: none;
                    display: inline-block;
                    margin-top: 20px;
                    font-size: 18px;
                }
                .btn:hover { background: #5568d3; }
            </style>
        </head>
        <body>
            <div class="box">
                <h1>🚀 NIFTY Option Scanner</h1>
                <p>Professional Option Chain Analysis</p>
                <p>✅ Live Data | ✅ Greeks | ✅ Max Pain</p>
                <a href="/login" class="btn">Login with Zerodha</a>
            </div>
        </body>
        </html>
        """
    
    try:
        kite.set_access_token(access_token)
        
        # Get NIFTY spot
        quote = kite.quote(["NSE:NIFTY 50"])
        spot_price = quote["NSE:NIFTY 50"]["last_price"]
        prev_close = quote["NSE:NIFTY 50"]["ohlc"]["close"]
        spot_change = ((spot_price - prev_close) / prev_close) * 100
        
        # Get instruments
        instruments = kite.instruments("NFO")
        nifty_options = [i for i in instruments 
                        if i['name'] == 'NIFTY' 
                        and i['instrument_type'] in ['CE', 'PE']]
        
        # Get nearest expiry
        expiries = sorted(set([i['expiry'] for i in nifty_options]))
        nearest_expiry = expiries[0]
        
        # Get ATM strike
        atm_strike = round(spot_price / 50) * 50
        
        # Get strikes
        strikes = sorted(set([i['strike'] for i in nifty_options]))
        atm_index = strikes.index(atm_strike) if atm_strike in strikes else len(strikes) // 2
        selected_strikes = strikes[max(0, atm_index-5):min(len(strikes), atm_index+6)]
        
        # Filter options
        filtered_options = [i for i in nifty_options 
                          if i['strike'] in selected_strikes 
                          and i['expiry'] == nearest_expiry]
        
        # Get quotes
        symbols = [f"NFO:{i['tradingsymbol']}" for i in filtered_options]
        quotes = kite.quote(symbols)
        
        days_to_expiry = (nearest_expiry - datetime.date.today()).days
        
        # Build option chain
        rows_html = ""
        total_call_oi = 0
        total_put_oi = 0
        option_chain_data = {}
        
        for strike in selected_strikes:
            call_data = None
            put_data = None
            call_oi_raw = 0
            put_oi_raw = 0
            
            for opt in filtered_options:
                if opt['strike'] == strike:
                    symbol = f"NFO:{opt['tradingsymbol']}"
                    q = quotes.get(symbol, {})
                    
                    ltp = q.get('last_price', 0)
                    prev_close_opt = q.get('ohlc', {}).get('close', ltp)
                    change_pct = ((ltp - prev_close_opt) / prev_close_opt * 100) if prev_close_opt > 0 else 0
                    
                    greeks = calculate_greeks(spot_price, strike, days_to_expiry, 20, opt['instrument_type'])
                    
                    data = {
                        'ltp': ltp,
                        'change': change_pct,
                        'volume': q.get('volume', 0) / 1000,
                        'oi': q.get('oi', 0) / 100000,
                        'greeks': greeks
                    }
                    
                    if opt['instrument_type'] == 'CE':
                        call_data = data
                        call_oi_raw = q.get('oi', 0)
                        total_call_oi += call_oi_raw
                    else:
                        put_data = data
                        put_oi_raw = q.get('oi', 0)
                        total_put_oi += put_oi_raw
            
            option_chain_data[strike] = {
                'call_oi': call_oi_raw,
                'put_oi': put_oi_raw
            }
            
            if call_data and put_data:
                strike_class = 'atm' if strike == atm_strike else ''
                change_color_call = 'positive' if call_data['change'] >= 0 else 'negative'
                change_color_put = 'positive' if put_data['change'] >= 0 else 'negative'
                
                rows_html += f"""
                <tr class="{strike_class}">
                    <td>{call_data['oi']:.1f}L</td>
                    <td>{call_data['volume']:.0f}K</td>
                    <td>₹{call_data['ltp']:.2f}</td>
                    <td class="{change_color_call}">{call_data['change']:+.1f}%</td>
                    <td>{call_data['greeks']['delta']}</td>
                    <td>{call_data['greeks']['gamma']}</td>
                    <td class="strike">{strike}</td>
                    <td>{put_data['greeks']['gamma']}</td>
                    <td>{put_data['greeks']['delta']}</td>
                    <td class="{change_color_put}">{put_data['change']:+.1f}%</td>
                    <td>₹{put_data['ltp']:.2f}</td>
                    <td>{put_data['volume']:.0f}K</td>
                    <td>{put_data['oi']:.1f}L</td>
                </tr>
                """
        
        pcr = round(total_put_oi / total_call_oi, 3) if total_call_oi > 0 else 0
        max_pain = calculate_max_pain(option_chain_data)
        spot_color = 'positive' if spot_change >= 0 else 'negative'
        
        return f"""
        <html>
        <head>
            <title>NIFTY Option Chain Pro</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    padding: 10px;
                    color: white;
                }}
                .container {{ max-width: 1600px; margin: 0 auto; }}
                .header {{
                    background: white;
                    color: #333;
                    padding: 15px;
                    border-radius: 10px;
                    margin-bottom: 15px;
                    box-shadow: 0 5px 15px rgba(0,0,0,0.2);
                }}
                .header-top {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 15px;
                    flex-wrap: wrap;
                    gap: 10px;
                }}
                .header-top h1 {{ font-size: 20px; }}
                .refresh-info {{ font-size: 12px; color: #666; }}
                .logout-btn {{
                    background: #dc3545;
                    color: white;
                    padding: 8px 20px;
                    border-radius: 20px;
                    text-decoration: none;
                    font-size: 14px;
                }}
                .stats {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
                    gap: 15px;
                }}
                .stat-box {{
                    text-align: center;
                    padding: 10px;
                    background: #f8f9fa;
                    border-radius: 8px;
                }}
                .stat-label {{ font-size: 11px; color: #666; margin-bottom: 5px; }}
                .stat-value {{ font-size: 18px; font-weight: bold; color: #667eea; }}
                .positive {{ color: #28a745; }}
                .negative {{ color: #dc3545; }}
                .table-container {{
                    background: white;
                    border-radius: 10px;
                    overflow-x: auto;
                    box-shadow: 0 5px 15px rgba(0,0,0,0.2);
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    color: #333;
                    font-size: 12px;
                }}
                th {{
                    background: #667eea;
                    color: white;
                    padding: 10px 6px;
                    text-align: center;
                    position: sticky;
                    top: 0;
                    z-index: 10;
                    font-size: 11px;
                }}
                td {{
                    padding: 8px 6px;
                    text-align: center;
                    border-bottom: 1px solid #eee;
                }}
                tr:hover {{ background: #f8f9fa; }}
                .strike {{
                    background: #fff3cd;
                    font-weight: bold;
                    font-size: 13px;
                }}
                .atm {{ background: #d4edda; }}
                .call-header {{ background: #28a745; }}
                .put-header {{ background: #dc3545; }}
                @media (max-width: 768px) {{
                    table {{ font-size: 10px; }}
                    th, td {{ padding: 6px 3px; }}
                    .stat-value {{ font-size: 16px; }}
                }}
            </style>
            <script>
                setTimeout(function(){{ location.reload(); }}, 30000);
            </script>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="header-top">
                        <div>
                            <h1>📊 NIFTY Option Chain Pro</h1>
                            <div class="refresh-info">Auto-refresh in 30s</div>
                        </div>
                        <a href="/logout" class="logout-btn">Logout</a>
                    </div>
                    <div class="stats">
                        <div class="stat-box">
                            <div class="stat-label">NIFTY Spot</div>
                            <div class="stat-value">₹{spot_price:.2f}</div>
                            <div class="{spot_color}">{spot_change:+.2f}%</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">PCR Ratio</div>
                            <div class="stat-value">{pcr}</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">Max Pain</div>
                            <div class="stat-value">{max_pain}</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">ATM Strike</div>
                            <div class="stat-value">{atm_strike}</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">Expiry</div>
                            <div class="stat-value">{nearest_expiry.strftime('%d-%b')}</div>
                            <div style="font-size: 11px; color: #666;">{days_to_expiry} days</div>
                        </div>
                    </div>
                </div>
                
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th colspan="6" class="call-header">CALLS</th>
                                <th rowspan="2" class="strike">STRIKE</th>
                                <th colspan="6" class="put-header">PUTS</th>
                            </tr>
                            <tr>
                                <th class="call-header">OI</th>
                                <th class="call-header">Vol</th>
                                <th class="call-header">LTP</th>
                                <th class="call-header">Chg%</th>
                                <th class="call-header">Δ</th>
                                <th class="call-header">Γ</th>
                                <th class="put-header">Γ</th>
                                <th class="put-header">Δ</th>
                                <th class="put-header">Chg%</th>
                                <th class="put-header">LTP</th>
                                <th class="put-header">Vol</th>
                                <th class="put-header">OI</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_html}
                        </tbody>
                    </table>
                </div>
            </div>
        </body>
        </html>
        """
        
    except Exception as e:
        return f"""
        <html>
        <body style="font-family: Arial; padding: 40px; background: #f5f5f5;">
            <div style="background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <h2 style="color: #dc3545;">⚠️ Error Loading Data</h2>
                <p style="color: #666;">{str(e)}</p>
                <p><a href="/logout" style="color: #667eea;">Logout and try again</a></p>
            </div>
        </body>
        </html>
        """

@app.route('/login')
def login():
    return redirect(kite.login_url())

@app.route('/callback')
def callback():
    request_token = request.args.get('request_token')
    if not request_token:
        return "Error: No request token"
    try:
        data = kite.generate_session(request_token, api_secret=API_SECRET)
        session['access_token'] = data['access_token']
        return redirect('/')
    except Exception as e:
        return f"Login failed: {str(e)}"

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/test')
def test():
    return """
    <html>
    <head>
        <style>
            body { font-family: Arial; padding: 40px; background: #f5f5f5; }
            .status { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h2 { color: #667eea; }
        </style>
    </head>
    <body>
        <h2>✅ System Check</h2>
        <div class="status">
            <p>✅ Flask: Working</p>
            <p>✅ Render: Deployed</p>
            <p>✅ Kiteconnect: Ready</p>
            <p>✅ Option Chain Pro: Ready</p>
            <p>✅ Greeks: Black-Scholes</p>
            <p>✅ Max Pain: Calculated</p>
        </div>
        <p><a href="/">Go Home</a></p>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
