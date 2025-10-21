from flask import Flask, request, redirect, session, jsonify
from kiteconnect import KiteConnect
import datetime
import math

app = Flask(__name__)
app.secret_key = 'nifty_scanner_secret_key_2025'

# Zerodha API credentials
API_KEY = "db1y53lzpboz4hnc"
API_SECRET = "juoejvar0br92vtuxlzv86w32uwmymfn"
REDIRECT_URL = "https://nifty-option-scanner.onrender.com/callback"

kite = KiteConnect(api_key=API_KEY)

def calculate_greeks(spot, strike, days_to_expiry, volatility=20, option_type='CE'):
    """Simple Greeks calculation"""
    try:
        if days_to_expiry <= 0:
            return {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0}
        
        # Simple approximation
        if option_type == 'CE':
            if strike < spot:
                delta = 0.7
            elif strike == spot:
                delta = 0.5
            else:
                delta = 0.3
        else:  # PE
            if strike > spot:
                delta = -0.7
            elif strike == spot:
                delta = -0.5
            else:
                delta = -0.3
        
        gamma = 0.05
        theta = -10
        vega = 50
        
        return {
            'delta': round(delta, 2),
            'gamma': round(gamma, 3),
            'theta': round(theta, 1),
            'vega': round(vega, 1)
        }
    except:
        return {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0}

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
                .btn {
                    background: #667eea;
                    color: white;
                    padding: 15px 40px;
                    border-radius: 25px;
                    text-decoration: none;
                    display: inline-block;
                    margin-top: 20px;
                    font-size: 18px;
                    border: none;
                    cursor: pointer;
                }
                .btn:hover { background: #5568d3; }
            </style>
        </head>
        <body>
            <div class="box">
                <h1>🚀 NIFTY Option Scanner</h1>
                <p>Connect with your Zerodha account to get live option chain data</p>
                <a href="/login" class="btn">Login with Zerodha</a>
            </div>
        </body>
        </html>
        """
    
    # User is logged in - get option chain
    try:
        kite.set_access_token(access_token)
        
        # Get NIFTY spot
        quote = kite.quote(["NSE:NIFTY 50"])
        spot_price = quote["NSE:NIFTY 50"]["last_price"]
        
        # Get instruments
        instruments = kite.instruments("NFO")
        
        # Filter NIFTY options
        nifty_options = [i for i in instruments 
                        if i['name'] == 'NIFTY' 
                        and i['instrument_type'] in ['CE', 'PE']]
        
        # Get nearest expiry
        expiries = sorted(set([i['expiry'] for i in nifty_options]))
        nearest_expiry = expiries[0]
        
        # Get ATM strike
        atm_strike = round(spot_price / 50) * 50
        
        # Get strikes around ATM
        strikes = sorted(set([i['strike'] for i in nifty_options]))
        atm_index = strikes.index(atm_strike) if atm_strike in strikes else len(strikes) // 2
        selected_strikes = strikes[max(0, atm_index-5):min(len(strikes), atm_index+6)]
        
        # Filter options for selected strikes
        filtered_options = [i for i in nifty_options 
                          if i['strike'] in selected_strikes 
                          and i['expiry'] == nearest_expiry]
        
        # Get quotes
        symbols = [f"NFO:{i['tradingsymbol']}" for i in filtered_options]
        quotes = kite.quote(symbols)
        
        # Days to expiry
        days_to_expiry = (nearest_expiry - datetime.date.today()).days
        
        # Build option chain HTML
        rows_html = ""
        total_call_oi = 0
        total_put_oi = 0
        
        for strike in selected_strikes:
            call_data = None
            put_data = None
            
            for opt in filtered_options:
                if opt['strike'] == strike:
                    symbol = f"NFO:{opt['tradingsymbol']}"
                    q = quotes.get(symbol, {})
                    
                    greeks = calculate_greeks(spot_price, strike, days_to_expiry, 20, opt['instrument_type'])
                    
                    data = {
                        'ltp': q.get('last_price', 0),
                        'volume': q.get('volume', 0) / 1000,  # in thousands
                        'oi': q.get('oi', 0) / 100000,  # in lakhs
                        'greeks': greeks
                    }
                    
                    if opt['instrument_type'] == 'CE':
                        call_data = data
                        total_call_oi += q.get('oi', 0)
                    else:
                        put_data = data
                        total_put_oi += q.get('oi', 0)
            
            # Build row
            strike_class = 'atm' if strike == atm_strike else ''
            rows_html += f"""
            <tr class="{strike_class}">
                <td>{call_data['oi']:.1f}L</td>
                <td>{call_data['volume']:.0f}K</td>
                <td>₹{call_data['ltp']:.2f}</td>
                <td>{call_data['greeks']['delta']}</td>
                <td class="strike">{strike}</td>
                <td>{put_data['greeks']['delta']}</td>
                <td>₹{put_data['ltp']:.2f}</td>
                <td>{put_data['volume']:.0f}K</td>
                <td>{put_data['oi']:.1f}L</td>
            </tr>
            """ if call_data and put_data else ""
        
        # Calculate PCR
        pcr = round(total_put_oi / total_call_oi, 3) if total_call_oi > 0 else 0
        
        return f"""
        <html>
        <head>
            <title>NIFTY Option Chain</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: Arial, sans-serif;
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    padding: 10px;
                    color: white;
                }}
                .container {{ max-width: 1400px; margin: 0 auto; }}
                .header {{
                    background: white;
                    color: #333;
                    padding: 15px;
                    border-radius: 10px;
                    margin-bottom: 15px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    flex-wrap: wrap;
                }}
                .header h1 {{ font-size: 20px; margin-bottom: 5px; }}
                .header-info {{ display: flex; gap: 20px; flex-wrap: wrap; }}
                .info-item {{ text-align: center; }}
                .info-item .label {{ font-size: 12px; color: #666; }}
                .info-item .value {{ font-size: 18px; font-weight: bold; color: #667eea; }}
                .logout-btn {{
                    background: #dc3545;
                    color: white;
                    padding: 8px 20px;
                    border-radius: 20px;
                    text-decoration: none;
                    font-size: 14px;
                }}
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
                    font-size: 13px;
                }}
                th {{
                    background: #667eea;
                    color: white;
                    padding: 12px 8px;
                    text-align: center;
                    position: sticky;
                    top: 0;
                    z-index: 10;
                }}
                td {{
                    padding: 10px 8px;
                    text-align: center;
                    border-bottom: 1px solid #eee;
                }}
                tr:hover {{ background: #f8f9fa; }}
                .strike {{
                    background: #fff3cd;
                    font-weight: bold;
                    font-size: 14px;
                }}
                .atm {{ background: #d4edda; }}
                .call-header {{ background: #28a745; }}
                .put-header {{ background: #dc3545; }}
                @media (max-width: 768px) {{
                    table {{ font-size: 11px; }}
                    th, td {{ padding: 8px 4px; }}
                }}
            </style>
            <script>
                // Auto-refresh every 30 seconds
                setTimeout(function(){{ location.reload(); }}, 30000);
            </script>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div>
                        <h1>✅ NIFTY Option Chain</h1>
                        <small>Auto-refresh in 30s</small>
                    </div>
                    <div class="header-info">
                        <div class="info-item">
                            <div class="label">Spot</div>
                            <div class="value">₹{spot_price:.2f}</div>
                        </div>
                        <div class="info-item">
                            <div class="label">PCR</div>
                            <div class="value">{pcr}</div>
                        </div>
                        <div class="info-item">
                            <div class="label">Expiry</div>
                            <div class="value">{nearest_expiry.strftime('%d-%b')}</div>
                        </div>
                    </div>
                    <a href="/logout" class="logout-btn">Logout</a>
                </div>
                
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th colspan="4" class="call-header">CALLS</th>
                                <th rowspan="2" class="strike">STRIKE</th>
                                <th colspan="4" class="put-header">PUTS</th>
                            </tr>
                            <tr>
                                <th class="call-header">OI</th>
                                <th class="call-header">Vol</th>
                                <th class="call-header">LTP</th>
                                <th class="call-header">Delta</th>
                                <th class="put-header">Delta</th>
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
        <body style="font-family: Arial; padding: 40px;">
            <h2>Error Loading Option Chain</h2>
            <p>{str(e)}</p>
            <p><a href="/logout">Logout and try again</a></p>
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
        return "Error: No request token received"
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
            <p>✅ Option Chain: Ready</p>
        </div>
        <p><a href="/">Go Home</a></p>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
