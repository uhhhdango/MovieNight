#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Discord Movie Night Bot - Entry point
"""
import asyncio
import os
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from bot import get_bot
from dotenv import load_dotenv

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def log_status(message: str):
    with open("bot_status.log", "a", encoding="utf-8") as f:
        f.write(message + "\n")

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        pass

def run_health_server():
    server = HTTPServer(("0.0.0.0", 8080), HealthHandler)
    server.serve_forever()

def main():
    load_dotenv()

    token = os.getenv('DISCORD_BOT_TOKEN')

    if not token:
        error_msg = "ERROR: DISCORD_BOT_TOKEN environment variable is required!"
        print(error_msg)
        log_status(error_msg)
        return

    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()

    bot = get_bot()

    try:
        startup_msg = "✅ Starting Discord Movie Night Bot..."
        print(startup_msg)
        log_status(startup_msg)
        bot.run(token)
    except Exception as e:
        fail_msg = f"❌ Failed to start bot: {e}"
        print(fail_msg)
        log_status(fail_msg)

if __name__ == "__main__":
    main()
