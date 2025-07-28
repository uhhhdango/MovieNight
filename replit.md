# Discord Movie Night Bot

## Overview

This is a Discord bot application designed to create movie night announcements through slash commands. The bot is built using Python with the discord.py library and provides a simple interface for users to schedule movie events with timestamps.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

The application follows a simple monolithic architecture with two main Python files:

- **bot.py**: Contains the core bot logic, command definitions, and Discord event handlers
- **main.py**: Entry point that handles environment setup and bot initialization

The architecture is straightforward and lightweight, designed for a single-purpose Discord bot without complex state management or external dependencies beyond Discord's API.

## Key Components

### Bot Class (`MovieNightBot`)
- Extends `discord.ext.commands.Bot` 
- Handles Discord intents and command prefix configuration
- Manages slash command synchronization during startup
- Provides connection status logging

### Slash Commands
- `/movie` command: Creates movie night announcements
- Takes movie name and Unix timestamp as parameters
- Includes basic input validation for timestamp format

### Environment Configuration
- Uses `DISCORD_BOT_TOKEN` environment variable for authentication
- Includes error handling for missing token configuration

## Data Flow

1. Bot starts up and authenticates with Discord using provided token
2. Slash commands are synchronized with Discord's API during setup
3. Users invoke `/movie` command with movie name and timestamp
4. Bot validates input parameters (particularly timestamp format)
5. Bot creates and sends movie night announcement (implementation appears incomplete)

## External Dependencies

### Discord API
- Primary integration through discord.py library
- Handles authentication, command registration, and message sending
- Uses Discord's slash command system for user interaction

### Python Standard Library
- `datetime` for timestamp handling
- `os` for environment variable access
- `asyncio` for asynchronous operation support

## Deployment Strategy

The application is designed for simple deployment patterns:

- **Environment Variables**: Uses `DISCORD_BOT_TOKEN` for configuration
- **Single Process**: Runs as a single Python process
- **No Database**: Currently no persistent storage requirements
- **Replit Compatible**: Structure suggests deployment on Replit platform

### Key Considerations
- Bot token security through environment variables
- Simple startup process with error handling
- Lightweight resource requirements
- No external database or storage dependencies

## Notes

The `/movie` command implementation appears to be incomplete in the provided code - the function cuts off during error handling. The bot structure is well-organized for a simple Discord bot but may need completion of the movie announcement functionality.