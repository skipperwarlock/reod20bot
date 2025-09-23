"""
Simple Discord bot that responds to the slash command /roll with a number between 1 and 20.

Usage:
  1) Install dependencies: pip install -r requirements.txt
  2) Set environment variable DISCORD_TOKEN to your bot token.
     - Windows PowerShell: $Env:DISCORD_TOKEN = "<your-token>"
  3) Run: python main.py

Notes:
  - This bot uses Slash Commands (Application Commands). After startup, it syncs the /roll command.
  - Message Content Intent is not required for slash commands.
  - Invite the bot with the applications.commands scope and permission to send messages.
"""
from __future__ import annotations
from dotenv import load_dotenv
import os
import random
import sys
import re

try:
    import discord  # discord.py
except Exception as e:
    print("discord.py is not installed. Install with: pip install -r requirements.txt", file=sys.stderr)
    raise

from discord import app_commands
load_dotenv()

# Role-based champion aggression maps (2 = least aggressive, 19 = most aggressive).
TOP_LANE_CHAMPIONS = {
    "Aatrox": 8, "Camille": 13, "Cho'Gath": 7, "Darius": 13, "Dr. Mundo": 4, "Fiora": 11, "Garen": 4, "Gnar": 16,
    "Illaoi": 7, "Irelia": 14, "Jax": 13, "Jayce": 4, "Kayle": 3, "Kennen": 17, "Kled": 20, "Malphite": 17, "Maokai": 9,
    "Mordekaiser": 8, "Nasus": 3, "Ornn": 14, "Poppy": 10, "Quinn": 3, "Renekton": 13, "Riven": 13, "Rumble": 8,
    "Sett": 14, "Shen": 17, "Singed": 8, "Sion": 9, "Tryndamere": 7, "Urgot": 8, "Volibear": 14, "Yorick": 8,
    "Teemo": 1, "Aurora": 2, "Vayne": 3, "Kalista": 4
}

SUPPORT_CHAMPIONS = {  # Typically supports in bot lane
    "Alistar": 15, "Bard": 11, "Blitzcrank": 14, "Braum": 10, "Janna": 3, "Karma": 3, "Leona": 17, "Lulu": 7, "Morgana": 13,
    "Nami": 12, "Nautilus": 16, "Pyke": 11, "Rakan": 17, "Rell": 18, "Renata Glasc": 10, "Sona": 8, "Soraka": 4,
    "Tahm Kench": 9, "Taric": 9, "Thresh": 16, "Yuumi": 2, "Zilean": 7, "Zyra": 9, "Milio": 5, "Malphite": 20, "Teemo": 1
}

JUNGLE_CHAMPIONS = {
    "Amumu": 17, "Bel'Veth": 5, "Briar": 19, "Diana": 16, "Ekko": 8, "Elise": 11, "Evelynn": 8, "Fiddlesticks": 17,
    "Gragas": 12, "Graves": 4, "Hecarim": 17, "Ivern": 2, "Jarvan IV": 16, "Jax": 13, "Karthus": 8, "Kayn": 14,
    "Kindred": 2, "Kha'Zix": 14, "Lee Sin": 17, "Lillia": 13, "Maokai": 9, "Master Yi": 5, "Nidalee": 5,
    "Nocturne": 16, "Nunu & Willump": 16, "Poppy": 10, "Rammus": 10, "Rek'Sai": 9, "Rengar": 11, "Sejuani": 16,
    "Shaco": 3, "Skarner": 16, "Talon": 11, "Trundle": 8, "Udyr": 6, "Vi": 16, "Viego": 9, "Warwick": 14,
    "Wukong": 15, "Xin Zhao": 9, "Zac": 17, "Teemo": 1, "Malphite": 20
}

ADC_CHAMPIONS = {
    "Aphelios": 8, "Ashe": 18, "Caitlyn": 3, "Draven": 14, "Ezreal": 2, "Jhin": 12, "Jinx": 20, "Kai'Sa": 14,
    "Kalista": 17, "Kog'Maw": 9, "Lucian": 14, "Miss Fortune": 8, "Nilah": 16, "Samira": 18, "Senna": 4,
    "Sivir": 3, "Tristana": 16, "Twitch": 16, "Varus": 16, "Vayne": 8, "Xayah": 8, "Zeri": 15, "Teemo": 1
}

