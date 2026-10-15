import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Debug mode lets anyone who can reach the server run code, so it stays off
    # unless you set FLASK_DEBUG=1 in .env for development.
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1")