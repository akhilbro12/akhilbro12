from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
import sys
import time
import os
import json
import asyncio
from telethon.tl.functions.messages import ForwardMessagesRequest
from telethon.errors import PhoneCodeInvalidError, PhoneNumberInvalidError
from telethon.errors import UserDeactivatedError, UserDeactivatedBanError

# Your Credintals here use yours
USER_ID = ADMIN_ID #For ex 123456789
API_ID = 'REPLACE_API"  
API_HASH = "REPLACE_API_HASH"  
BOT_TOKEN = "YOURBOT_TOKEN_FOR_CONTROL"
SESSION_DIR = "sessions"
os.makedirs(SESSION_DIR, exist_ok=True)
user_states = {}
user_settings = {}
user_intervals = {}
user_speeds = {}
settings_messages = {}
bot = TelegramClient("TGbot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
async def notify_startup():
    try:
        await bot.send_message(USER_ID, "**Bot has been Started!**", parse_mode='markdown')
        print("Notified Admin 🗣️")
    except Exception as e:
        print(f"Failed to send notification: {e}")
def get_session_file(user_id):
    return os.path.join(SESSION_DIR, f"{user_id}_session.json")
def save_session(user_id, session_string):
    session_file = get_session_file(user_id)
    with open(session_file, 'w') as f:
        json.dump({'session': session_string}, f)
def load_session(user_id):
    session_file = get_session_file(user_id)
    if os.path.exists(session_file):
        with open(session_file, 'r') as f:
            data = json.load(f)
            return StringSession(data['session'])
    return None
def is_logged_in(user_id):
    return os.path.exists(get_session_file(user_id))
@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    user_id = event.sender_id
    if is_logged_in(user_id):
        await event.reply("**Welcome back!\nUse /autosend to start forwarding✅** .", parse_mode='markdown')
    else:
        await event.reply("**Welcome!\nUse /login to add your account & Continue.**", parse_mode='markdown')
@bot.on(events.NewMessage(pattern="/login"))
async def login(event):
    user_id = event.sender_id
    if await check_session_validity(user_id, event):
        await event.reply("**You already have an active account.**", parse_mode='markdown')
        return
    await event.reply("**Please enter your phone number (in international format, e.g., +123456789):**", parse_mode='markdown')
    user_states[user_id] = {"state": "awaiting_phone_number"}
from telethon.errors import PhoneCodeExpiredError  
@bot.on(events.NewMessage)
async def handle_login_steps(event):
    user_id = event.sender_id
    state = user_states.get(user_id)
    if state and state.get("state") == "awaiting_phone_number":
        phone_number = event.message.message
        if phone_number.startswith("/"):
            return  
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        try:
            progress_message = await event.reply("**Sending OTP...**\n`▱▱▱▱▱▱▱▱▱▱ 0%`")
            for i in range(1, 11):
                progress = "▰" * i + "▱" * (10 - i)
                await progress_message.edit(f"**Sending OTP...**\n`{progress} {i * 10}%`")
                await asyncio.sleep(0.05)  
            await client.send_code_request(phone_number)
            user_states[user_id] = {
                "phone_number": phone_number,
                "client": client,
                "state": "awaiting_otp"
            }
            await progress_message.edit("**OTP sent💬! Please enter the OTP:**", parse_mode='markdown')
        except PhoneNumberInvalidError:
            await progress_message.edit("**Incorrect number❌. Please enter a valid phone number.**", parse_mode='markdown')
        except Exception as e:
            await progress_message.edit(f"**Error sending OTP: {e}**", parse_mode='markdown')
        finally:
            await client.disconnect()
    elif state and state.get("state") == "awaiting_otp":
        otp = event.message.message
        phone_number = state.get("phone_number")
        client = state.get("client")
        try:
            await client.connect()
            await client.sign_in(phone_number, otp)
            save_session(user_id, client.session.save())
            user_states.pop(user_id, None)
            await event.reply("**Logged in successfully! You can now use /autosend.**", parse_mode='markdown')
        except SessionPasswordNeededError:
            user_states[user_id] = {"client": client, "state": "awaiting_password"}
            await event.reply("**This account has 2FA enabled🔐. Please enter your password:**", parse_mode='markdown')
        except PhoneCodeInvalidError:
            await event.reply("**Incorrect OTP. Please try again.❌**", parse_mode='markdown')
        except PhoneCodeExpiredError:
            await event.reply("**Code Expired Login Again🚫**", parse_mode='markdown')
        except Exception as e:
            await event.reply(f"**Error during OTP verification: {e}**", parse_mode='markdown')
        finally:
            await client.disconnect()
    elif state and state.get("state") == "awaiting_password":
        password = event.message.message
        client = state.get("client")
        try:
            await client.connect()
            await client.sign_in(password=password)  
            save_session(user_id, client.session.save())
            user_states.pop(user_id, None)
            await event.reply("**Logged in successfully! You can now use /autosend.**", parse_mode='markdown')
        except Exception as e:
            await event.reply(f"**Error during 2FA login: {e}**", parse_mode='markdown')
        finally:
            await client.disconnect()
           
@bot.on(events.NewMessage(pattern='/about'))
async def about(event):
    sender = await event.get_sender()
    firstname = sender.first_name
    await event.reply(
        f"**Hello 👋, {firstname}**\n"
        "🤖 **Bot version :** `v0.13.6`\n"
        "💟 **Owner : @SoulHuz**\n"
        "🔤 **Language :** `Python 3.14`\n"
        "🗃️ **Server :** `KnockKnockServer 4444`",
        parse_mode='markdown'
    )

@bot.on(events.NewMessage(pattern="/settings"))
async def settings(event):
    user_id = event.sender_id
    current_setting = user_settings.get(user_id, False)
    current_speed = user_speeds.get(user_id, 2)  
    if user_id in settings_messages:
        message_id = settings_messages[user_id]
        await bot.edit_message(
            event.chat_id, message_id,
            f"Choose your settings:\nCurrent Speed: {current_speed} seconds\nChoose whether to show 'Forwarded from' or not:",
            buttons=[
                [Button.inline(f"Show 'Forwarded from' (ON⏸️)" if current_setting else "Show 'Forwarded from' (OFF⏸️)", data="toggle_forwarded_header")],
                [Button.inline(f"Current Speed: {current_speed} seconds", data="change_speed")]
            ]
        )
    else:
        message = await event.reply(
            f"Choose your settings:\nCurrent Speed: {current_speed} seconds\nChoose whether to show 'Forwarded from' or not:",
            buttons=[
                [Button.inline(f"Show 'Forwarded from' (ON⏸️)" if current_setting else "Show 'Forwarded from' (OFF⏸️)", data="toggle_forwarded_header")],
                [Button.inline(f"Current Speed: {current_speed} seconds", data="change_speed")]
            ]
        )
        settings_messages[user_id] = message.id
@bot.on(events.CallbackQuery(pattern="change_speed"))
async def prompt_for_speed(event):
    user_id = event.sender_id
    await event.reply("**Please enter the new speed in seconds💨 :**", parse_mode='markdown')
    user_states[user_id] = {"state": "awaiting_speed"}
@bot.on(events.NewMessage)
async def handle_speed_input(event):
    user_id = event.sender_id
    state = user_states.get(user_id)
    if state and state.get("state") == "awaiting_speed":
        try:
            speed = float(event.message.message)
            if speed <= 0:
                await event.reply("**Speed must be a positive number.💨 Please try again.**", parse_mode='markdown')
                return
            user_speeds[user_id] = speed
            user_states.pop(user_id, None)  
            await event.reply(f"**Speed updated to {speed} seconds per message.**", parse_mode='markdown')
            await settings(event)  
        except ValueError:
            await event.reply("**Invalid input. Please enter a number (e.g., 1, 0.5, 2.3).**", parse_mode='markdown')
@bot.on(events.CallbackQuery(pattern="toggle_forwarded_header"))
async def toggle_forwarded_header(event):
    user_id = event.sender_id
    current_setting = user_settings.get(user_id, False)
    new_setting = not current_setting
    user_settings[user_id] = new_setting
    await event.answer(f"Forwarded header {'enabled' if new_setting else 'disabled'}")
    if user_id in settings_messages:
        message_id = settings_messages[user_id]
        print(f"Editing message ID {message_id} to show new setting")
        await bot.edit_message(event.chat_id, message_id, 
            "Choose whether to show 'Forwarded from' or not:",
            buttons=[
                [Button.inline(f"Show 'Forwarded from' (ON⏸️)" if new_setting else "Show 'Forwarded from' (OFF⏸️)", data="toggle_forwarded_header")]
            ]
        )
    else:
        await event.reply("Settings message not found.")
user_pause_states = {}
ongoing_sessions = {}
@bot.on(events.CallbackQuery(pattern=r"cancel_"))
async def cancel_handler(event):
    user_id = int(event.data.decode().split("_")[2])
    if user_id in ongoing_sessions:
        session_data = ongoing_sessions[user_id]
        processing_msg = session_data.get("processing_msg")
        if processing_msg:
            await processing_msg.delete()
        telethon_client = session_data.get("telethon_client")
        if telethon_client:
            await telethon_client.disconnect()
        ongoing_sessions.pop(user_id, None)
        await event.answer("Forwarding canceled ❌")
        await event.reply("**Forwarding session canceled.**")
    else:
        await event.answer("No active session to cancel.")
from telethon import Button
ongoing_sessions = {} 
async def check_session_validity(user_id, event=None):
    session_string = load_session(user_id)
    if not session_string:
        return False
    client = TelegramClient(session_string, API_ID, API_HASH)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            if event:
                await event.reply("**Your session is invalid or has been logged out. Please use /login to add your account again.**", parse_mode='markdown')
            os.remove(get_session_file(user_id))  
            return False
        return True
    except (UserDeactivatedError, UserDeactivatedBanError):
        if event:
            await event.reply("**Your account has been deactivated or banned by Telegram. Please contact support @SoulHuz if you believe this is an error.**", parse_mode='markdown')
        os.remove(get_session_file(user_id))  
        return False
    finally:
        await client.disconnect()
        
@bot.on(events.NewMessage(pattern='/speed'))
async def speed_test(event):
    start_time = time.time()
    msg = await event.reply("**Processing...**")
    response_time = time.time() - start_time
    await msg.edit(f"**🚄 Connection Status**\n**Response Time:** `{response_time:.2f}` **seconds**")
    
@bot.on(events.NewMessage(pattern="/autosend"))
async def autosend(event):
    user_id = event.sender_id
    if not await check_session_validity(user_id, event):
        return  
    processing_msg = await event.reply(
        "**Sending messages to groups...**",
        buttons=[Button.inline("Cancel", b"cancel_sending")],
        parse_mode='markdown'
    )
    if user_id not in user_intervals:
        await processing_msg.edit("**Please enter the time delay (in minutes) between rounds of sending messages**:", parse_mode='markdown')
        user_states[user_id] = {"state": "awaiting_interval"}
        return
    interval = user_intervals[user_id]
    while True:
        if user_id in user_pause_states and user_pause_states[user_id]:
            await processing_msg.edit("**Paused. Press RESUME to continue.**")
            while user_pause_states.get(user_id):
                await asyncio.sleep(5)  
            await processing_msg.edit("**Resumed.**")
        if not await check_session_validity(user_id, event):
            await processing_msg.edit("Session expired or invalid. Please log in again.")
            return
        session_string = load_session(user_id)
        show_forwarded_header = user_settings.get(user_id, False)
        try:
            telethon_client = TelegramClient(session_string, API_ID, API_HASH)
            async with telethon_client as client:
                if not await client.is_user_authorized():
                    await processing_msg.edit("Session expired or invalid. Please log in again.")
                    return
                bot_username = '@RealisticXX_bot'
                try:
                    bot_entity = await client.get_entity(bot_username)
                    messages = await client.get_messages(bot_entity, limit=1)
                    if not messages:
                        await processing_msg.edit(f"No messages found in {bot_username}.")
                        return
                    last_message = messages[0]
                except Exception:
                    pass  
                dialogs = await client.get_dialogs()
                group_peers = {}
                for dialog in dialogs:
                    if dialog.is_group:
                        try:
                            input_peer = await client.get_input_entity(dialog.id)
                            group_peers[dialog.id] = input_peer
                        except Exception:
                            pass  
                if not group_peers:
                    await processing_msg.edit("**No groups found to send the message.**", parse_mode='markdown')
                    return
                ongoing_sessions[user_id] = {"processing_msg": processing_msg, "telethon_client": telethon_client}
                total_groups = 0  
                for chat_id, input_peer in group_peers.items():
                    if user_id in ongoing_sessions and ongoing_sessions[user_id].get('cancelled', False):
                        await processing_msg.edit("**Message sending canceled.**")
                        return
                    try:
                        if show_forwarded_header:
                            await client.forward_messages(input_peer, last_message.id, bot_entity)
                        else:
                            await client.send_message(input_peer, last_message.text)
                        total_groups += 1 
                        await asyncio.sleep(0.01) 
                    except Exception:
                        pass 
                await processing_msg.edit(f"**Messages successfully sent to {total_groups} groups.**")
                await processing_msg.edit(f"**Waiting for {interval} minutes before the next round...**", parse_mode='markdown')
                await asyncio.sleep(interval * 60)  
        except Exception:
            pass
        finally:
            await telethon_client.disconnect()
@bot.on(events.CallbackQuery(data=b"cancel_sending"))
async def cancel_sending(event):
    user_id = event.sender_id
    if user_id in ongoing_sessions:
        ongoing_sessions[user_id]['cancelled'] = True
        await event.edit("**Message sending canceled.**")
    else:
        await event.answer("No ongoing message sending process to cancel.", alert=True)
@bot.on(events.NewMessage)
async def handle_interval_input(event):
    user_id = event.sender_id
    state = user_states.get(user_id)
    if state and state.get("state") == "awaiting_interval":
        if event.message.message.startswith('/'):
            return
        try:
            interval = int(event.message.message)
            if interval <= 0:
                await event.reply("**The interval must be a positive number. Please enter a valid time delay (in minutes).**", parse_mode='markdown')
                return
            user_intervals[user_id] = interval
            await event.delete()
            user_states[user_id]["state"] = "ready_to_autosend"
            await autosend(event)
        except ValueError:
            await event.reply("**Invalid input. Please enter a valid number representing the time delay (in minutes).**", parse_mode='markdown')
@bot.on(events.CallbackQuery(pattern=r"pause_"))
async def pause_handler(event):
    user_id = int(event.data.decode().split("_")[2])
    user_pause_states[user_id] = True
    await event.answer("Paused ⏸️")
    await event.edit("**Sending paused. Press RESUME ▶️ to continue.**")
@bot.on(events.CallbackQuery(pattern=r"resume_"))
async def resume_handler(event):
    user_id = int(event.data.decode().split("_")[2])
    user_pause_states[user_id] = False
    await event.answer("Resumed ▶️")
    await event.edit("**Sending resumed.**")

@bot.on(events.NewMessage(pattern="/restart"))
async def restart(event):
    if event.sender_id == 5421296573:  # Admin check
        await event.reply("Restarting the bot...")
        os.execv(sys.executable, ['python'] + sys.argv)
    else:
        await event.reply("You are not authorized to use this command.")
@bot.on(events.NewMessage(pattern="/logout"))
async def logout(event):
    user_id = event.sender_id
    if is_logged_in(user_id):
        await event.reply("**Are you sure you want to logout?**", buttons=[
            [Button.inline("Logout 🫱", data=f"confirm_logout_{user_id}")]
        ], parse_mode='markdown')
    else:
        await event.reply("**You are not logged in. Use /login to add your account first.**", parse_mode='markdown')
@bot.on(events.CallbackQuery(pattern=r"confirm_logout_"))
async def confirm_logout(event):
    user_id = int(event.data.decode().split("_")[2])
    if is_logged_in(user_id):
        session_file = get_session_file(user_id)
        try:
            os.remove(session_file)  
            await event.reply("You have been logged out successfully.")
            await event.answer("Logged out!")
        except Exception as e:
            await event.reply(f"**Error while logging out:** `{e}`", parse_mode='markdown')
    else:
        await event.reply("**You are not logged in.**", parse_mode='markdown')
        await event.answer("No active session.")
print("Bot is starting...")
async def main():
    await notify_startup()
    await bot.run_until_disconnected()
bot.loop.run_until_complete(main())
