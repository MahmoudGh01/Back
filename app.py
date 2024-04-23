import os
from flask import Flask
from flask_cors import CORS

app = Flask(__name__)

port = int(os.getenv("PORT", 8000))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
