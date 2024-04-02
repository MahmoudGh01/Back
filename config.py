class Config:
    SECRET_KEY = 'your_secret_key'

    MONGO_URI = "mongodb+srv://mongo:mongo@cluster0.3t1xgux.mongodb.net/?retryWrites=true&w=majority"

    FLASK_JWT_SECRET_KEY = '7e4d21e87dd2238e8cf031df'
    UPLOAD_FOLDER = '/Users/mahmoudgharbi/Documents/Mahmoud/Back/Uploads'

    # Flask-Mail configuration
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 465
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True
    MAIL_USERNAME = 'airecruittn@gmail.com'  # Your Gmail email address
    MAIL_PASSWORD = 'xqoy cere atgg ccxf'  # Your Gmail password
    MAIL_DEFAULT_SENDER = 'airecruittn@gmail.com'  # Default sender

    CLIENT_ID = '104792978938-smu99c48hkqint3g8afkm42ffeuikqig.apps.googleusercontent.com'
    CLIENT_SECRET = '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'
    REDIRECT_URI = 'https://localhost:5000/home'
