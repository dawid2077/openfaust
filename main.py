import os
import discord
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from multiprocessing import Process
from multiprocessing import Process, Queue 
from discord.ext import tasks
from pathlib import Path

from dockersetup import init_db

init_db()

from api import call_mistral
from save_messages import save_normal_message
from kairos import decide
from context import context_kairos
from heartbeat import heartbeat




load_dotenv(dotenv_path="./data/config.txt")

active_channel_id=0
user_message_log = {}
DAILY_LIMIT=os.getenv("MESSAGES_BY_USER_LIMIT")
DAILY_LIMIT=int(DAILY_LIMIT)



personality_path= Path(os.getenv("APP_PERSONALITY_PATH", "./data/personality.md"))
try:
    with open(personality_path, "r", encoding="utf-8") as f:
        personality = f.read()
except Exception as e:
    print(f"DEBUG: Could not load personality file: {e}")


def split_message(content, limit=2000):
    for i in range(0, len(content), limit):
        yield content[i:i + limit]



intents = discord.Intents.default()
intents.message_content = True  #idk
client = discord.Client(intents=intents)


#heartbeat response
@tasks.loop(seconds=5)
async def check_heartbeat_queue():
    if communication_queue.empty():
        return
    trigger=communication_queue.get()
    if trigger =="TRIGGER_WAKE":
        print("firing faust")
        channel=client.get_channel(active_channel_id)
        if channel:
            response = call_mistral("", "", client.user.id, client.user.name,1)
            for chunk in split_message(response):
                await channel.send(chunk)






#here we start queue 
@client.event
async def on_ready():
    print(f'logged in as {client.user}!')
    check_heartbeat_queue.start() 

@client.event
async def on_message(message):
    # disabling answering to her own messages
    if message.author == client.user:
        return
    global active_channel_id
    active_channel_id = message.channel.id
    print(active_channel_id)

    user_id=message.author.id
    nickname = message.author.display_name
    bot_name = client.user.name
    bot_id = client.user.id


    if client.user in message.mentions:

        #rate limit check
        now = datetime.now(timezone.utc)
        day_ago = now - timedelta(days=2)
        
        log = user_message_log.get(user_id, [])
        recent_log = [ts for ts in log if ts > day_ago]
        
        if len(recent_log) >= DAILY_LIMIT:
            await message.reply("Hey, calm down! You've used up your daily quota of messages. Come back tomorrow.")
            return
        
        recent_log.append(now)
        user_message_log[user_id] = recent_log

    
    if client.user in message.mentions:
        #make the question prettier 
        message.content=message.content.split(">")[-1].strip()
        if not message.content.strip():
            print(message.content)
            await message.reply("Wrap it up buddy ")
        else:
            response = call_mistral(message.content, nickname, user_id,bot_id,bot_name)
            for chunk in split_message(response):
                await message.reply(chunk)
    else:
        message.content=message.content.split(">")[-1].strip()
        save_normal_message(message.content,nickname, user_id)
        decision=decide(message.content,context_kairos(),personality)
        #waking up the bot 
        print(decision)
        if decision == "0":
            #basic decision
            pass
        elif decision =="1":
            #staying silent
            pass
        elif decision =="2":
            #short message /casual interaction
            response = call_mistral(message.content, nickname, user_id,bot_id,bot_name)
            for chunk in split_message(response):
                await message.reply(chunk)
        elif decision =="3":
            #normal response
            response = call_mistral(message.content, nickname, user_id,bot_id,bot_name)
            for chunk in split_message(response):
                await message.reply(chunk)
        else:
            print("Kairos error ")
        decision=0

    


communication_queue = Queue()
# runs the script
bg_process = Process(target=heartbeat,args=(communication_queue,), daemon=True)
bg_process.start()

client.run(os.getenv("DISCORD_TOKEN"))
