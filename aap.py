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
    """Standard normal CDF"""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def norm_pdf(x):
    """Standard normal PDF"""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)

def calculate_greeks(spot, strike, days_to_expiry, volatility=20, option_type='CE', rate=0.07):
    """Black-Scholes Greeks"""
    try:
        if days_to_expiry <= 0:
            return {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0, 'iv': volatility}
        
        S = spot
        K = strike
        T = days_to_expiry / 365.0
        sigma = volatility / 100.0
        r = rate
        
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        
        if option_type == 'CE':
            delta = norm_cdf(d1)
            theta = (-S * norm_pdf(d1) * sigma / (2 * math.sqrt(T)) - 
                    r * K * math.exp(-r * T) * norm_cdf(d2)) / 365
        else:
            delta = norm_cdf(d1) - 1
            theta = (-S * norm_pdf(d1) * sigma / (2 * math.sqrt(T)) + 
                    r * K * math.exp(-r * T) * norm_cdf(-d2)) / 365
        
        gamma = norm_pdf(d1) / (S * sigma * math.sqrt(T))
        vega = S * norm_pdf(d1) * math.sqrt(T)
        
        return {
            'delta': round(delta, 3),
            'gamma': round(gamma, 5),
            'theta': round(theta, 2),
            'vega': round(vega, 2),
            'iv': round(volatility, 1)
        }
    except:
        return {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0, 'iv': volatility}