MID_LANE_CHAMPIONS = {
    "Ahri": 12, "Akali": 17, "Anivia": 11, "Annie": 18, "Aurelion Sol": 11, "Azir": 17, "Cassiopeia": 14, "Corki": 2,
    "Diana": 16, "Ekko": 12, "Fizz": 17, "Galio": 14, "Irelia": 17, "Jayce": 4, "Kassadin": 12, "Katarina": 17,
    "LeBlanc": 8, "Lissandra": 14, "Lux": 6, "Malzahar": 14, "Neeko": 17, "Orianna": 14, "Qiyana": 18, "Ryze": 11,
    "Seraphine": 14, "Sylas": 16, "Syndra": 12, "Taliyah": 12, "Talon": 14, "Twisted Fate": 10, "Veigar": 11,
    "Vel'Koz": 4, "Viktor": 6, "Vladimir": 7, "Xerath": 3, "Yasuo": 17, "Yone": 17, "Zed": 18, "Ziggs": 4, "Zoe": 8,
    "Teemo": 1, "Malphite": 20
}


def _is_likely_discord_token(s: str) -> bool:
    pattern = r'^[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{5,}\.[A-Za-z0-9_\-]{10,}$'
    return re.match(pattern, s) is not None


def get_token() -> str:
    token = os.getenv("DISCORD_TOKEN", "").strip().strip('"').strip("'")

    # Some users mistakenly include the literal "Bot " prefix; discord.py expects just the raw token.
    if token.lower().startswith("bot "):
        token = token[4:].strip()

    if not token:
        print(
            "ERROR: DISCORD_TOKEN environment variable is not set.\n"
            "Set it and run again. Example (PowerShell):\n"
            "$Env:DISCORD_TOKEN = 'YOUR_TOKEN_HERE'",
            file=sys.stderr,
        )
        sys.exit(1)

    if not _is_likely_discord_token(token):
        print(
            "ERROR: The value in DISCORD_TOKEN doesn't look like a valid Discord bot token.\n"
            "- Paste the Bot Token from the Developer Portal (not the Client Secret).\n"
            "- Do not include quotes or a 'Bot ' prefix.\n"
            "- If you regenerated the token, update DISCORD_TOKEN and try again.",
            file=sys.stderr,
        )
        sys.exit(1)

    return token


intents = discord.Intents.default()
# Not required for slash commands, but harmless if left enabled
intents.message_content = False

client = discord.Client(intents=intents)

tree = app_commands.CommandTree(client)

# Mapping from champion display names to icon filenames for champions in champion_icons.
# We handle tricky cases where the filename differs from the display name.
_ICON_OVERRIDES = {
    "Bel'Veth": "Belveth.png",
    "Cho'Gath": "Chogath.png",
    "Dr. Mundo": "DrMundo.png",
    "Jarvan IV": "JarvanIV.png",
    "Kai'Sa": "Kaisa.png",
    "Kha'Zix": "Khazix.png",
    "Kog'Maw": "KogMaw.png",
    "LeBlanc": "Leblanc.png",
    "Lee Sin": "LeeSin.png",
    "Master Yi": "MasterYi.png",
    "Miss Fortune": "MissFortune.png",
    "Nunu & Willump": "Nunu.png",
    "Rek'Sai": "RekSai.png",
    "Renata Glasc": "Renata.png",
    "Tahm Kench": "TahmKench.png",
    "Twisted Fate": "TwistedFate.png",
    "Vel'Koz": "Velkoz.png",
    "Xin Zhao": "XinZhao.png",
    # Wukong is sometimes stored as MonkeyKing in assets
    "Wukong": "MonkeyKing.png",
    # Aurelion Sol stored without space
    "Aurelion Sol": "AurelionSol.png",
}

CHAMPION_ICONS_DIR = os.path.join(os.path.dirname(__file__), 'champion_icons')

def _default_icon_filename(name: str) -> str:
    # Remove non-letter characters and join parts to form PascalCase-like filename.
    parts = re.split(r"[^A-Za-z]+", name)
    joined = "".join(parts)
    return f"{joined}.png"


def get_icon_path_for_champion(name: str) -> str | None:
    """Return the full path to the icon for the given champion name, if it exists."""
    # First try overrides
    fname = _ICON_OVERRIDES.get(name)
    candidates = []
    if fname:
        candidates.append(fname)
    # Then try normalized filename
    candidates.append(_default_icon_filename(name))
    # Also try lowercase for the tail in some assets
    if not fname:
        # Try making internal capitalization looser for odd cases like Velkoz (already covered), Belveth etc.
        candidates.append(_default_icon_filename(name).replace("'", "").replace(" ", ""))
    # Ensure uniqueness
    seen = set()
    uniq_candidates = []
    for c in candidates:
        if c not in seen:
            uniq_candidates.append(c)
            seen.add(c)
    for filename in uniq_candidates:
        full = os.path.join(CHAMPION_ICONS_DIR, filename)
        if os.path.isfile(full):
            return full
    return None

