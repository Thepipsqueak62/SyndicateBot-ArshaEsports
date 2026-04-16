import os
from configparser import ConfigParser
from pathlib import Path

# Get the absolute path to config.ini based on THIS file's location
CURRENT_FILE = Path(__file__)  # shared_code/read_config.py
PROJECT_ROOT = CURRENT_FILE.parent.parent  # Go up to Syndicate_ArshaBot
CONFIG_PATH = PROJECT_ROOT / "config.ini"

config = ConfigParser()
config.read(CONFIG_PATH)

def get_guild_id():
    guild_id = config["BotSettings"]["Guild_Id"]
    return guild_id

def get_event_channel():
    return config["BotSettings"]["Event_Pings"]

def get_welcome_channel():
    return config["BotSettings"]["Welcome_Channel"]

def get_allow_ping_role():
    return config["BotSettings"]["Allow_Ping_Role"]