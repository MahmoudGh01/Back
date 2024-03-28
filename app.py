from flask import Flask

app = Flask(__name__)


@app.route('/')
def home():
    return 'Hello, World!'


port = int(os.getenv("PORT", 8000))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=port)