@tree.command(name="roll", description="Roll a d20 and return champions matching the same aggression range.")
@app_commands.describe(role="Optional: pick a lane/role")
@app_commands.choices(role=[
    app_commands.Choice(name="jungle", value="jungle"),
    app_commands.Choice(name="adc", value="adc"),
    app_commands.Choice(name="support", value="support"),
    app_commands.Choice(name="top", value="top"),
    app_commands.Choice(name="mid", value="mid"),
])
async def roll(interaction: discord.Interaction, role: app_commands.Choice[str] | None = None):
    roll_value = random.randint(1, 20)

    # Determine the bucket for the rolled value and pick a thematic line
    if roll_value == 1:
        low, high = 1, 1
        labels = [
            "Chuck Norris rolled a 1 once. The dice apologized. You? You get benched...",
            "Worst roll I’ve ever seen. Total disaster. People are laughing, believe me.",
            "That’s not a roll, that’s a cry for help. What’re you even doing here?",
            "You know you deserve this...",
            "Natural one. Congratulations. You’ve managed to weaponize incompetence.",
            "Just dodge..."
        ]
    elif 2 <= roll_value <= 4:
        low, high = 2, 4
        labels = [
            "Be nowhere near the enemy this game...",
            "Get down! Stay out of sight till you can pump iron. — Arnold",
            "Your best move? Pretend you’re furniture. Nobody attacks a chair.",
            "Walk away from danger. Keep walking. In fact, don’t stop walking.",
            "The best fight is the one you don't take. — Bruce"
        ]
    elif 5 <= roll_value <= 9:
        low, high = 5, 9
        labels = [
            "You get some rope this game. Don't hang yourself with it..",
            "Light skirmishes only. If it bleeds, let your jungler kill it. — Arnold"
        ]
    elif 10 <= roll_value <= 14:
        low, high = 10, 14
        labels = [
            "Your team is relying on you to make plays this game. Don't let them down...",
        ]
    elif 15 <= roll_value <= 19:
        low, high = 15, 19
        labels = [
            "YOU ARE THE ENGAGE. BE THE ENGAGE.",
            "Get to the teamfight! You start it. Hasta la vista, backline. — Arnold",
            "Ring the bell. You lead the charge. — Stallone"
        ]
    else:  # roll_value == 20
        low, high = 20, 20
        labels = [
            "The team fights when you say they fight!"
        ]
    label = random.choice(labels)

    # Choose the relevant maps based on the role argument
    role_value = role.value if role is not None else None
    maps = []
    scope = "all roles"
    if role_value is None:
        maps = [TOP_LANE_CHAMPIONS, JUNGLE_CHAMPIONS, ADC_CHAMPIONS, MID_LANE_CHAMPIONS, SUPPORT_CHAMPIONS]
    else:
        scope = role_value
        if role_value == "top":
            maps = [TOP_LANE_CHAMPIONS]
        elif role_value == "jungle":
            maps = [JUNGLE_CHAMPIONS]
        elif role_value == "adc":
            maps = [ADC_CHAMPIONS]
        elif role_value == "mid":
            maps = [MID_LANE_CHAMPIONS]
        elif role_value == "support":
            maps = [SUPPORT_CHAMPIONS]
        else:
            maps = [TOP_LANE_CHAMPIONS, JUNGLE_CHAMPIONS, ADC_CHAMPIONS, MID_LANE_CHAMPIONS, SUPPORT_CHAMPIONS]
            scope = "all roles"

    # Gather all champions whose aggression score falls within the bucket
    names = set()
    for m in maps:
        for name, score in m.items():
            if low <= score <= high:
                names.add(name)

    names_list = sorted(names)
    if names_list:
        picked = random.choice(names_list)
        msg = f"Rolled {roll_value} — {scope} champion: {picked}\n{label}"
        # Try to attach the champion icon image if available
        icon_path = get_icon_path_for_champion(picked)
        if icon_path:
            await interaction.response.send_message(msg, file=discord.File(icon_path))
            return
    else:
        msg = f"Rolled {roll_value} — No champions found in {scope} for this range."

    await interaction.response.send_message(msg)


@client.event
async def on_ready():
    try:
        await tree.sync()
        print(f"Logged in as {client.user} (id={client.user.id}) | Slash commands synced")
    except Exception as e:
        print(f"Logged in as {client.user} (id={client.user.id})")
        print("WARNING: Failed to sync application commands:", e, file=sys.stderr)




if __name__ == "__main__":
    try:
        client.run(get_token())
    except discord.errors.LoginFailure:
        print(
            "Login failed: Discord rejected the token provided in DISCORD_TOKEN.\n"
            "- Verify you're using the current Bot Token from the Developer Portal.\n"
            "- Do not prefix it with 'Bot ' and remove any surrounding quotes.\n"
            "- If you regenerated the token, update the environment variable and rerun.",
            file=sys.stderr,
        )
        sys.exit(1)
