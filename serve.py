"""Run the app with Waitress, a production-grade server.

Use this (not run.py) when publishing through a Cloudflare Tunnel. It listens
on 127.0.0.1 only, so the tunnel is the only way in from the internet.
"""

import os

from waitress import serve

from app import create_app

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    print(f"Serving on http://127.0.0.1:{port}")
    serve(create_app(), host="127.0.0.1", port=port)