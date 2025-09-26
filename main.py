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
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

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
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'bot_data.db')

# Initialize database
def init_database():
    """Initialize the SQLite database for storing roll statistics."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Create rolls table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rolls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            roll_value INTEGER NOT NULL,
            role TEXT,
            champion TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def log_roll(user_id: int, username: str, roll_value: int, role: Optional[str], champion: Optional[str]):
    """Log a roll to the database."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO rolls (user_id, username, roll_value, role, champion)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, username, roll_value, role, champion))
    
    conn.commit()
    conn.close()

def get_user_stats(user_id: int) -> Dict[str, Any]:
    """Get roll statistics for a specific user."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Get total rolls
    cursor.execute('SELECT COUNT(*) FROM rolls WHERE user_id = ?', (user_id,))
    total_rolls = cursor.fetchone()[0]
    
    # Get natural 20s
    cursor.execute('SELECT COUNT(*) FROM rolls WHERE user_id = ? AND roll_value = 20', (user_id,))
    natural_20s = cursor.fetchone()[0]
    
    # Get natural 1s
    cursor.execute('SELECT COUNT(*) FROM rolls WHERE user_id = ? AND roll_value = 1', (user_id,))
    natural_1s = cursor.fetchone()[0]
    
    # Get recent rolls (last 10)
    cursor.execute('''
        SELECT roll_value, role, champion, timestamp 
        FROM rolls 
        WHERE user_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 10
    ''', (user_id,))
    recent_rolls = cursor.fetchall()
    
    conn.close()
    
    return {
        'total_rolls': total_rolls,
        'natural_20s': natural_20s,
        'natural_1s': natural_1s,
        'recent_rolls': recent_rolls
    }

def get_leaderboard_data(category: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get leaderboard data for a specific category."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    if category == "total_rolls":
        cursor.execute('''
            SELECT user_id, username, COUNT(*) as count
            FROM rolls 
            GROUP BY user_id, username 
            ORDER BY count DESC 
            LIMIT ?
        ''', (limit,))
    elif category == "natural_20s":
        cursor.execute('''
            SELECT user_id, username, COUNT(*) as count
            FROM rolls 
            WHERE roll_value = 20
            GROUP BY user_id, username 
            ORDER BY count DESC 
            LIMIT ?
        ''', (limit,))
    elif category == "natural_1s":
        cursor.execute('''
            SELECT user_id, username, COUNT(*) as count
            FROM rolls 
            WHERE roll_value = 1
            GROUP BY user_id, username 
            ORDER BY count DESC 
            LIMIT ?
        ''', (limit,))
    elif category == "luckiest":
        cursor.execute('''
            SELECT user_id, username, 
                   COUNT(CASE WHEN roll_value = 20 THEN 1 END) as nat_20s,
                   COUNT(*) as total_rolls,
                   ROUND(COUNT(CASE WHEN roll_value = 20 THEN 1 END) * 100.0 / COUNT(*), 2) as luck_percentage
            FROM rolls 
            GROUP BY user_id, username 
            HAVING total_rolls >= 5
            ORDER BY luck_percentage DESC, nat_20s DESC
            LIMIT ?
        ''', (limit,))
    elif category == "unluckiest":
        cursor.execute('''
            SELECT user_id, username, 
                   COUNT(CASE WHEN roll_value = 1 THEN 1 END) as nat_1s,
                   COUNT(*) as total_rolls,
                   ROUND(COUNT(CASE WHEN roll_value = 1 THEN 1 END) * 100.0 / COUNT(*), 2) as unluck_percentage
            FROM rolls 
            GROUP BY user_id, username 
            HAVING total_rolls >= 5
            ORDER BY unluck_percentage DESC, nat_1s DESC
            LIMIT ?
        ''', (limit,))
    elif category == "highest_avg":
        cursor.execute('''
            SELECT user_id, username, 
                   ROUND(AVG(roll_value), 2) as avg_roll,
                   COUNT(*) as total_rolls
            FROM rolls 
            GROUP BY user_id, username 
            HAVING total_rolls >= 5
            ORDER BY avg_roll DESC, total_rolls DESC
            LIMIT ?
        ''', (limit,))
    elif category == "most_active_today":
        cursor.execute('''
            SELECT user_id, username, COUNT(*) as count
            FROM rolls 
            WHERE DATE(timestamp) = DATE('now')
            GROUP BY user_id, username 
            ORDER BY count DESC 
            LIMIT ?
        ''', (limit,))
    elif category == "most_active_week":
        cursor.execute('''
            SELECT user_id, username, COUNT(*) as count
            FROM rolls 
            WHERE timestamp >= datetime('now', '-7 days')
            GROUP BY user_id, username 
            ORDER BY count DESC 
            LIMIT ?
        ''', (limit,))
    else:
        conn.close()
        return []
    
    results = cursor.fetchall()
    conn.close()
    
    # Convert to list of dictionaries
    leaderboard = []
    for i, (user_id, username, *data) in enumerate(results, 1):
        entry = {
            'rank': i,
            'user_id': user_id,
            'username': username,
            'data': data
        }
        leaderboard.append(entry)
    
    return leaderboard

def get_user_rank(user_id: int, category: str) -> Optional[Dict[str, Any]]:
    """Get a user's rank in a specific category."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    if category == "total_rolls":
        cursor.execute('''
            SELECT COUNT(*) + 1 as rank
            FROM (
                SELECT user_id, COUNT(*) as count
                FROM rolls 
                GROUP BY user_id
                HAVING count > (
                    SELECT COUNT(*) 
                    FROM rolls 
                    WHERE user_id = ?
                )
            )
        ''', (user_id,))
    elif category == "natural_20s":
        cursor.execute('''
            SELECT COUNT(*) + 1 as rank
            FROM (
                SELECT user_id, COUNT(*) as count
                FROM rolls 
                WHERE roll_value = 20
                GROUP BY user_id
                HAVING count > (
                    SELECT COUNT(*) 
                    FROM rolls 
                    WHERE user_id = ? AND roll_value = 20
                )
            )
        ''', (user_id,))
    elif category == "luckiest":
        cursor.execute('''
            SELECT COUNT(*) + 1 as rank
            FROM (
                SELECT user_id, 
                       ROUND(COUNT(CASE WHEN roll_value = 20 THEN 1 END) * 100.0 / COUNT(*), 2) as luck_percentage
                FROM rolls 
                GROUP BY user_id
                HAVING COUNT(*) >= 5 AND luck_percentage > (
                    SELECT ROUND(COUNT(CASE WHEN roll_value = 20 THEN 1 END) * 100.0 / COUNT(*), 2)
                    FROM rolls 
                    WHERE user_id = ?
                )
            )
        ''', (user_id,))
    else:
        conn.close()
        return None
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {'rank': result[0]}
    return None

