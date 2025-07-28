"""
Discord Movie Night Bot
Handles slash commands for creating movie night announcements
"""
import discord
from discord.ext import commands, tasks
from datetime import datetime, timezone
import os
import asyncio


class MovieNight(commands.Bot):

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        """Setup hook called when bot is starting up"""
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} slash command(s)")
        except Exception as e:
            print(f"Failed to sync commands: {e}")

    async def on_ready(self):
        """Called when bot is ready and connected to Discord"""
        print(f'{self.user} has connected to Discord!')
        print(f'Bot is in {len(self.guilds)} guilds')
        # Start the background task for updating announcements
        if not update_movie_announcements.is_running():
            update_movie_announcements.start()


# Create bot instance
bot = MovieNight()

# Store active movie announcements for updating
active_announcements = {}

def calculate_relative_time(movie_datetime):
    """Calculate relative time string from movie datetime"""
    current_time = datetime.now(timezone.utc)
    time_difference = movie_datetime - current_time
    total_seconds = int(time_difference.total_seconds())
    
    if total_seconds < 0:
        # Time has passed
        abs_seconds = abs(total_seconds)
        if abs_seconds < 60:
            return "just passed"
        elif abs_seconds < 3600:
            minutes = abs_seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif abs_seconds < 86400:
            hours = abs_seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = abs_seconds // 86400
            return f"{days} day{'s' if days != 1 else ''} ago"
    else:
        # Time is in the future
        if total_seconds < 60:
            return "in less than a minute"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            return f"in {minutes} minute{'s' if minutes != 1 else ''}"
        elif total_seconds < 86400:
            hours = total_seconds // 3600
            return f"in {hours} hour{'s' if hours != 1 else ''}"
        else:
            days = total_seconds // 86400
            return f"in {days} day{'s' if days != 1 else ''}"

def create_announcement_text(host_name, movie_name, movie_datetime):
    """Create the formatted announcement text"""
    formatted_date = movie_datetime.strftime("%A, %B %d, %Y at %I:%M %p")
    relative_time = calculate_relative_time(movie_datetime)
    
    return f"""🎬 **Movie Night Hosting!**
🍿 **Host:** {host_name}
📽️ **Movie:** *{movie_name}*
🕒 **Time:** {formatted_date} UTC | {relative_time}"""

@tasks.loop(minutes=1)
async def update_movie_announcements():
    """Update all active movie announcements every minute"""
    current_time = datetime.now(timezone.utc)
    to_remove = []
    
    for message_id, data in active_announcements.items():
        try:
            # Stop updating if movie time has passed by more than 1 hour
            if (current_time - data['movie_datetime']).total_seconds() > 3600:
                to_remove.append(message_id)
                continue
            
            # Get the message and update it
            channel = bot.get_channel(data['channel_id'])
            if channel:
                message = await channel.fetch_message(message_id)
                new_text = create_announcement_text(
                    data['host_name'], 
                    data['movie_name'], 
                    data['movie_datetime']
                )
                await message.edit(content=new_text)
        except (discord.NotFound, discord.Forbidden):
            # Message was deleted or we lost permission
            to_remove.append(message_id)
        except Exception as e:
            print(f"Error updating message {message_id}: {e}")
    
    # Remove expired or failed announcements
    for message_id in to_remove:
        active_announcements.pop(message_id, None)


@bot.tree.command(name="movie",
                  description="Create a movie night announcement")
async def movie_command(interaction: discord.Interaction, name: str,
                        time: str):
    """
    Create a movie night announcement with auto-updating countdown
    
    Args:
        interaction: Discord interaction object
        name: Name of the movie
        time: Unix timestamp for the movie time
    """
    try:
        # Parse Unix timestamp
        try:
            unix_timestamp = int(time)
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid timestamp format! Please provide a valid Unix timestamp.",
                ephemeral=True)
            return

        # Convert Unix timestamp to datetime
        try:
            movie_datetime = datetime.fromtimestamp(unix_timestamp,
                                                    tz=timezone.utc)
        except (ValueError, OSError) as e:
            await interaction.response.send_message(
                "❌ Invalid timestamp! Please provide a valid Unix timestamp.",
                ephemeral=True)
            return

        # Get host information
        host_display_name = interaction.user.display_name

        # Create the formatted announcement using our helper function
        announcement_text = create_announcement_text(host_display_name, name, movie_datetime)

        # Send the announcement
        await interaction.response.send_message(announcement_text)
        
        # Store this announcement for auto-updating
        # Get the message after sending
        message = await interaction.original_response()
        active_announcements[message.id] = {
            'channel_id': interaction.channel.id,
            'host_name': host_display_name,
            'movie_name': name,
            'movie_datetime': movie_datetime
        }

    except Exception as e:
        print(f"Error in movie command: {e}")
        await interaction.response.send_message(
            "❌ An error occurred while processing your request. Please try again.",
            ephemeral=True
        )
        await interaction.response.send_message(
            "❌ An error occurred while processing your request. Please try again.",
            ephemeral=True)


@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands

    print(f"Command error: {error}")


# Export the bot instance for main.py
def get_bot():
    return bot
