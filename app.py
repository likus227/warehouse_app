from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Flask Docker App</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
        }
        .status {
            color: #28a745;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🐳 Flask Docker App</h1>
        <p class="status">✓ App is running successfully!</p>
        <p>This Flask application is running inside a Docker container.</p>
        <p>Try the API endpoint: <a href="/api/status">/api/status</a></p>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/status')
def status():
    return jsonify({
        'status': 'running',
        'message': 'Flask app is working in Docker!'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)