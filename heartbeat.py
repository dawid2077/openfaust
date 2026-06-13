import time
import os
from pathlib import Path
from datetime import datetime, timedelta,timezone
from multiprocessing import Process

from dotenv import load_dotenv

from kairos import decide
from context import context_kairos


load_dotenv(dotenv_path="./data/config.txt")
RESET_ANCHOR = datetime.now(timezone.utc)
data_path = os.getenv("APP_DATA_PATH", "./data/")
db_path = os.path.join(data_path, "data.db")

personality_path = "/app/data/personality.md"
personality_path= Path(os.getenv("APP_PERSONALITY_PATH", "./data/personality.md"))

try:
    with open(personality_path, "r", encoding="utf-8") as f:
        CHARACTER_PROFILE= f.read()
except Exception as e:
    print(f"DEBUG: Could not load personality file: {e}")        



def restart_limit():
    global RESET_ANCHOR
    now = datetime.now(timezone.utc)
    
    days_after_limit_resets=os.getenv("DAYS_AFTER_LIMIT_RESETS","./data/config.txt")
    days_after_limit_resets=int(days_after_limit_resets)
    if now - RESET_ANCHOR >= timedelta(days_after_limit_resets):
        RESET_ANCHOR = now  
        global daily_limit
        daily_limit=0

def check_limits(daily_limit):
    daily_limit_max=os.getenv("DAILY_LIMIT_MAX")
    daily_limit_max=int(daily_limit_max)



    if daily_limit >= daily_limit_max:
        return "daily limit for heartbeat used"
    return 0

def heartbeat(task_queue):


    #Runs in background every 30 minutes
    daily_limit=0
    while True:
        heartbeat_time=os.getenv("HEARTBEAT_TIME_SECONDS")
        heartbeat_time=int(heartbeat_time)
        time.sleep(heartbeat_time)
        print("[Background] Running heartbeat...")


        #check if the required time was passed
        restart_limit()


        
        if check_limits(daily_limit)==0:
            pass
        else:
            print(check_limits)
            print("going to sleep")
            continue
        
        #logic
        kairos_instruction = (
            f"You are Kairos, an intelligent, event-driven routing engine and context-gatekeeper for an AI companion.\n\n"
            f"### TARGET CHARACTER PROFILE:\n"
            f"{CHARACTER_PROFILE}\n\n"
            f"Your current task is an autonomous BACKGROUND HEARTBEAT CHECK because the channel has gone silent. "
            f"Review the recent chat history and determine if it fits this specific character's personality profile "
            f"to spontaneously break the silence and engage with the room.\n\n"
            f"### CONTEXT EVALUATION RULES:\n"
            f"1. Action '1' (STAY SILENT):\n"
            f"   - If the previous conversation ended naturally or wrapped up conclusively.\n"
            f"   - If the last few messages cover topics that this specific character profile would find uninteresting, "
            f"irrelevant, or out-of-character to comment on.\n"
            f"   - If the Daily Counter Status shows they have already initiated a chat multiple times today.\n\n"
            f"2. Action '3' (ENGAGE / POKE USER):\n"
            f"   - If the conversation was cut off mid-thought, or left hanging on an open topic that aligns directly "
            f"with the character's interests, traits, or expertise.\n"
            f"   - If there is a topic left unaddressed that this character would highly desire to react to, critique, "
            f"joke about, or dive into based on their profile.\n"
            f"   - If the Daily Counter Status is low, leaving conversational budget to burn.\n\n"
            f"### OUTPUT FORMAT:\n"
            f"Respond ONLY with a valid JSON object. No markdown code blocks, no extra text.\n"
            f"{{\n"
            f"  'action': '1'\n"
            f"}}\n"
            f"OR\n"
            f"{{\n"
            f"  'action': '3'\n"
            f"}}"
        )
        decision =decide("",context_kairos(db_path,"10"),kairos_instruction)
        print("heartbeat decision", decision)
        if decision == "0":
            pass
        elif decision =="1":
            pass
        elif decision =="3":
            #call_main
            task_queue.put("TRIGGER_WAKE")
        else:
            print("Kairos error in heartbeat ")
        decision=0

        daily_limit+=1
if __name__=="__main__":
    restart_limit()
    heartbeat()