def get_champion_info(champion_name: str) -> Optional[Dict[str, Any]]:
    """Get comprehensive information about a champion."""
    # Search for champion in all role dictionaries
    all_champions = {}
    all_champions.update(TOP_LANE_CHAMPIONS)
    all_champions.update(JUNGLE_CHAMPIONS)
    all_champions.update(ADC_CHAMPIONS)
    all_champions.update(MID_LANE_CHAMPIONS)
    all_champions.update(SUPPORT_CHAMPIONS)
    
    # Find champion (case-insensitive)
    champion_key = None
    for key in all_champions.keys():
        if key.lower() == champion_name.lower():
            champion_key = key
            break
    
    if not champion_key:
        return None
    
    aggression = all_champions[champion_key]
    
    # Determine roles
    roles = []
    if champion_key in TOP_LANE_CHAMPIONS:
        roles.append("Top")
    if champion_key in JUNGLE_CHAMPIONS:
        roles.append("Jungle")
    if champion_key in ADC_CHAMPIONS:
        roles.append("ADC")
    if champion_key in MID_LANE_CHAMPIONS:
        roles.append("Mid")
    if champion_key in SUPPORT_CHAMPIONS:
        roles.append("Support")
    
    # Determine aggression level description
    if aggression == 1:
        aggression_desc = "Ultra Passive"
    elif 2 <= aggression <= 4:
        aggression_desc = "Very Passive"
    elif 5 <= aggression <= 9:
        aggression_desc = "Moderate"
    elif 10 <= aggression <= 14:
        aggression_desc = "Aggressive"
    elif 15 <= aggression <= 19:
        aggression_desc = "Very Aggressive"
    else:  # aggression == 20
        aggression_desc = "Ultra Aggressive"
    
    return {
        'name': champion_key,
        'aggression': aggression,
        'aggression_desc': aggression_desc,
        'roles': roles,
        'icon_path': get_icon_path_for_champion(champion_key)
    }

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
        
        # Log the roll to database
        log_roll(
            user_id=interaction.user.id,
            username=interaction.user.display_name,
            roll_value=roll_value,
            role=role_value,
            champion=picked
        )
        
        # Determine embed color based on roll value
        if roll_value == 20:
            color = 0x00ff00  # Green for natural 20
        elif roll_value == 1:
            color = 0xff0000  # Red for natural 1
        elif roll_value >= 15:
            color = 0xff8c00  # Orange for high rolls
        elif roll_value <= 5:
            color = 0x87ceeb  # Light blue for low rolls
        else:
            color = 0x7289da  # Discord blue for average rolls
        
        # Create embed
        embed = discord.Embed(
            title=f"🎲 Rolled {roll_value}!",
            description=f"**{scope.title()} Champion:** {picked}",
            color=color
        )
        
        # Add roll value with visual representation
        roll_bar = "█" * (roll_value // 2) + "░" * (10 - roll_value // 2)
        embed.add_field(
            name="🎯 Roll Result",
            value=f"**{roll_value}/20**\n`{roll_bar}`",
            inline=True
        )
        
        # Add role information if specified
        if role_value:
            role_emojis = {
                "top": "🔝",
                "jungle": "🌲",
                "mid": "⚡",
                "adc": "🏹",
                "support": "🛡️"
            }
            role_emoji = role_emojis.get(role_value, "⚔️")
            embed.add_field(
                name="🎭 Role",
                value=f"{role_emoji} **{role_value.title()}**",
                inline=True
            )
        
        # Add aggression level info
        champion_info = get_champion_info(picked)
        if champion_info:
            aggression = champion_info['aggression']
            aggression_percentage = (aggression / 20) * 100
            
            # Add aggression emoji
            if aggression == 1:
                aggression_emoji = "🛡️"
            elif 2 <= aggression <= 4:
                aggression_emoji = "🌱"
            elif 5 <= aggression <= 9:
                aggression_emoji = "⚖️"
            elif 10 <= aggression <= 14:
                aggression_emoji = "⚔️"
            elif 15 <= aggression <= 19:
                aggression_emoji = "🔥"
            else:  # aggression == 20
                aggression_emoji = "💥"
            
            embed.add_field(
                name=f"{aggression_emoji} Aggression",
                value=f"**{aggression}/20** ({aggression_percentage:.0f}%)",
                inline=True
            )
        
        # Add the thematic label
        embed.add_field(
            name="💬 Message",
            value=f"*{label}*",
            inline=False
        )
        
        # Add footer with user info
        embed.set_footer(text=f"Rolled by {interaction.user.display_name}")
        
        # Try to attach the champion icon image if available
        icon_path = get_icon_path_for_champion(picked)
        if icon_path:
            embed.set_thumbnail(url="attachment://champion.png")
            await interaction.response.send_message(embed=embed, file=discord.File(icon_path, filename="champion.png"))
            return
        else:
            await interaction.response.send_message(embed=embed)
            return
    else:
        # Log the roll even if no champion found
        log_roll(
            user_id=interaction.user.id,
            username=interaction.user.display_name,
            roll_value=roll_value,
            role=role_value,
            champion=None
        )
        
        # Create embed for no champion found
        embed = discord.Embed(
            title=f"🎲 Rolled {roll_value}!",
            description=f"No champions found in **{scope}** for this range.",
            color=0x808080  # Gray for no results
        )
        
        embed.add_field(
            name="🎯 Roll Result",
            value=f"**{roll_value}/20**",
            inline=True
        )
        
        if role_value:
            role_emojis = {
                "top": "🔝",
                "jungle": "🌲",
                "mid": "⚡",
                "adc": "🏹",
                "support": "🛡️"
            }
            role_emoji = role_emojis.get(role_value, "⚔️")
            embed.add_field(
                name="🎭 Role",
                value=f"{role_emoji} **{role_value.title()}**",
                inline=True
            )
        
        embed.add_field(
            name="💬 Message",
            value=f"*{label}*",
            inline=False
        )
        
        embed.set_footer(text=f"Rolled by {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed)


@tree.command(name="stats", description="Show your roll statistics including total rolls, natural 20s, natural 1s, and recent rolls.")
async def stats(interaction: discord.Interaction):
    """Show user's roll statistics."""
    stats_data = get_user_stats(interaction.user.id)
    
    if stats_data['total_rolls'] == 0:
        embed = discord.Embed(
            title="🎲 No Rolls Yet!",
            description="You haven't rolled any dice yet! Use `/roll` to get started.",
            color=0x7289da
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)
        return
    
    # Calculate percentages
    nat_20_percent = (stats_data['natural_20s'] / stats_data['total_rolls']) * 100 if stats_data['total_rolls'] > 0 else 0
    nat_1_percent = (stats_data['natural_1s'] / stats_data['total_rolls']) * 100 if stats_data['total_rolls'] > 0 else 0
    
    # Determine embed color based on luck
    if nat_20_percent > 10:  # Very lucky
        color = 0x00ff00  # Green
    elif nat_20_percent > 5:  # Lucky
        color = 0xffff00  # Yellow
    elif nat_1_percent > 15:  # Unlucky
        color = 0xff0000  # Red
    else:  # Average
        color = 0x7289da  # Discord blue
    
    # Create embed
    embed = discord.Embed(
        title=f"🎲 Roll Statistics",
        description=f"**{interaction.user.display_name}**'s dice rolling performance",
        color=color,
        timestamp=datetime.now()
    )
    
    # Set user avatar as thumbnail
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    
    # Add statistics fields
    embed.add_field(
        name="📊 Overall Stats",
        value=f"**Total Rolls:** {stats_data['total_rolls']}\n"
              f"**Natural 20s:** {stats_data['natural_20s']} ({nat_20_percent:.1f}%)\n"
              f"**Natural 1s:** {stats_data['natural_1s']} ({nat_1_percent:.1f}%)",
        inline=True
    )
    
    # Calculate additional stats
    avg_roll = sum(roll[0] for roll in stats_data['recent_rolls']) / len(stats_data['recent_rolls']) if stats_data['recent_rolls'] else 0
    high_rolls = sum(1 for roll in stats_data['recent_rolls'] if roll[0] >= 15)
    low_rolls = sum(1 for roll in stats_data['recent_rolls'] if roll[0] <= 5)
    
    embed.add_field(
        name="🎯 Recent Performance",
        value=f"**Average Roll:** {avg_roll:.1f}\n"
              f"**High Rolls (15+):** {high_rolls}\n"
              f"**Low Rolls (≤5):** {low_rolls}",
        inline=True
    )
    
    # Add recent rolls as a field
    if stats_data['recent_rolls']:
        recent_text = ""
        for i, roll in enumerate(stats_data['recent_rolls'][:5], 1):
            roll_value, role, champion, timestamp = roll
            role_str = f" ({role})" if role else ""
            champion_str = f" → {champion}" if champion else ""
            
            # Add emoji based on roll value
            if roll_value == 20:
                emoji = "🎉"
            elif roll_value == 1:
                emoji = "💀"
            elif roll_value >= 15:
                emoji = "🔥"
            elif roll_value <= 5:
                emoji = "😞"
            else:
                emoji = "🎲"
            
            recent_text += f"{emoji} **{roll_value}**{role_str}{champion_str}\n"
        
        embed.add_field(
            name="📜 Recent Rolls",
            value=recent_text,
            inline=False
        )
    
    # Add footer with fun fact
    if nat_20_percent > 10:
        footer_text = "🎊 You're incredibly lucky!"
    elif nat_20_percent > 5:
        footer_text = "🍀 Lady luck is on your side!"
    elif nat_1_percent > 15:
        footer_text = "😅 Maybe try a different dice?"
    else:
        footer_text = "🎲 Keep rolling!"
    
    embed.set_footer(text=footer_text)
    
    await interaction.response.send_message(embed=embed)


@tree.command(name="leaderboard", description="View leaderboards for various roll statistics.")
@app_commands.describe(
    category="Choose which leaderboard to view",
    limit="Number of entries to show (1-25, default: 10)"
)
@app_commands.choices(category=[
    app_commands.Choice(name="🏆 Total Rolls", value="total_rolls"),
    app_commands.Choice(name="🎉 Natural 20s", value="natural_20s"),
    app_commands.Choice(name="💀 Natural 1s", value="natural_1s"),
    app_commands.Choice(name="🍀 Luckiest", value="luckiest"),
    app_commands.Choice(name="😅 Unluckiest", value="unluckiest"),
    app_commands.Choice(name="📊 Highest Average", value="highest_avg"),
    app_commands.Choice(name="📅 Most Active Today", value="most_active_today"),
    app_commands.Choice(name="📆 Most Active This Week", value="most_active_week"),
])
async def leaderboard(interaction: discord.Interaction, category: app_commands.Choice[str], limit: int = 10):
    """Show leaderboard for various statistics."""
    # Validate limit
    if limit < 1 or limit > 25:
        embed = discord.Embed(
            title="❌ Invalid Limit",
            description="Limit must be between 1 and 25.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed)
        return
    
    # Get leaderboard data
    leaderboard_data = get_leaderboard_data(category.value, limit)
    
    if not leaderboard_data:
        embed = discord.Embed(
            title="📊 Leaderboard",
            description=f"No data available for **{category.name}** yet.\n\nStart rolling to see leaderboards!",
            color=0x808080
        )
        await interaction.response.send_message(embed=embed)
        return
    
    # Determine embed color based on category
    color_map = {
        "total_rolls": 0x7289da,      # Discord blue
        "natural_20s": 0x00ff00,       # Green
        "natural_1s": 0xff0000,        # Red
        "luckiest": 0xffd700,          # Gold
        "unluckiest": 0x808080,        # Gray
        "highest_avg": 0x9932cc,       # Purple
        "most_active_today": 0xff8c00, # Orange
        "most_active_week": 0x00bfff   # Deep sky blue
    }
    color = color_map.get(category.value, 0x7289da)
    
    # Create embed
    embed = discord.Embed(
        title=f"🏆 {category.name} Leaderboard",
        description=f"Top {len(leaderboard_data)} players",
        color=color,
        timestamp=datetime.now()
    )
    
    # Build leaderboard text
    leaderboard_text = ""
    for entry in leaderboard_data:
        rank = entry['rank']
        username = entry['username']
        data = entry['data']
        
        # Add rank emoji
        if rank == 1:
            rank_emoji = "🥇"
        elif rank == 2:
            rank_emoji = "🥈"
        elif rank == 3:
            rank_emoji = "🥉"
        else:
            rank_emoji = f"**{rank}.**"
        
        # Format data based on category
        if category.value == "total_rolls":
            value_text = f"{data[0]} rolls"
        elif category.value == "natural_20s":
            value_text = f"{data[0]} natural 20s"
        elif category.value == "natural_1s":
            value_text = f"{data[0]} natural 1s"
        elif category.value == "luckiest":
            nat_20s, total_rolls, luck_percentage = data
            value_text = f"{luck_percentage}% ({nat_20s}/{total_rolls})"
        elif category.value == "unluckiest":
            nat_1s, total_rolls, unluck_percentage = data
            value_text = f"{unluck_percentage}% ({nat_1s}/{total_rolls})"
        elif category.value == "highest_avg":
            avg_roll, total_rolls = data
            value_text = f"{avg_roll} avg ({total_rolls} rolls)"
        elif category.value in ["most_active_today", "most_active_week"]:
            value_text = f"{data[0]} rolls"
        else:
            value_text = str(data[0])
        
        leaderboard_text += f"{rank_emoji} **{username}** - {value_text}\n"
    
    embed.add_field(
        name="📊 Rankings",
        value=leaderboard_text,
        inline=False
    )
    
    # Add user's rank if they have data
    user_rank = get_user_rank(interaction.user.id, category.value)
    if user_rank:
        embed.add_field(
            name="🎯 Your Rank",
            value=f"You are ranked **#{user_rank['rank']}** in this category!",
            inline=False
        )
    
    # Add footer with helpful info
    footer_text = ""
    if category.value == "luckiest":
        footer_text = "🍀 Based on natural 20 percentage (minimum 5 rolls)"
    elif category.value == "unluckiest":
        footer_text = "😅 Based on natural 1 percentage (minimum 5 rolls)"
    elif category.value == "highest_avg":
        footer_text = "📊 Based on average roll value (minimum 5 rolls)"
    elif category.value == "most_active_today":
        footer_text = "📅 Rolls made today"
    elif category.value == "most_active_week":
        footer_text = "📆 Rolls made in the last 7 days"
    else:
        footer_text = "🎲 Keep rolling to climb the leaderboard!"
    
    embed.set_footer(text=footer_text)
    
    await interaction.response.send_message(embed=embed)


@tree.command(name="lb", description="Quick access to leaderboards (alias for /leaderboard).")
@app_commands.describe(
    category="Choose which leaderboard to view",
    limit="Number of entries to show (1-25, default: 10)"
)
@app_commands.choices(category=[
    app_commands.Choice(name="🏆 Total Rolls", value="total_rolls"),
    app_commands.Choice(name="🎉 Natural 20s", value="natural_20s"),
    app_commands.Choice(name="💀 Natural 1s", value="natural_1s"),
    app_commands.Choice(name="🍀 Luckiest", value="luckiest"),
    app_commands.Choice(name="😅 Unluckiest", value="unluckiest"),
    app_commands.Choice(name="📊 Highest Average", value="highest_avg"),
    app_commands.Choice(name="📅 Most Active Today", value="most_active_today"),
    app_commands.Choice(name="📆 Most Active This Week", value="most_active_week"),
])
async def lb(interaction: discord.Interaction, category: app_commands.Choice[str], limit: int = 10):
    """Quick access to leaderboards."""
    # Reuse the leaderboard logic
    await leaderboard.callback(interaction, category, limit)


@tree.command(name="champion", description="Get detailed information about a specific champion.")
@app_commands.describe(champion_name="The name of the champion to look up")
async def champion(interaction: discord.Interaction, champion_name: str):
    """Show detailed information about a champion."""
    champion_info = get_champion_info(champion_name)
    
    if not champion_info:
        # Try to find similar champion names
        all_champions = set()
        all_champions.update(TOP_LANE_CHAMPIONS.keys())
        all_champions.update(JUNGLE_CHAMPIONS.keys())
        all_champions.update(ADC_CHAMPIONS.keys())
        all_champions.update(MID_LANE_CHAMPIONS.keys())
        all_champions.update(SUPPORT_CHAMPIONS.keys())
        
        # Find champions with similar names
        similar = []
        champion_lower = champion_name.lower()
        for champ in all_champions:
            if champion_lower in champ.lower() or champ.lower() in champion_lower:
                similar.append(champ)
        
        embed = discord.Embed(
            title="❌ Champion Not Found",
            description=f"Champion '{champion_name}' not found.",
            color=0xff0000
        )
        
        if similar:
            similar_str = ", ".join(sorted(similar)[:5])  # Show up to 5 similar names
            embed.add_field(
                name="💡 Did you mean:",
                value=similar_str,
                inline=False
            )
        else:
            embed.add_field(
                name="💡 Tip:",
                value="Use `/roll` to see available champions.",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
        return
    
    # Determine embed color based on aggression level
    aggression = champion_info['aggression']
    if aggression == 1:
        color = 0x808080  # Gray - passive
    elif 2 <= aggression <= 4:
        color = 0x87ceeb  # Light blue - very passive
    elif 5 <= aggression <= 9:
        color = 0xffff00  # Yellow - moderate
    elif 10 <= aggression <= 14:
        color = 0xff8c00  # Orange - aggressive
    elif 15 <= aggression <= 19:
        color = 0xff4500  # Red-orange - very aggressive
    else:  # aggression == 20
        color = 0xff0000  # Red - ultra aggressive
    
    # Create embed with enhanced title and description
    embed = discord.Embed(
        title=f"⚔️ {champion_info['name']}",
        description=f"*{champion_info['aggression_desc']}*",
        color=color
    )
    
    # Add aggression level with enhanced visual bar and percentage
    aggression_percentage = (aggression / 20) * 100
    aggression_bar = "█" * (aggression // 2) + "░" * (10 - aggression // 2)
    
    # Add aggression emoji based on level
    if aggression == 1:
        aggression_emoji = "🛡️"
    elif 2 <= aggression <= 4:
        aggression_emoji = "🌱"
    elif 5 <= aggression <= 9:
        aggression_emoji = "⚖️"
    elif 10 <= aggression <= 14:
        aggression_emoji = "⚔️"
    elif 15 <= aggression <= 19:
        aggression_emoji = "🔥"
    else:  # aggression == 20
        aggression_emoji = "💥"
    
    embed.add_field(
        name=f"{aggression_emoji} Aggression Level",
        value=f"**{aggression}/20** ({aggression_percentage:.0f}%)\n`{aggression_bar}`",
        inline=True
    )
    
    # Add roles with enhanced emojis and formatting
    role_emojis = {
        "Top": "🔝",
        "Jungle": "🌲", 
        "Mid": "⚡",
        "ADC": "🏹",
        "Support": "🛡️"
    }
    
    # Create role badges
    role_badges = []
    for role in champion_info['roles']:
        emoji = role_emojis.get(role, '⚔️')
        role_badges.append(f"{emoji} **{role}**")
    
    embed.add_field(
        name="🎭 Primary Roles",
        value="\n".join(role_badges),
        inline=True
    )
    
    # Add champion tier/rarity based on aggression
    if aggression >= 18:
        tier = "🏆 **Legendary**"
        tier_desc = "Extremely rare and powerful"
    elif aggression >= 15:
        tier = "💎 **Epic**"
        tier_desc = "High-tier champion"
    elif aggression >= 10:
        tier = "⭐ **Rare**"
        tier_desc = "Above average champion"
    elif aggression >= 5:
        tier = "🔸 **Common**"
        tier_desc = "Standard champion"
    else:
        tier = "🔹 **Basic**"
        tier_desc = "Entry-level champion"
    
    embed.add_field(
        name="🏅 Champion Tier",
        value=f"{tier}\n*{tier_desc}*",
        inline=True
    )
    
    # Add detailed playstyle description with enhanced formatting
    playstyle_desc = ""
    if aggression == 1:
        playstyle_desc = (
            "🛡️ **Ultra Passive Playstyle**\n"
            "• Avoid all fights and skirmishes\n"
            "• Focus on farming and scaling\n"
            "• Play defensively at all times\n"
            "• Perfect for patient players"
        )
    elif 2 <= aggression <= 4:
        playstyle_desc = (
            "🌱 **Very Passive Playstyle**\n"
            "• Farm safely and avoid unnecessary fights\n"
            "• Only engage when you have clear advantages\n"
            "• Focus on late-game scaling\n"
            "• Great for defensive players"
        )
    elif 5 <= aggression <= 9:
        playstyle_desc = (
            "⚖️ **Balanced Playstyle**\n"
            "• Participate in light skirmishes\n"
            "• Look for safe opportunities\n"
            "• Adapt to game state\n"
            "• Versatile for all players"
        )
    elif 10 <= aggression <= 14:
        playstyle_desc = (
            "⚔️ **Aggressive Playstyle**\n"
            "• Look for opportunities to make plays\n"
            "• Control the pace of the game\n"
            "• Take calculated risks\n"
            "• Perfect for proactive players"
        )
    elif 15 <= aggression <= 19:
        playstyle_desc = (
            "🔥 **Very Aggressive Playstyle**\n"
            "• Be the primary engage for teamfights\n"
            "• Dictate when fights happen\n"
            "• Create pressure and opportunities\n"
            "• Ideal for aggressive players"
        )
    else:  # aggression == 20
        playstyle_desc = (
            "💥 **Ultra Aggressive Playstyle**\n"
            "• Dictate when fights happen\n"
            "• Control the entire game flow\n"
            "• Maximum pressure and aggression\n"
            "• For fearless players only!"
        )
    
    embed.add_field(
        name="📋 Playstyle Guide",
        value=playstyle_desc,
        inline=False
    )
    
    # Add matchup information
    matchup_info = ""
    if aggression >= 15:
        matchup_info = "🔥 **Counters:** Passive champions\n🛡️ **Weak to:** Disengage champions"
    elif aggression <= 5:
        matchup_info = "🛡️ **Counters:** Aggressive champions\n⚔️ **Weak to:** Early game champions"
    else:
        matchup_info = "⚖️ **Counters:** Extreme playstyles\n🎯 **Weak to:** Specialized champions"
    
    embed.add_field(
        name="⚔️ Matchup Info",
        value=matchup_info,
        inline=True
    )
    
    # Add recommended game phase
    if aggression >= 15:
        phase_info = "🌅 **Early Game**\n• Strong laning phase\n• Look for early kills\n• Control objectives"
    elif aggression <= 5:
        phase_info = "🌙 **Late Game**\n• Focus on farming\n• Scale into late game\n• Teamfight oriented"
    else:
        phase_info = "🌞 **Mid Game**\n• Balanced approach\n• Adapt to game state\n• Flexible timing"
    
    embed.add_field(
        name="⏰ Best Phase",
        value=phase_info,
        inline=True
    )
    
    # Add footer with enhanced message and champion count
    total_champions = len(set().union(TOP_LANE_CHAMPIONS.keys(), JUNGLE_CHAMPIONS.keys(), 
                                     ADC_CHAMPIONS.keys(), MID_LANE_CHAMPIONS.keys(), 
                                     SUPPORT_CHAMPIONS.keys()))
    
    if aggression >= 15:
        footer_text = f"🔥 Perfect for aggressive players! • {total_champions} champions available"
    elif aggression <= 5:
        footer_text = f"🛡️ Great for defensive players! • {total_champions} champions available"
    else:
        footer_text = f"⚖️ Balanced for all playstyles! • {total_champions} champions available"
    
    embed.set_footer(text=footer_text)
    
    # Try to attach the champion icon image if available
    if champion_info['icon_path']:
        embed.set_thumbnail(url="attachment://champion.png")
        await interaction.response.send_message(embed=embed, file=discord.File(champion_info['icon_path'], filename="champion.png"))
    else:
        await interaction.response.send_message(embed=embed)


@client.event
async def on_ready():
    try:
        # Initialize database
        init_database()
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
