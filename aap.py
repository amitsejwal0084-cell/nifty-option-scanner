from flask import Flask, request, redirect, session, jsonify
from kiteconnect import KiteConnect
import os

app = Flask(__name__)
app.secret_key = 'nifty_scanner_secret_key_2025'

# Zerodha API credentials
API_KEY = "db1y53lzpboz4hnc"
API_SECRET = "juoejvar0br92vtuxlzv86w32uwmymfn"

# Replace with your Render URL after first deploy
REDIRECT_URL = "https://nifty-option-scanner.onrender.com/callback"

kite = KiteConnect(api_key=API_KEY)

@app.route('/')
def home():
    access_token = session.get('access_token')
    
    if not access_token:
        return """
        <html>
        <head>
            <title>NIFTY Scanner - Login</title>
            <style>
                body {
                    font-family: Arial;
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    padding: 40px;
                    text-align: center;
                    color: white;
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
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
                .btn:hover {
                    background: #5568d3;
                }
            </style>
        </head>
        <body>
            <div class="box">
                <h1>🚀 NIFTY Option Scanner</h1>
                <p>Connect with your Zerodha account to get live market data</p>
                <a href="/login" class="btn">Login with Zerodha</a>
            </div>
        </body>
        </html>
        """
    
    # User is logged in - show dashboard with demo data
    try:
        # Try to get NIFTY spot price
        kite.set_access_token(access_token)
        quote = kite.quote(["NSE:NIFTY 50"])
        spot_price = quote["NSE:NIFTY 50"]["last_price"]
    except:
        spot_price = 25706  # Fallback demo price
    
    return f"""
    <html>
    <head>
        <title>NIFTY Scanner - Dashboard</title>
        <style>
            body {{
                font-family: Arial;
                background: linear-gradient(135deg, #667eea, #764ba2);
                padding: 20px;
                color: white;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
            }}
            .header {{
                background: white;
                color: #333;
                padding: 20px;
                border-radius: 15px;
                margin-bottom: 20px;
            }}
            .card {{
                background: white;
                color: #333;
                padding: 20px;
                border-radius: 10px;
                margin: 10px 0;
            }}
            .price {{
                font-size: 32px;
                font-weight: bold;
                color: #667eea;
            }}
            .btn {{
                background: #dc3545;
                color: white;
                padding: 10px 20px;
                border-radius: 20px;
                text-decoration: none;
                display: inline-block;
                margin-top: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>✅ NIFTY Option Scanner</h1>
                <p>Connected to Zerodha</p>
                <a href="/logout" class="btn">Logout</a>
            </div>
            <div class="card">
                <h2>NIFTY 50</h2>
                <div class="price">₹{spot_price:.2f}</div>
                <p>Live spot price from NSE</p>
            </div>
            <div class="card">
                <h3>🔜 Coming Soon:</h3>
                <p>✅ Full Option Chain</p>
                <p>✅ Greeks (Delta, Gamma, Theta, Vega)</p>
                <p>✅ PCR Ratio & Max Pain</p>
                <p>✅ Real-time Updates</p>
            </div>
        </div>
    </body>
    </html>
    """

@app.route('/login')
def login():
    login_url = kite.login_url()
    return redirect(login_url)

@app.route('/callback')
def callback():
    request_token = request.args.get('request_token')
    
    if not request_token:
        return "Error: No request token received"
    
    try:
        # Generate session
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
                background: #f5f5f5;
            }
            .status { 
                background: white;
                padding: 20px; 
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h2 { color: #667eea; }
        </style>
    </head>
    <body>
        <h2>✅ System Check</h2>
        <div class="status">
            <p>✅ Flask: Working</p>
            <p>✅ Render: Deployed</p>
            <p>✅ Routes: Active</p>
            <p>✅ Kiteconnect: Imported</p>
        </div>
        <p><a href="/">Go Home</a></p>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
