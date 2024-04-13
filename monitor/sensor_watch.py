"""
Configure actions like notifications or auto system reboot/shutdown in case of undesired sensor reading.

Config:
    Store action config file with configparser inside bot_config/sensor_actions
    config structure - list of action entries:
        "sensor_name.entry_name" = action, value...

GUI:
    add:
        menu with column of buttons - btn text: "sensor name: current reading"
        add condition and action by choosing sensor from menu by name
        configure condition: choose one from button column, then input condition value
        confirm or cancel
    remove:
        clear all menu

Action Conditions:
    more
    less
    in exclusive range

Actions:
    Notify
    Reboot
    Shutdown
"""

from enum import IntFlag, IntEnum
from pathlib import Path
import os
import requests
import configparser
from telegram.ext import CallbackContext
from monitor.bot_utils import logger, DATA_PATH, config
from monitor.sensors_api import get_all_sensors

CONFIG_FILE_NAME = "sensor_actions_config"
SENSOR_WATCH_JOB_NAME = "sensor_watch_job"


class Action(IntFlag):
    Notify = 1
    Reboot = 2
    Shutdown = 4


class Condition(IntEnum):
    More = 0
    Less = 1
    ExclusiveRange = 2


class ConfigEntry:
    def __init__(self, name: str, action: Action, condition: Condition, value) -> None:
        self.name: str = name
        self.action: Action = action
        self.condition: Condition = condition
        self.value = value
        self.failed_condition_num = 0
        self.triggered = False
        if condition == Condition.ExclusiveRange:
            ConfigEntry.parse_range_value(value)
        else:
            self.value = float(value)

    def parse_range_value(value: str) -> tuple:
        min, max = map(float, value.split(':'))
        if min >= max:
            raise ValueError("invalid range")
        return min, max
    
    def check_condition(self, value) -> bool:
        """True if satisfied"""
        if self.condition == Condition.ExclusiveRange:
            try:
                min, max = ConfigEntry.parse_range_value(self.value)
                return min < value and value < max
            except:
                return True
            
        elif self.condition == Condition.More:
            return self.value < value
        else:
            return self.value > value
        
    def get_condition_str(self) -> str:
        if self.condition == Condition.ExclusiveRange:
            return "in range"
        elif self.condition == Condition.Less:
            return "less than"
        else:
            return "more than"
        
    def trigger_action(self, value: float) -> None:
        self.failed_condition_num = 0
        if self.triggered:
            return
                    
        postfix = ""
        if self.action & (Action.Reboot | Action.Shutdown):
            cmd = "shutdown "
            if self.action & Action.Reboot:
                cmd += "-r"
            cmd += f" +{config.reboot_time_minutes}"
            ret = os.system(f"shutdown -r +{config.reboot_time_minutes}")
            if ret != 0:
                postfix = "Failed to execute system action command, please check user permissions"
                logger.warn(postfix)
            else:
                postfix = "The system is going to {}".format("reboot" if self.action & Action.Reboot else "shutdown")

        if self.action & Action.Notify:
            if config.is_user_specified():
                for user_id in config.user_id_set:
                    msg =f"Sensor Watcher Warning: sensor <b>\"{self.name}\"</b> with reading <b>{value}</b> is outside configured: {self.get_condition_str()} <b>{self.value}</b>"
                    if postfix:
                        msg += f"\n{postfix}"
                    payload = {
                        'chat_id': user_id,
                        'text': msg,
                        'parse_mode': 'HTML'
                    }
                    requests.post("https://api.telegram.org/bot{token}/sendMessage".format(token=config.token),
                                        data=payload).content

        self.triggered = True


class SensorActionConfig:
    def __init__(self) -> None:
        self.configEntries: dict[str, ConfigEntry] = {}
        self.config = configparser.ConfigParser()
        self.num_values_in_entry = 3

    def load_config(self) -> None:
        """open or create config file, load config from file"""
        file_path = Path(os.path.join(DATA_PATH, CONFIG_FILE_NAME))
        if file_path.exists():
            with open(file_path) as config_file:
                self.config.read_file(config_file)
                for entry in self.config["DEFAULT"]:
                    value_str = self.config["DEFAULT"][entry]
                    value_str = value_str.replace(" ", "")
                    values = value_str.split(",")
                    if len(values) != self.num_values_in_entry:
                        logger.error(f"Failed to load Sensor Action config entry: {entry} - invalid value structure")
                    else:
                        try:
                            config_entry = ConfigEntry(entry, int(values[0]), int(values[1]), values[2])
                            self.configEntries[entry] = config_entry
                        except Exception as e:
                            logger.error(f"Failed to load Sensor Action config entry: {entry} - {e}")
        else:
            fp = open(file_path, mode="x")
            fp.close()

    def update_config(self, entry: ConfigEntry) -> None:
        """rewrite file with new config"""
        self.configEntries[entry.name] = entry
        file_path = Path(os.path.join(DATA_PATH, CONFIG_FILE_NAME))
        with open(file_path, mode="w") as fp:
            self.config["DEFAULT"][entry.name] = f"{entry.action}, {entry.condition}, {entry.value}"
            self.config.write(fp)


async def on_check_sensors(context: CallbackContext):
    if len(sensor_action_config.configEntries) == 0:
        return
    
    sensors = get_all_sensors()
    for name, action_item in sensor_action_config.configEntries.items():
        sensor = sensors.get(name, None)
        if sensor:
            if action_item.check_condition(sensor.value):
                action_item.triggered = False
            else:
                action_item.failed_condition_num += 1
                if action_item.failed_condition_num >= config.sensor_watch_threshold:
                    action_item.trigger_action(sensor.value)                
    

sensor_action_config = SensorActionConfig()
