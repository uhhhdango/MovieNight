#!/usr/bin/env python3
"""
Discord Movie Night Bot - Entry point
"""
import asyncio
import os
from bot import get_bot

def main():
    """Main entry point for the Discord bot"""
    # Get bot token from environment variable
    token = os.getenv('DISCORD_BOT_TOKEN')
    
    if not token:
        print("ERROR: DISCORD_BOT_TOKEN environment variable is required!")
        print("Please set your Discord bot token in the environment variables.")
        return
    
    # Create and run the bot
    bot = get_bot()
    
    try:
        print("Starting Discord Movie Night Bot...")
        bot.run(token)
    except Exception as e:
        print(f"Failed to start bot: {e}")

if __name__ == "__main__":
    main()
