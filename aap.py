from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return """
    <html>
    <head>
        <title>NIFTY Scanner</title>
        <style>
            body {
                font-family: Arial;
                background: linear-gradient(135deg, #667eea, #764ba2);
                padding: 40px;
                text-align: center;
                color: white;
            }
            .box {
                background: white;
                color: #333;
                padding: 40px;
                border-radius: 15px;
                max-width: 600px;
                margin: 0 auto;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            }
            .btn {
                background: #667eea;
                color: white;
                padding: 12px 30px;
                border-radius: 25px;
                text-decoration: none;
                display: inline-block;
                margin-top: 20px;
            }
        </style>
    </head>
    <body>
        <div class="box">
            <h1>🎉 NIFTY Option Scanner</h1>
            <p>Successfully deployed on Render!</p>
            <p>Spot Price: ₹25,706</p>
            <a href="/test" class="btn">Test Page</a>
        </div>
    </body>
    </html>
    """

@app.route('/test')
def test():
    return """
    <html>
    <head>
        <style>
            body { font-family: Arial; padding: 40px; }
            .status { background: #f0f0f0; padding: 20px; border-radius: 10px; }
        </style>
    </head>
    <body>
        <h2>✅ System Check</h2>
        <div class="status">
            <p>✅ Flask: Working</p>
            <p>✅ Render: Deployed</p>
            <p>✅ Routes: Active</p>
        </div>
        <p><a href="/">Go Home</a></p>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
