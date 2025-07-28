"""
Discord Movie Night Bot
Handles slash commands for creating movie night announcements
"""
import discord
from discord.ext import commands
from datetime import datetime, timezone
import os

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

# Create bot instance
bot = MovieNight()

@bot.tree.command(name="movie", description="Create a movie night announcement")
async def movie_command(interaction: discord.Interaction, name: str, time: str):
    """
    Create a movie night announcement
    
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
                ephemeral=True
            )
            return
        
        # Convert Unix timestamp to datetime
        try:
            movie_datetime = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
        except (ValueError, OSError) as e:
            await interaction.response.send_message(
                "❌ Invalid timestamp! Please provide a valid Unix timestamp.",
                ephemeral=True
            )
            return
        
        # Get current time for relative time calculation
        current_time = datetime.now(timezone.utc)
        time_difference = movie_datetime - current_time
        
        # Format the datetime for display
        formatted_date = movie_datetime.strftime("%A, %B %d, %Y at %I:%M %p")
        
        # Calculate relative time
        relative_time = ""
        total_seconds = int(time_difference.total_seconds())
        
        if total_seconds < 0:
            # Time has passed
            abs_seconds = abs(total_seconds)
            if abs_seconds < 60:
                relative_time = "just passed"
            elif abs_seconds < 3600:
                minutes = abs_seconds // 60
                relative_time = f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            elif abs_seconds < 86400:
                hours = abs_seconds // 3600
                relative_time = f"{hours} hour{'s' if hours != 1 else ''} ago"
            else:
                days = abs_seconds // 86400
                relative_time = f"{days} day{'s' if days != 1 else ''} ago"
        else:
            # Time is in the future
            if total_seconds < 60:
                relative_time = "in less than a minute"
            elif total_seconds < 3600:
                minutes = total_seconds // 60
                relative_time = f"in {minutes} minute{'s' if minutes != 1 else ''}"
            elif total_seconds < 86400:
                hours = total_seconds // 3600
                relative_time = f"in {hours} hour{'s' if hours != 1 else ''}"
            else:
                days = total_seconds // 86400
                relative_time = f"in {days} day{'s' if days != 1 else ''}"
        
        # Get host information
        host_display_name = interaction.user.display_name
        
        # Create the formatted announcement
        announcement = f"""🎬 **Movie Night Hosting!**
🍿 **Host:** {host_display_name}
📽️ **Movie:** *{name}*
🕒 **Time:** {formatted_date} UTC | {relative_time}"""
        
        # Send the announcement
        await interaction.response.send_message(announcement)
        
    except Exception as e:
        print(f"Error in movie command: {e}")
        await interaction.response.send_message(
            "❌ An error occurred while processing your request. Please try again.",
            ephemeral=True
        )

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands
    
    print(f"Command error: {error}")

# Export the bot instance for main.py
def get_bot():
    return bot
