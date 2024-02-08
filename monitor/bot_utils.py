import logging
import os
import configparser
from functools import wraps
from typing import Callable


CONFIG_FILE_NAME = "config"
SCRIPT_PATH = os.path.realpath(os.path.dirname(__file__))
DATA_PATH = os.path.realpath(os.path.join(SCRIPT_PATH, "../bot_config"))
QUERY_PATTERN_REFRESH = "c_re"
QUERY_PATTERN_TOGGLE_REFRESH = "c_toggle_re"
QUERY_PATTERN_CONFIRM_REBOOT = "c_call_reboot"
SOURCE_WEB_LINK = "https://github.com/Helther/server-mon-bot.git"
REBOOT_CMD_DELAY_DEFAULT = 1
REFRESH_RATE_DEFAULT = 5


# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("Monitor Bot")
logger.setLevel(logging.DEBUG)


class Config(object):
    def __init__(self) -> None:
        self.token = ""
        self.user_id_set: set = set()
        self.reboot_time_minutes = 0
        self.update_period_seconds = 0

    def is_user_specified(self) -> bool:
        return len(self.user_id_set) != 0

    def load_config(self, filepath: str) -> None:
        config = configparser.ConfigParser()
        with open(filepath, 'r') as config_file:
            config.read_file(config_file)
            config_section_name = "Main"
            self.token = config[config_section_name]["TOKEN"]  # if config invalid then terminate
            user_id_str = config[config_section_name].get("USER_ID", None)
            if user_id_str:
                user_id_str = user_id_str.replace(" ", "")
                user_ids = user_id_str.split(",")
                for id in user_ids:
                    self.user_id_set.add(int(id)) 

            self.reboot_time_minutes = config[config_section_name].get("REBOOT_CMD_DELAY", REBOOT_CMD_DELAY_DEFAULT)
            if self.reboot_time_minutes <= 0:
                self.reboot_time_minutes = REBOOT_CMD_DELAY_DEFAULT
            self.update_period_seconds = config[config_section_name].get("REFRESH_RATE", REFRESH_RATE_DEFAULT)
            if self.update_period_seconds <= 0:
                self.update_period_seconds = REFRESH_RATE_DEFAULT

config = Config()


def log_cmd(user, name: str) -> None:
    logger.info(f"user: {user.full_name} with id: {user.id} called: {name}")


def user_restricted(func: Callable):
    """Restrict usage of func to allowed users only and replies if necessary"""
    @wraps(func)
    async def inner(update, *args, **kwargs):
        user = update.effective_user
        user_id = user.id
        if config.is_user_specified() and user_id not in config.user_id_set:
            logger.debug(f"Unauthorized call of {func.__name__} by user: {user.full_name}, with id: {user_id}")
            if update.effective_message:
                reply = f"Sorry, {user.mention_html()}, it's a private bot, access denied"
                await update.effective_message.reply_html(reply)
            return  # quit function

        log_cmd(user, func.__name__)
        return await func(update, *args, **kwargs)
    return inner


async def answer_query(query) -> None:
    await query.answer()
