import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import View, Select, Button
from discord import ButtonStyle
from discord import Interaction, SelectOption
from datetime import datetime, timedelta, timezone
import aiohttp
import re
import difflib
from discord import TextChannel, Thread
from datetime import datetime, timezone

now = datetime.now(timezone.utc)
TMDB_API_KEY = "e36e2f2241622833afa86a4ece029828"
active_announcements = {}

def slugify(title: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')

# ✅ Autocomplete function (not a class!)

async def movie_autocomplete(interaction: Interaction, current: str):
    if not current:
        return []

    url = "https://api.themoviedb.org/3/search/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "query": current,
        "include_adult": "false"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                return []
            results = (await resp.json()).get("results", [])

    top_matches = results[:20]

    return [
        app_commands.Choice(
            name=f"{m['title']} ({m.get('release_date', '????')[:4]})",
            value=str(m["id"])
        )
        for m in top_matches
    ]


async def series_autocomplete(interaction: Interaction, current: str):
    if not current:
        return []

    url = "https://api.themoviedb.org/3/search/tv"
    params = {
        "api_key": TMDB_API_KEY,
        "query": current,
        "include_adult": "false"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                return []
            results = (await resp.json()).get("results", [])

    top_matches = results[:20]

    return [
        app_commands.Choice(
            name=f"{s['name']} ({s.get('first_air_date', '????')[:4]})",
            value=str(s["id"])
        )
        for s in top_matches
    ]


class TimezoneSelect(Select):
    def __init__(self, state):
        self.state = state
        selected_offset = state.get('selected_timezone')

        options = []
        for offset in range(-12, 13):  # UTC-12 to UTC+14
            label = f"UTC{offset:+d}"
            options.append(SelectOption(
                label=label,
                value=str(offset),
                default=False
            ))

        placeholder = f"UTC{selected_offset:+d}" if selected_offset is not None else "What's your timezone?"

        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options
        )


    async def callback(self, interaction: Interaction):
        if interaction.user != self.state['user']:
            await interaction.response.send_message("❌ You're not allowed to interact with this menu.", ephemeral=True)
            return

        self.state['selected_timezone'] = int(self.values[0])
        offset = self.state['selected_timezone']
        label = f"UTC{'+' if offset >= 0 else ''}{offset}"

        # Update only Date, Hour, and Minute selects with new timezone
# New improved version
        new_view = ScheduleMovieView.from_state(self.state)
        self.state['view'] = new_view
        await interaction.response.edit_message(view=new_view)



class DateSelect(Select):
    def __init__(self, state):
        self.state = state
        offset_hours = state.get('selected_timezone', 0)
        tz = timezone(timedelta(hours=offset_hours))
        today = datetime.now(tz).date()
        options = []

        for i in range(14):
            date = today + timedelta(days=i)
            label = date.strftime("%d %B")
            tags = []

            if i == 0:
                tags.append("Today")
            if i == 1:
                tags.append("Tomorrow")
                if date.weekday() == 0:
                    tags.append("Next Week")
            elif date.weekday() == 0:
                tags.append("Next Week")

            if tags:
                label += f" ({' - '.join(tags)})"

            options.append(SelectOption(label=label, value=date.isoformat()))

        super().__init__(placeholder="Select a date for the stream", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: Interaction):
        if interaction.user != self.state['user']:
            await interaction.response.send_message("❌ You're not allowed to interact with this menu.", ephemeral=True)
            return

        selected_date = datetime.fromisoformat(self.values[0]).date()
        self.state['selected_date'] = selected_date
        await interaction.response.defer(ephemeral=True)


class HourSelect(Select):
    def __init__(self, state):
        self.state = state
        options = []
        for hour in range(24):
            suffix = "AM" if hour < 12 else "PM"
            hour_12 = hour % 12 or 12
            label = f"{hour_12:02d}:   {suffix}"
            options.append(SelectOption(label=label, value=str(hour)))
        super().__init__(placeholder="Stream starts at (hour)", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: Interaction):
        if interaction.user != self.state['user']:
            await interaction.response.send_message("❌ You're not allowed to interact with this menu.", ephemeral=True)
            return
        self.state['selected_hour'] = int(self.values[0])
        await interaction.response.defer(ephemeral=True)

class MinuteSelect(Select):
    def __init__(self, state):
        self.state = state
        options = [SelectOption(label=f":{minute:02d}", value=str(minute)) for minute in range(0, 60, 15)]
        super().__init__(placeholder="(minute)", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: Interaction):
        if interaction.user != self.state['user']:
            await interaction.response.send_message("❌ You're not allowed to interact with this menu.", ephemeral=True)
            return
        self.state['selected_minute'] = int(self.values[0])
        await interaction.response.defer(ephemeral=True)
class ConfirmChoiceButton(Button):
    def __init__(self, label, style, callback_func):
        super().__init__(label=label, style=style)
        self.callback_func = callback_func

    async def callback(self, interaction):
        await self.callback_func(interaction)

class MovieConfirmView(View):
    def __init__(self, movie_name, tmdb_link, overview, poster_url, rating, backdrop_url, user):
        super().__init__(timeout=60)
        self.movie_name = movie_name
        self.tmdb_link = tmdb_link
        self.overview = overview
        self.poster_url = poster_url
        self.rating = rating
        self.backdrop_url = backdrop_url
        self.user = user

        self.add_item(ConfirmChoiceButton("Yes!", ButtonStyle.success, self.yes_callback))
        self.add_item(ConfirmChoiceButton("No!", ButtonStyle.danger, self.no_callback))




    async def yes_callback(self, interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ You're not allowed to confirm this movie.", ephemeral=True)
            return
        state = {
            'movie_name': self.movie_name,
            'user': self.user,
            'tmdb_link': self.tmdb_link,
            'overview': self.overview,
            'poster_url': self.poster_url,
            'rating': self.rating,
            'backdrop_url': self.backdrop_url
        }

        view = ScheduleMovieView(state)
        state['view'] = view  # ✅ assign *after* the view is created

        await interaction.response.edit_message(
            content=f"🗓️Great! Let's schedule your movie hosting!\n**Movie:** [{self.movie_name}]({self.tmdb_link})",
            view=view
            )

      


    async def no_callback(self, interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ You're not allowed to cancel this.", ephemeral=True)
            return

        await interaction.response.edit_message(content="❌ Movie scheduling cancelled.", view=None)

class ConfirmButton(Button):
    def __init__(self, state):
        self.state = state
        super().__init__(label="Confirm", style=discord.ButtonStyle.success)

    async def callback(self, interaction: Interaction):
        if interaction.user != self.state['user']:
            await interaction.response.send_message("❌ You're not allowed to confirm this selection.", ephemeral=True)
            return

        missing = []
        if 'selected_date' not in self.state:
            missing.append("date")
        if 'selected_hour' not in self.state:
            missing.append("hour")
        if 'selected_minute' not in self.state:
            missing.append("minute")

        if missing:
            await interaction.response.send_message(
                f"You need to select {', '.join(missing)} before confirming",
                ephemeral=True
            )
            return


        offset_hours = self.state.get('selected_timezone', 0)
        tz = timezone(timedelta(hours=offset_hours))

        movie_datetime = datetime.combine(
            self.state['selected_date'], datetime.min.time()
        ).replace(
            hour=self.state['selected_hour'],
            minute=self.state['selected_minute'],
            tzinfo=tz
        )


        self.disabled = True
        await interaction.response.edit_message(view=self.state['view'])

        if not interaction.guild:
            await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
            return

        role = next(
            (r for r in interaction.guild.roles if "movie" in r.name.lower() and "ticket" in r.name.lower()),
            None
        )

        if not role:
            await interaction.followup.send("⚠️ Could not find a role containing both `movie` and `ticket` in its name.", ephemeral=True)
            return

        role_ping = role.mention

        reschedule_message_id = self.state.get('reschedule_message_id')
        existing_interested_users = self.state.get('existing_interested_users', [])

        # If rescheduling, delete the old announcement and use its channel
        if reschedule_message_id:
            old_data = active_announcements.get(reschedule_message_id)
            if old_data:
                channel = bot.get_channel(old_data['channel_id'])
                if channel:
                    try:
                        old_msg = await channel.fetch_message(reschedule_message_id)
                        await old_msg.delete()
                    except Exception as e:
                        print(f"Error deleting old announcement during reschedule: {e}")
                active_announcements.pop(reschedule_message_id, None)
            else:
                channel = interaction.channel
        else:
            channel = interaction.channel

        if isinstance(channel, discord.TextChannel):
            embed = create_announcement_embed(
                host_name=self.state['user'].display_name,
                movie_name=self.state['movie_name'],
                movie_datetime=movie_datetime,
                tmdb_link=self.state.get("tmdb_link"),
                overview=self.state.get("overview"),
                poster_url=self.state.get("poster_url"),
                rating=self.state.get("rating"),
                backdrop_url=self.state.get("backdrop_url"),
                interested_users=existing_interested_users
            )

            message = await channel.send(
                embed=embed,
                content=role_ping,
                allowed_mentions=discord.AllowedMentions(roles=True)
            )

            if message:
                active_announcements[message.id] = {
                    'channel_id': channel.id,
                    'host_name': self.state['user'].display_name,
                    'host_id': self.state['user'].id,
                    'movie_name': self.state['movie_name'],
                    'movie_datetime': movie_datetime,
                    'tmdb_link': self.state.get("tmdb_link"),
                    'overview': self.state.get("overview"),
                    'poster_url': self.state.get("poster_url"),
                    'rating': self.state.get("rating"),
                    'backdrop_url': self.state.get("backdrop_url"),
                    'notified_10min': False,
                    'interested_users': list(existing_interested_users)
                }

                ticket_view = build_announcement_view(message.id, active_announcements[message.id])
                await message.edit(view=ticket_view)

class ScheduleMovieView(View):
    def __init__(self, state):
        super().__init__(timeout=None)
        self.state = state  # ✅ Use shared state
        self.confirm_button = ConfirmButton(state)
        self.add_item(TimezoneSelect(state))
        self.add_item(DateSelect(state))
        self.add_item(HourSelect(state))
        self.add_item(MinuteSelect(state))
        self.add_item(self.confirm_button)

    @classmethod
    def from_state(cls, state):
        return cls(state)


        # Preserve selections if already made
        if 'selected_date' in state:
            view.confirm_button.state['selected_date'] = state['selected_date']
        if 'selected_hour' in state:
            view.confirm_button.state['selected_hour'] = state['selected_hour']
        if 'selected_minute' in state:
            view.confirm_button.state['selected_minute'] = state['selected_minute']
        if 'selected_timezone' in state:
            view.confirm_button.state['selected_timezone'] = state['selected_timezone']

        return view



# The rest of the code remains unchanged...

class TakeTicketButton(Button):
    def __init__(self, message_id):
        super().__init__(label="🎫 Get a ticket!", style=discord.ButtonStyle.primary, custom_id=f"ticket_{message_id}")
        self.message_id = message_id

    async def callback(self, interaction: Interaction):
        user = interaction.user
        movie_data = active_announcements.get(self.message_id)

        if not movie_data:
            # Only keep this if you're worried about message deletion, otherwise skip it.
            await interaction.response.send_message("❌ Ticket no longer available. It may have expired or been deleted.", ephemeral=True)
            return

        # ✅ Already took ticket
        if user.id in movie_data['interested_users']:
            await interaction.response.send_message("🎟️ You have already received the ticket! Stay tuned!", ephemeral=True)
            return

        # ✅ First time taking ticket
        movie_data['interested_users'].append(user.id)
# ✅ Update the original message embed and view
        channel = bot.get_channel(movie_data['channel_id'])
        if channel:
            try:
                msg = None
                if isinstance(channel, (TextChannel, Thread)):
                    msg = await channel.fetch_message(self.message_id)

                updated_embed = create_announcement_embed(
                    host_name=movie_data['host_name'],
                    movie_name=movie_data['movie_name'],
                    movie_datetime=movie_data['movie_datetime'],
                    tmdb_link=movie_data.get("tmdb_link"),
                    overview=movie_data.get("overview"),
                    poster_url=movie_data.get("poster_url"),
                    rating=movie_data.get("rating"),
                    backdrop_url=movie_data.get("backdrop_url"),
                    interested_users=movie_data.get("interested_users", [])
                )

                view = build_announcement_view(self.message_id, movie_data)
                if msg:
                    await msg.edit(embed=updated_embed, view=view)
            except Exception as e:
                print(f"Error updating message after ticket taken: {e}")
        await interaction.response.send_message(
            f"✅ You have received the ticket for the movie **{movie_data['movie_name']}**! I will notify you 10 minutes before the movie starts!",
            ephemeral=True
        )


class RetrieveTicketButton(Button):
    def __init__(self, message_id):
        super().__init__(label="🎟️ Retrieve ticket", style=discord.ButtonStyle.secondary, custom_id=f"retrieve_{message_id}")
        self.message_id = message_id

    async def callback(self, interaction: Interaction):
        user = interaction.user
        movie_data = active_announcements.get(self.message_id)

        if not movie_data:
            await interaction.response.send_message("❌ This event no longer exists.", ephemeral=True)
            return

        if user.id == movie_data.get('host_id'):
            await interaction.response.send_message("❌ The host cannot retrieve a ticket.", ephemeral=True)
            return

        if user.id not in movie_data['interested_users']:
            await interaction.response.send_message("❌ You don't have a ticket for this event to retrieve.", ephemeral=True)
            return

        movie_data['interested_users'].remove(user.id)

        channel = bot.get_channel(movie_data['channel_id'])
        if channel:
            try:
                msg = await channel.fetch_message(self.message_id)
                updated_embed = create_announcement_embed(
                    host_name=movie_data['host_name'],
                    movie_name=movie_data['movie_name'],
                    movie_datetime=movie_data['movie_datetime'],
                    tmdb_link=movie_data.get("tmdb_link"),
                    overview=movie_data.get("overview"),
                    poster_url=movie_data.get("poster_url"),
                    rating=movie_data.get("rating"),
                    backdrop_url=movie_data.get("backdrop_url"),
                    interested_users=movie_data.get("interested_users", [])
                )
                view = build_announcement_view(self.message_id, movie_data)
                if msg:
                    await msg.edit(embed=updated_embed, view=view)
            except Exception as e:
                print(f"Error updating message after ticket retrieval: {e}")

        await interaction.response.send_message(
            f"✅ Your ticket for **{movie_data['movie_name']}** has been retrieved. You will no longer be notified.",
            ephemeral=True
        )


class ShowAttendeesButton(Button):
    def __init__(self, message_id):
        super().__init__(label="👥 Show Audiences", style=ButtonStyle.secondary)
        self.message_id = message_id

    async def callback(self, interaction: Interaction):
        movie_data = active_announcements.get(self.message_id)
        if not movie_data:
            await interaction.response.send_message("❌ Couldn't fetch audience list for this event.", ephemeral=True)
            return

        user_ids = movie_data.get("interested_users", [])
        if not user_ids:
            await interaction.response.send_message("🍿 No one has taken a ticket yet!", ephemeral=True)
            return

        mentions = [f"<@{uid}>" for uid in user_ids]

        movie_time_unix = int(movie_data['movie_datetime'].timestamp())
        time_display = f"<t:{movie_time_unix}:F> | <t:{movie_time_unix}:R>"

        await interaction.response.send_message(
            f"🍿 Audience list for **{movie_data['movie_name']}** on **{time_display}** ({len(user_ids)}/50 Seats taken):\n"
            + "\n".join(mentions),
            ephemeral=True
        )




class CancelButton(Button):
    def __init__(self, message_id):
        super().__init__(label="❌ Cancel", style=discord.ButtonStyle.danger, custom_id=f"cancel_{message_id}")
        self.message_id = message_id

    async def callback(self, interaction: Interaction):
        movie_data = active_announcements.get(self.message_id)
        if not movie_data:
            await interaction.response.send_message("❌ This event no longer exists.", ephemeral=True)
            return

        if interaction.user.id != movie_data.get('host_id'):
            await interaction.response.send_message("❌ Only the host can cancel this event.", ephemeral=True)
            return

        movie_name = movie_data['movie_name']
        channel = bot.get_channel(movie_data['channel_id'])

        await interaction.response.defer()

        if channel:
            try:
                msg = await channel.fetch_message(self.message_id)
                await msg.delete()
            except Exception as e:
                print(f"Error deleting announcement: {e}")

        active_announcements.pop(self.message_id, None)

        if channel:
            await channel.send(f"❌ **{movie_name}** has been canceled.")


class AdjustButton(Button):
    def __init__(self, message_id):
        super().__init__(label="🕐 Adjust Time", style=discord.ButtonStyle.secondary, custom_id=f"adjust_{message_id}")
        self.message_id = message_id

    async def callback(self, interaction: Interaction):
        movie_data = active_announcements.get(self.message_id)
        if not movie_data:
            await interaction.response.send_message("❌ This event no longer exists.", ephemeral=True)
            return

        if interaction.user.id != movie_data.get('host_id'):
            await interaction.response.send_message("❌ Only the host can adjust the time.", ephemeral=True)
            return

        state = {
            'movie_name': movie_data['movie_name'],
            'user': interaction.user,
            'tmdb_link': movie_data.get('tmdb_link'),
            'overview': movie_data.get('overview'),
            'poster_url': movie_data.get('poster_url'),
            'rating': movie_data.get('rating'),
            'backdrop_url': movie_data.get('backdrop_url'),
            'reschedule_message_id': self.message_id,
            'existing_interested_users': list(movie_data.get('interested_users', [])),
        }

        view = ScheduleMovieView(state)
        state['view'] = view

        await interaction.response.send_message(
            f"🕐 Pick a new time for **{movie_data['movie_name']}**:",
            view=view,
            ephemeral=True
        )


def build_announcement_view(message_id, movie_data):
    now_utc = datetime.now(timezone.utc)
    view = View(timeout=None)
    btn = TakeTicketButton(message_id)
    if (now_utc - movie_data['movie_datetime']).total_seconds() > 7200:
        btn.disabled = True
    view.add_item(btn)
    view.add_item(RetrieveTicketButton(message_id))
    view.add_item(ShowAttendeesButton(message_id))
    view.add_item(AdjustButton(message_id))
    view.add_item(CancelButton(message_id))
    return view


# 🔧 ONLY THIS FUNCTION WAS MODIFIED
def create_announcement_embed(host_name, movie_name, movie_datetime, tmdb_link=None, overview=None, poster_url=None, rating=None, backdrop_url=None, interested_users=None):



    unix_timestamp = int(movie_datetime.timestamp())
    full = f"<t:{unix_timestamp}:F>"
    relative = f"<t:{unix_timestamp}:R>"

    embed = discord.Embed(
        title="🎬 Movie Theater Announcement",
        color=discord.Color.red()
    )

    embed.add_field(name="Movie", value=f"[{movie_name}]({tmdb_link})", inline=False)

    if overview:
        embed.add_field(name="Description", value=overview, inline=False)

    if rating:
        embed.add_field(name="Rating", value=f"⭐ {rating:.1f}/10", inline=False)

    embed.add_field(name="Host", value=host_name, inline=False)
    embed.add_field(name="Time", value=f"{full} | {relative}", inline=False)

    if poster_url:
        embed.set_thumbnail(url=backdrop_url)  # poster on the right
    if backdrop_url:
        embed.set_image(url=poster_url)    # backdrop on the bottom


    seats_taken = len(interested_users) if interested_users else 0
    embed.add_field(name="🎟️ Seats Taken", value=f"{seats_taken}/50", inline=False)


    return embed



class MovieNightBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

    async def on_ready(self):
        print(f"Logged in as {self.user}")
        if not update_movie_announcements.is_running():
            update_movie_announcements.start()
        if not ping_health_check.is_running():
            ping_health_check.start()



bot = MovieNightBot()
@bot.tree.command(name="movie", description="Schedule a movie night")
@app_commands.describe(movie_id="Type to search for a movie")
@app_commands.autocomplete(movie_id=movie_autocomplete)
async def movie(interaction: Interaction, movie_id: str):
    movie_data = None

    if movie_id.isdigit():
        url = f"https://api.themoviedb.org/3/movie/{movie_id}"
        params = {"api_key": TMDB_API_KEY}
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params=params) as resp:
                text = await resp.text()
                print(f"[DEBUG] Requested URL: {resp.url}")
                print(f"[DEBUG] Status Code: {resp.status}")
                print(f"[DEBUG] Response Text: {text[:500]}")
                if resp.status == 200:
                    movie_data = await resp.json()
                    print("[DEBUG] Movie Data:", movie_data)
    else:
        search_url = "https://api.themoviedb.org/3/search/movie"
        params = {"api_key": TMDB_API_KEY, "query": movie_id, "include_adult": "false"}
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url, params=params) as resp:
                if resp.status == 200:
                    results = (await resp.json()).get("results", [])
                    if results:
                        movie_data = results[0]

    if not movie_data:
        await interaction.response.send_message("❌ Could not fetch movie info.", ephemeral=True)
        return

    title = movie_data.get("title", "Unknown Title")
    release_year = movie_data.get("release_date", "????")[:4]
    movie_id = movie_data.get("id")
    movie_name = f"{title} ({release_year})"
    slug = slugify(title)
    tmdb_link = f"https://www.themoviedb.org/movie/{movie_id}-{slug}"

    # 🔽 New Data from TMDB
    overview = movie_data.get("overview")
    poster_path = movie_data.get("poster_path")
    poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
    rating = movie_data.get("vote_average")

    backdrop_path = movie_data.get("backdrop_path")
    backdrop_url = f"https://image.tmdb.org/t/p/w1280{backdrop_path}" if backdrop_path else None

    await interaction.response.send_message(
        content=f"Are you looking for this movie?\n🎬 **Movie:** [{movie_name}]({tmdb_link})",
        view=MovieConfirmView(movie_name, tmdb_link, overview, poster_url, rating, backdrop_url, interaction.user),
        ephemeral=True
    )


@bot.tree.command(name="series", description="Schedule a series night")
@app_commands.describe(series_id="Type to search for a TV series / anime / OVA / ONA")
@app_commands.autocomplete(series_id=series_autocomplete)
async def series(interaction: Interaction, series_id: str):

    url = f"https://api.themoviedb.org/3/tv/{series_id}"
    params = {"api_key": TMDB_API_KEY}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                await interaction.response.send_message("❌ Could not fetch series info.", ephemeral=True)
                return
            data = await resp.json()

    title = data.get("name", "Unknown Title")
    year = data.get("first_air_date", "????")[:4]
    series_name = f"{title} ({year})"

    slug = slugify(title)
    tmdb_link = f"https://www.themoviedb.org/tv/{series_id}-{slug}"

    overview = data.get("overview")
    poster_path = data.get("poster_path")
    poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
    rating = data.get("vote_average")

    backdrop_path = data.get("backdrop_path")
    backdrop_url = f"https://image.tmdb.org/t/p/w1280{backdrop_path}" if backdrop_path else None

    await interaction.response.send_message(
        content=f"Is this the correct **series**?\n📺 **Series:** [{series_name}]({tmdb_link})",
        view=MovieConfirmView(series_name, tmdb_link, overview, poster_url, rating, backdrop_url, interaction.user),
        ephemeral=True
    )


# Keep the bot awake by pinging the health check endpoint
@tasks.loop(minutes=30)
async def ping_health_check():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    print("[HEALTH] Health check ping successful")
    except Exception as e:
        print(f"[HEALTH] Health check ping failed: {e}")


@tasks.loop(minutes=1)
async def update_movie_announcements():
    now = datetime.now(timezone.utc)
    expired = []

    for msg_id, data in list(active_announcements.items()):
        time_until = (data['movie_datetime'] - now).total_seconds()

        # Expire 2 hours after movie time
        if (now - data['movie_datetime']).total_seconds() > 7200:
            expired.append(msg_id)
            continue

        # 10-minute notification
        if 0 < time_until <= 600 and not data.get("notified_10min"):
            channel = bot.get_channel(data['channel_id'])
            if isinstance(channel, discord.TextChannel):
                mentions = [f"<@{uid}>" for uid in data.get("interested_users", [])]
                if mentions:
                    try:
                        await channel.send(
                            f"The movie *{data['movie_name']}* is going to starts soon in 10 minutes! Grab a snack and take a seat!🍿\n🎟️ {' '.join(mentions)}"
                        )
                        data['notified_10min'] = True
                    except Exception as e:
                        print(f"Failed to send 10-minute reminder: {e}")

        # Always update the embed and check if ticket button should be disabled
        channel = bot.get_channel(data['channel_id'])
        if isinstance(channel, discord.TextChannel):
            try:
                message = await channel.fetch_message(msg_id)
                new_embed = create_announcement_embed(
                    host_name=data['host_name'],
                    movie_name=data['movie_name'],
                    movie_datetime=data['movie_datetime'],
                    tmdb_link=data.get("tmdb_link"),
                    overview=data.get("overview"),
                    poster_url=data.get("poster_url"),
                    rating=data.get("rating"),
                    backdrop_url=data.get("backdrop_url"),
                    interested_users=data.get("interested_users", [])
                )


                ticket_view = build_announcement_view(msg_id, data)
                await message.edit(embed=new_embed, view=ticket_view)

            except (discord.NotFound, discord.Forbidden):
                expired.append(msg_id)
            except Exception as e:
                print(f"Error updating message {msg_id}: {e}")

    for msg_id in expired:
        active_announcements.pop(msg_id, None)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    print(f"Error: {error}")

def get_bot():
    return bot
