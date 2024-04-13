from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    AIORateLimiter,
    ExtBot
)
from telegram import Bot, request
import asyncio
import os.path
from monitor.bot_handlers import (
    start_cmd,
    print_readouts_cmd,
    reboot_cmd,
    refresh_button,
    toggle_refresh_button,
    reboot_button,
    shutdown_cmd,
    shutdown_button,
    help_cmd,
    error_handler
)
import monitor.bot_utils as utils
from monitor.sensor_watch import sensor_action_config, on_check_sensors, SENSOR_WATCH_JOB_NAME
import requests
import signal


def initialize_bot_config() -> None:
    utils.config.load_config(os.path.join(utils.DATA_PATH, utils.CONFIG_FILE_NAME))
    sensor_action_config.load_config()


def init_http_request() -> request.HTTPXRequest:
    return request.HTTPXRequest(http_version="1.1", connection_pool_size=8, read_timeout=30, write_timeout=30)


async def init_bot_settings() -> ExtBot:
    bot = ExtBot(utils.config.token, request=init_http_request(),
              get_updates_request=init_http_request(), rate_limiter=AIORateLimiter())
    cmds = [("print_sensors", "Display current system info"),
            ("reboot_host", "Reboot with configured delay"),
            ("shutdown_host", "Shutdown with configured delay"),
            ("help", "Get command usage help")]
    await bot.set_my_commands(commands=cmds, language_code="en")
    if utils.config.is_user_specified():
        for user_id in utils.config.user_id_set:
            await bot.send_message(chat_id=user_id, text="System monitor online")
    return bot


def create_bot() -> Bot:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    task = loop.create_task(init_bot_settings())
    loop.run_until_complete(task)

    return task.result()

def finalize_bot() -> None:
    if utils.config.is_user_specified():
        for user_id in utils.config.user_id_set:
            msg ="System monitor offline"
            payload = {
                'chat_id': user_id,
                'text': msg,
                'parse_mode': 'HTML'
            }
            requests.post("https://api.telegram.org/bot{token}/sendMessage".format(token=utils.config.token),
                                data=payload).content


def run_application() -> None:

    application = Application.builder().bot(create_bot()).build()

    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("print_sensors", print_readouts_cmd))
    application.add_handler(CommandHandler("reboot_host", reboot_cmd))
    application.add_handler(CommandHandler("shutdown_host", shutdown_cmd))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CallbackQueryHandler(refresh_button, pattern=f"^{utils.QUERY_PATTERN_REFRESH}*"))
    application.add_handler(CallbackQueryHandler(toggle_refresh_button, pattern=f"^{utils.QUERY_PATTERN_TOGGLE_REFRESH}*"))
    application.add_handler(CallbackQueryHandler(reboot_button, pattern=f"^{utils.QUERY_PATTERN_CONFIRM_REBOOT}*"))
    application.add_handler(CallbackQueryHandler(shutdown_button, pattern=f"^{utils.QUERY_PATTERN_CONFIRM_SHUTDOWN}*"))

    application.add_error_handler(error_handler)
    application.job_queue.run_repeating(on_check_sensors, utils.config.sensor_watch_time, name=SENSOR_WATCH_JOB_NAME)

    application.run_polling(stop_signals=[signal.SIGINT, signal.SIGTERM])


def main() -> None:
    initialize_bot_config()

    run_application()

    finalize_bot()


if __name__ == "__main__":
    main()