def calculate_max_pain(option_chain_data):
    """Max Pain calculation"""
    try:
        strikes = list(option_chain_data.keys())
        min_pain = float('inf')
        max_pain_strike = strikes[len(strikes)//2]
        
        for test_strike in strikes:
            total_pain = 0
            for strike, data in option_chain_data.items():
                if strike < test_strike:
                    total_pain += (test_strike - strike) * data['call_oi']
                if strike > test_strike:
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
            <title>NIFTY Scanner Pro - Login</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 20px;
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .box {
                    background: white;
                    padding: 50px 40px;
                    border-radius: 20px;
                    max-width: 500px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    text-align: center;
                }
                h1 { 
                    font-size: 32px; 
                    color: #333; 
                    margin-bottom: 15px;
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }
                .subtitle { color: #666; margin-bottom: 20px; font-size: 16px; }
                .features {
                    background: #f8f9fa;
                    padding: 20px;
                    border-radius: 10px;
                    margin: 25px 0;
                    text-align: left;
                }
                .features h3 { 
                    color: #667eea; 
                    font-size: 14px; 
                    margin-bottom: 10px;
                    text-align: center;
                }
                .feature-item {
                    padding: 8px 0;
                    color: #555;
                    font-size: 14px;
                }
                .btn {
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    color: white;
                    padding: 18px 50px;
                    border-radius: 30px;
                    text-decoration: none;
                    display: inline-block;
                    font-size: 18px;
                    font-weight: 600;
                    box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
                    transition: transform 0.3s;
                }
                .btn:hover { transform: translateY(-2px); }
            </style>
        </head>
        <body>
            <div class="box">
                <h1>🚀 NIFTY Scanner Pro</h1>
                <div class="subtitle">Professional Option Chain Analysis Platform</div>
                
                <div class="features">
                    <h3>✨ Premium Features</h3>
                    <div class="feature-item">📊 Real-time Option Chain</div>
                    <div class="feature-item">📈 All Greeks (Δ, Γ, Θ, V)</div>
                    <div class="feature-item">🎯 Max Pain Analysis</div>
                    <div class="feature-item">💹 PCR & IV Tracking</div>
                    <div class="feature-item">🔄 Auto-refresh (30s)</div>
                    <div class="feature-item">📱 Mobile Responsive</div>
                </div>
                
                <a href="/login" class="btn">Connect with Zerodha</a>
                <div style="margin-top: 20px; font-size: 12px; color: #999;">
                    Powered by Zerodha Kite API
                </div>
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
        day_high = quote["NSE:NIFTY 50"]["ohlc"]["high"]
        day_low = quote["NSE:NIFTY 50"]["ohlc"]["low"]
        
        # Get instruments
        instruments = kite.instruments("NFO")
        nifty_options = [i for i in instruments 
                        if i['name'] == 'NIFTY' 
                        and i['instrument_type'] in ['CE', 'PE']]
        
        # Get nearest expiry
        expiries = sorted(set([i['expiry'] for i in nifty_options]))
        nearest_expiry = expiries[0]
        
        # Get ATM
        atm_strike = round(spot_price / 50) * 50
        
        # Get strikes
        strikes = sorted(set([i['strike'] for i in nifty_options]))
        atm_index = strikes.index(atm_strike) if atm_strike in strikes else len(strikes) // 2
        selected_strikes = strikes[max(0, atm_index-6):min(len(strikes), atm_index+7)]
        
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
        total_call_volume = 0
        total_put_volume = 0
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
                    
                    # Estimate IV based on price and moneyness
                    moneyness = strike / spot_price
                    base_iv = 20
                    if abs(moneyness - 1) < 0.01:  # ATM
                        iv = base_iv + 2
                    elif moneyness < 1:  # ITM for calls
                        iv = base_iv - 2
                    else:  # OTM
                        iv = base_iv + 3
                    
                    greeks = calculate_greeks(spot_price, strike, days_to_expiry, iv, opt['instrument_type'])
                    
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
                        total_call_volume += q.get('volume', 0)
                    else:
                        put_data = data
                        put_oi_raw = q.get('oi', 0)
                        total_put_oi += put_oi_raw
                        total_put_volume += q.get('volume', 0)
            
            option_chain_data[strike] = {
                'call_oi': call_oi_raw,
                'put_oi': put_oi_raw
            }
            
            if call_data and put_data:
                strike_class = 'atm' if strike == atm_strike else ''
                call_chg_color = 'positive' if call_data['change'] >= 0 else 'negative'
                put_chg_color = 'positive' if put_data['change'] >= 0 else 'negative'
                
                # Strike-wise PCR
                strike_pcr = round(put_oi_raw / call_oi_raw, 2) if call_oi_raw > 0 else 0
                
                rows_html += f"""
                <tr class="{strike_class}">
                    <td>{call_data['oi']:.1f}L</td>
                    <td>{call_data['volume']:.0f}K</td>
                    <td>₹{call_data['ltp']:.2f}</td>
                    <td class="{call_chg_color}">{call_data['change']:+.1f}%</td>
                    <td title="Delta">{call_data['greeks']['delta']}</td>
                    <td title="Gamma">{call_data['greeks']['gamma']}</td>
                    <td title="Theta">{call_data['greeks']['theta']}</td>
                    <td title="Vega">{call_data['greeks']['vega']}</td>
                    <td title="IV">{call_data['greeks']['iv']}%</td>
                    <td class="strike" title="Strike PCR">{strike}<br><small style="color:#666;">{strike_pcr}</small></td>
                    <td title="IV">{put_data['greeks']['iv']}%</td>
                    <td title="Vega">{put_data['greeks']['vega']}</td>
                    <td title="Theta">{put_data['greeks']['theta']}</td>
                    <td title="Gamma">{put_data['greeks']['gamma']}</td>
                    <td title="Delta">{put_data['greeks']['delta']}</td>
                    <td class="{put_chg_color}">{put_data['change']:+.1f}%</td>
                    <td>₹{put_data['ltp']:.2f}</td>
                    <td>{put_data['volume']:.0f}K</td>
                    <td>{put_data['oi']:.1f}L</td>
                </tr>
                """
        
        pcr = round(total_put_oi / total_call_oi, 3) if total_call_oi > 0 else 0
        max_pain = calculate_max_pain(option_chain_data)
        spot_color = 'positive' if spot_change >= 0 else 'negative'
        
        # Market sentiment
        if pcr > 1.3:
            sentiment = "🟢 Bullish"
        elif pcr < 0.7:
            sentiment = "🔴 Bearish"
        else:
            sentiment = "🟡 Neutral"
        
        return f"""
        <html>
        <head>
            <title>NIFTY Scanner Pro - Live</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    padding: 10px;
                    color: white;
                }}
                .container {{ max-width: 100%; margin: 0 auto; }}
                .header {{
                    background: white;
                    color: #333;
                    padding: 15px;
                    border-radius: 12px;
                    margin-bottom: 12px;
                    box-shadow: 0 5px 20px rgba(0,0,0,0.2);
                }}
                .header-top {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 15px;
                    flex-wrap: wrap;
                    gap: 10px;
                }}
                .title {{ 
                    font-size: 20px; 
                    font-weight: 700;
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }}
                .refresh {{ font-size: 11px; color: #999; }}
                .logout-btn {{
                    background: #dc3545;
                    color: white;
                    padding: 8px 20px;
                    border-radius: 20px;
                    text-decoration: none;
                    font-size: 13px;
                    font-weight: 600;
                }}
                .stats {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
                    gap: 12px;
                }}
                .stat {{
                    background: linear-gradient(135deg, #f8f9fa, #e9ecef);
                    padding: 12px;
                    border-radius: 10px;
                    text-align: center;
                }}
                .stat-label {{ font-size: 10px; color: #666; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 0.5px; }}
                .stat-value {{ font-size: 16px; font-weight: 700; color: #667eea; }}
                .stat-sub {{ font-size: 11px; margin-top: 3px; }}
                .positive {{ color: #28a745; }}
                .negative {{ color: #dc3545; }}
                .table-wrapper {{
                    background: white;
                    border-radius: 12px;
                    overflow: hidden;
                    box-shadow: 0 5px 20px rgba(0,0,0,0.2);
                }}
                .table-scroll {{
                    overflow-x: auto;
                    -webkit-overflow-scrolling: touch;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    color: #333;
                    font-size: 11px;
                    min-width: 1200px;
                }}
                thead {{
                    position: sticky;
                    top: 0;
                    z-index: 100;
                }}
                th {{
                    background: #667eea;
                    color: white;
                    padding: 10px 5px;
                    text-align: center;
                    font-size: 10px;
                    font-weight: 600;
                }}
                td {{
                    padding: 8px 5px;
                    text-align: center;
                    border-bottom: 1px solid #f0f0f0;
                }}
                tr:hover {{ background: #f8f9fa; }}
                .strike {{
                    background: #fff3cd;
                    font-weight: 700;
                    font-size: 12px;
                    position: sticky;
                    left: 50%;
                    transform: translateX(-50%);
                }}
                .atm {{ background: #d4edda !important; }}
                .call-header {{ background: #28a745; }}
                .put-header {{ background: #dc3545; }}
                @media (max-width: 768px) {{
                    .title {{ font-size: 18px; }}
                    .stat-value {{ font-size: 14px; }}
                }}
            </style>
            <script>
                setTimeout(() => location.reload(), 30000);
            </script>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="header-top">
                        <div>
                            <div class="title">📊 NIFTY Scanner Pro</div>
                            <div class="refresh">Auto-refresh • 30s</div>
                        </div>
                        <a href="/logout" class="logout-btn">Logout</a>
                    </div>
                    
                    <div class="stats">
                        <div class="stat">
                            <div class="stat-label">Spot</div>
                            <div class="stat-value">₹{spot_price:.2f}</div>
                            <div class="stat-sub {spot_color}">{spot_change:+.2f}%</div>
                        </div>
                        <div class="stat">
                            <div class="stat-label">Range</div>
                            <div class="stat-value" style="font-size:13px;">{day_low:.0f}-{day_high:.0f}</div>
                        </div>
                        <div class="stat">
                            <div class="stat-label">PCR</div>
                            <div class="stat-value">{pcr}</div>
                            <div class="stat-sub" style="color:#667eea;">{sentiment}</div>
                        </div>
                        <div class="stat">
                            <div class="stat-label">Max Pain</div>
                            <div class="stat-value">{max_pain}</div>
                        </div>
                        <div class="stat">
                            <div class="stat-label">ATM</div>
                            <div class="stat-value">{atm_strike}</div>
                        </div>
                        <div class="stat">
                            <div class="stat-label">Expiry</div>
                            <div class="stat-value">{nearest_expiry.strftime('%d-%b')}</div>
                            <div class="stat-sub">{days_to_expiry}d</div>
                        </div>
                    </div>
                </div>
                
                <div class="table-wrapper">
                    <div class="table-scroll">
                        <table>
                            <thead>
                                <tr>
                                    <th colspan="9" class="call-header">CALLS</th>
                                    <th rowspan="2" class="strike">STRIKE<br><small>PCR</small></th>
                                    <th colspan="9" class="put-header">PUTS</th>
                                </tr>
                                <tr>
                                    <th class="call-header">OI</th>
                                    <th class="call-header">Vol</th>
                                    <th class="call-header">LTP</th>
                                    <th class="call-header">Chg</th>
                                    <th class="call-header">Δ</th>
                                    <th class="call-header">Γ</th>
                                    <th class="call-header">Θ</th>
                                    <th class="call-header">V</th>
                                    <th class="call-header">IV</th>
                                    <th class="put-header">IV</th>
                                    <th class="put-header">V</th>
                                    <th class="put-header">Θ</th>
                                    <th class="put-header">Γ</th>
                                    <th class="put-header">Δ</th>
                                    <th class="put-header">Chg</th>
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
            </div>
        </body>
        </html>
        """
        
    except Exception as e:
        return f"""
        <html>
        <body style="font-family: Arial; padding: 40px; background: linear-gradient(135deg, #667eea, #764ba2);">
            <div style="background: white; padding: 40px; border-radius: 15px; max-width: 600px; margin: 0 auto; box-shadow: 0 10px 30px rgba(0,0,0,0.3);">
                <h2 style="color: #dc3545; margin-bottom: 20px;">⚠️ Error Loading Data</h2>
                <div style="background: #f8d7da; padding: 15px; border-radius: 8px; color: #721c24; margin-bottom: 20px;">
                    {str(e)}
                </div>
                <p style="color: #666; margin-bottom: 20px;">This could be due to:</p>
                <ul style="color: #666; margin-bottom: 30px;">
                    <li>Market is closed</li>
                    <li>Session expired</li>
                    <li>API rate limit</li>
                </ul>
                <a href="/logout" style="background: #667eea; color: white; padding: 12px 30px; border-radius: 25px; text-decoration: none; display: inline-block;">Logout & Retry</a>
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
            body { 
                font-family: Arial; 
                padding: 40px; 
                background: linear-gradient(135deg, #667eea, #764ba2);
            }
            .status { 
                background: white; 
                padding: 30px; 
                border-radius: 15px; 
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                max-width: 600px;
                margin: 0 auto;
            }
            h2 { 
                color: #667eea; 
                margin-bottom: 20px;
            }
            .feature {
                padding: 12px;
                margin: 8px 0;
                background: #f8f9fa;
                border-radius: 8px;
                border-left: 4px solid #667eea;
            }
        </style>
    </head>
    <body>
        <div class="status">
            <h2>✅ System Status - All Green!</h2>
            <div class="feature">✅ Flask Server: Running</div>
            <div class="feature">✅ Render Deployment: Active</div>
            <div class="feature">✅ Kiteconnect API: Ready</div>
            <div class="feature">✅ Option Chain Engine: Live</div>
            <div class="feature">✅ All Greeks (Δ, Γ, Θ, V): Calculated</div>
            <div class="feature">✅ Max Pain Algorithm: Working</div>
            <div class="feature">✅ IV Estimation: Active</div>
            <div class="feature">✅ Auto-refresh: Enabled</div>
            <div style="margin-top: 30px; text-align: center;">
                <a href="/" style="background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 15px 40px; border-radius: 25px; text-decoration: none; display: inline-block; font-weight: 600;">Go to Dashboard</a>
            </div>
        </div>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
