import time
from pathlib import Path
from datetime import datetime, timezone
start = time.perf_counter()  # start timer

import os
from dotenv import load_dotenv
from openai import OpenAI


from tosqlite import save
from context import context_call


load_dotenv()

# Grab your key.
api_key = os.getenv("OPENROUTER_API_KEY") 

if not api_key:
    raise ValueError("ERROR: Could not find an API key in your .env file! Make sure OPENROUTER_API_KEY is set.")

# Initialize OpenRouter Client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key
) 

def generate_answer_call(messages: list, nickname: str = "",user_id: int=0,messagecontent: str="",bot_id=1 ,bot_name=""):
    event=" "
    response = client.chat.completions.create(
        model="mistralai/mistral-small-2603",       
        messages=messages,
        extra_body={
            "provider": {
                "allow_fallbacks": True,
                "order": ["mistral", "google","openai"]  
            }
        }
    )
    #save it to sqlite database
    data=response.model_dump_json()
    save(nickname, data,user_id,messagecontent,bot_id,bot_name)

    return response.choices[0].message.content


def call_mistral(messagecontent: str, nickname: str = "Alex",user_id: int=0,bot_id=1,bot_name="",type=0):
    events=" "
    personality_path= Path(os.getenv("APP_PERSONALITY_PATH", "./data/personality.md"))

    # Safely load the personality
    try:
        with open(personality_path, "r", encoding="utf-8") as f:
            persona = f.read()
    except Exception as e:
        print(f"DEBUG: Could not load personality file: {e}")
    #type==1 is for heartbeat
    if type==1:
        now = datetime.now().astimezone()
        formatted_now = now.strftime("%Y-%m-%d %H:%M:%S.%f%z")
        time = f"{formatted_now[:-2]}:{formatted_now[-2:]}"
        #prompts for kairos and combining messages
        situational_prompt = (
            "SYSTEM DIRECTIVE: The channel has been completely silent and dead for a long time. "
            "You have decided to autonomously break the silence. Review the previous topic or "
            "the room's current state. Respond completely in-character, either"
            " bringing up a completely new thought that fits your profil or targeting someone's "
            "last remark sarcastically"
            "Do not acknowledge this system message; speak directly to the channel."
        )
        messages = [{"role": "system", "content": f"""{persona} {events} current time is {time}. 
                     You are in a group chat. Users will have their names prefixed to their messages like 
                     'Name: message'.Every message from users will be strictly prefixed with their unique 
                     name like 'Name: message'. Pay close attention to these prefixes! Do not mix up who said what. 
                     Address the user who sent the final message appropriately if needed, but never prefix your own 
                     response with your name. {situational_prompt}"""}]
        history = context_call()

        messages.extend(history)

        return generate_answer_call(messages,nickname,user_id,messagecontent,bot_id,bot_name)




    #normal flow when tagged /normal message that kairos decided to answer

    now = datetime.now().astimezone()
    formatted_now = now.strftime("%Y-%m-%d %H:%M:%S.%f%z")
    time = f"{formatted_now[:-2]}:{formatted_now[-2:]}"
    messages = [{"role": "system", "content": f"{persona} {events} current time is {time}. You are in a group chat. Users will have their names prefixed to their messages like 'Name: message'.Every message from users will be strictly prefixed with their unique name like 'Name: message'. Pay close attention to these prefixes! Do not mix up who said what. Address the user who sent the final message appropriately if needed, but never prefix your own response with your name."}]
    history = context_call()

    messages.extend(history)

    messages.append({"role": "user", "content": messagecontent})
    print("\n")
    print("\n")
    print(messages)
    return generate_answer_call(messages,nickname,user_id,messagecontent,bot_id,bot_name)







