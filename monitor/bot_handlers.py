from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.error import TelegramError
from telegram.ext import CallbackContext, ContextTypes
from telegram.constants import ParseMode
from monitor.bot_utils import (
    user_restricted,
    log_cmd,
    answer_query,
    logger,
    config
)
from monitor.bot_utils import (
    SOURCE_WEB_LINK,
    QUERY_PATTERN_REFRESH,
    QUERY_PATTERN_TOGGLE_REFRESH,
    QUERY_PATTERN_CONFIRM_REBOOT
)
from monitor.sensors_api import (
    get_sensors_fan_speeds,
    get_sensors_temperatures,
    temperatures_to_str,
    fans_to_str,
    get_gpu_temps,
    gpu_temps_to_str,
    get_gpu_fans,
    gpu_fans_to_str
)
import os
from datetime import datetime


def get_header_text(print_refresh_rate: bool = False) -> str:
    dt = datetime.now().strftime("%d/%m/%y %H:%M:%S")
    if print_refresh_rate:
        return f"<i>Auto update is enabled, refresh rate: {config.update_period_seconds}s</i>" + "\n<b>" + dt + "</b>\n"
    else:
        return "<b>" + dt + "</b>\n"
    

def get_sensors_text() -> str:
    fans = get_sensors_fan_speeds()
    temps = get_sensors_temperatures()
    gpu_temps = get_gpu_temps()
    gpu_str = gpu_temps_to_str(gpu_temps)
    res_str = temperatures_to_str(temps)
    gpu_fans = get_gpu_fans()
    gpu_fans_str = gpu_fans_to_str(gpu_fans)

    if gpu_str:
        res_str += '\n' + gpu_str
    res_str += '\n\n' + fans_to_str(fans)
    if gpu_fans_str:
        res_str += '\n' + gpu_fans_str

    return res_str


def get_info_text(print_refresh_rate: bool = False) -> str:
    return get_header_text(print_refresh_rate) + get_sensors_text()


def get_refresh_markup() -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton(text="Refresh", callback_data=QUERY_PATTERN_REFRESH)],
                [InlineKeyboardButton(text="Toggle auto refresh", callback_data=QUERY_PATTERN_TOGGLE_REFRESH)]]
    return InlineKeyboardMarkup(keyboard)


async def on_auto_refresh(context: CallbackContext):
    reply = get_info_text(True)
    try:
        await context.job.data.edit_text(text=reply, reply_markup=get_refresh_markup(), parse_mode=ParseMode.HTML)
    except TelegramError:  # message was deleted
        context.job.schedule_removal()
        reply = get_info_text(False)
        await context.job.data.edit_text(text=reply, reply_markup=get_refresh_markup(), parse_mode=ParseMode.HTML)


@user_restricted
async def start_cmd(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    reply = f"Hi, {user.mention_html()}! Call /help to get info about bot usage"
    await update.message.reply_html(reply)


@user_restricted
async def print_readouts_cmd(update: Update, context: CallbackContext) -> None:
    """Query configured sensor and system info."""
    reply = get_info_text()

    await update.message.reply_html(text=reply, reply_markup=get_refresh_markup())


@user_restricted
async def reboot_cmd(update: Update, context: CallbackContext) -> None:
    reply = "Are you sure you want to reboot the host?"
    keyboard = [[InlineKeyboardButton(text="Do it!", callback_data=QUERY_PATTERN_CONFIRM_REBOOT)]]
    markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_html(text=reply, reply_markup=markup)

@user_restricted
async def refresh_button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    context.application.create_task(answer_query(query), update=update)
    
    reply = get_info_text()
    try:
        await update.effective_message.edit_text(text=reply, reply_markup=get_refresh_markup(), parse_mode=ParseMode.HTML)
    except TelegramError:  # causes error when message has not changed, ignore
        pass

@user_restricted
async def reboot_button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    context.application.create_task(answer_query(query), update=update)
    
    ret = os.system(f"shutdown -r +{config.reboot_time_minutes}")
    if ret != 0:
        await update.effective_message.reply_html(f"Failed to execute reboot command, please check user permissions")
    else:
        await update.effective_message.reply_html(f"Rebooting in {config.reboot_time_minutes} {'minutes' if config.reboot_time_minutes > 1 else 'minute'}...")
        
    try:
        await update.effective_message.delete()
    except TelegramError:
        logger.error(msg="Failed to delete progress message")


@user_restricted
async def toggle_refresh_button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    context.application.create_task(answer_query(query), update=update)

    reply = get_info_text()
    try:
        await update.effective_message.edit_text(text=reply, reply_markup=get_refresh_markup(), parse_mode=ParseMode.HTML)
    except TelegramError:  # causes error when message has not changed, ignore
        pass

    if context.job_queue.jobs():
        await context.job_queue.stop()
        await context.job_queue.start()
    else:
        context.job_queue.run_repeating(on_auto_refresh, config.update_period_seconds, data=update.effective_message)


@user_restricted
async def help_cmd(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    log_cmd(user, "help_cmd")
    help_msg = ("Bot usage: select from the menu or type commands to interact with the bot. List of commands:\n\n"
                "<u>print_sensors</u> - display current sensor readouts on host machine\n\n"
                "<u>reboot_host</u> - attempt to execute reboot on host machine (root access required)\n\n"
                f"Take a look at source code for additional info, or to try it out yourself at<a href='{SOURCE_WEB_LINK}'>GitHub</a>")
    await update.message.reply_html(help_msg, disable_web_page_preview=True)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    if update and update.effective_message and update.effective_user:
        reply = f"Sorry {update.effective_user.mention_html()}, there has been a Server Internal Error when processing your command, please try again"
        try:
            await update.effective_message.reply_html(reply, reply_to_message_id=update.effective_message.message_id)
        except TelegramError:  # if reply message was deleted
            await context.bot.send_message(chat_id=update.effective_chat.id, text=reply, parse_mode=ParseMode.HTML)
