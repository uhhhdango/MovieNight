import discord
from discord.ext import commands
import os

# Simple test bot to verify slash command registration
class TestBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        print("Setting up bot...")
        try:
            # Clear existing commands and sync new ones
            self.tree.clear_commands(guild=None)
            synced = await self.tree.sync()
            print(f"Successfully synced {len(synced)} command(s)")
            for cmd in synced:
                print(f"  - {cmd.name}: {cmd.description}")
        except Exception as e:
            print(f"Failed to sync commands: {e}")

    async def on_ready(self):
        print(f'Bot {self.user} is ready!')
        print(f'Connected to {len(self.guilds)} guild(s)')

# Create bot instance
bot = TestBot()

@bot.tree.command(name="movie", description="Create a movie night announcement")
async def movie_test(interaction: discord.Interaction, name: str, time: str):
    """Test movie command"""
    await interaction.response.send_message(f"Test successful! Movie: {name}, Time: {time}")

# Get token from environment
token = os.getenv('DISCORD_BOT_TOKEN')

if __name__ == "__main__":
    print("Starting test bot...")
    bot.run(token)