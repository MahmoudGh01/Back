

import os
from app import app


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))  # Default to 5000 if PORT not found
    app.run(host='0.0.0.0', port=port)
