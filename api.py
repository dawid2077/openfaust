import time
from pathlib import Path
from datetime import datetime, timezone
start = time.perf_counter()  # start timer

import os
import random
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
    if messagecontent=="change_temperature00":
        response = client.chat.completions.create(
            model="mistralai/mistral-small-2603",       
            messages=messages,
            #in future here i will change temperature
            temperature=1,
            extra_body={
                "provider": {
                    "allow_fallbacks": True,
                    "order": ["mistral", "google","openai"]  
                }
            }
        )
        
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

    #TODO get rid of type==1 case
    #type==1 is for heartbeat
    now = datetime.now().astimezone()
    formatted_now = now.strftime("%Y-%m-%d %H:%M:%S.%f%z")
    time = f"{formatted_now[:-2]}:{formatted_now[-2:]}"
    if type==1:
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
    #type==2 is for heartbeating personality
    if type==2:

        situational_prompt_1 = (
            "CRITICAL INSTRUCTION: Your internal boredom meter has peaked and you must break the silence. "
            "Share a personal fact, quirk, or an existential realization about yourself. "
            "This thought must be fully derived from your core traits defined in your identity profile above, adapted to reflect your active emotional state."
        )
        situational_prompt_2 = (
            "CRITICAL INSTRUCTION: Review the chat history below. "
            "Your internal boredom has forced you to chime in. "
            "Pick one specific topic, object, or opinion that the users mentioned earlier, single it out, and give an unsolicited review or reaction to it that perfectly aligns with your established personal taste and current mood."
        )
        situational_prompt_3 = (
            "CRITICAL INSTRUCTION: Look at the very last topic brought up in the chat history below. "
            "Do not pivot to a new conversation; "
            "instead, add to it or expand on it by offering a theory, complaint, or observation that matches how you would uniquely view this topic based on your identity profile."
        )
        situational_prompt_4 = (
            "CRITICAL INSTRUCTION: Your internal boredom meter has peaked and you must break the silence. "
            "Formulate a completely new thought, topic, or question that is subtly inspired by or loosely connected to something mentioned much earlier in the chat history. "
            "Do not directly reply to anyone or reference the previous messages explicitly; make it sound like an unprompted idea that naturally popped into your head while you were daydreaming, completely filtered through your core persona traits and active mood."
        )
        #here we roll for the prompt
        situational_prompt=random.choice([situational_prompt_1,situational_prompt_2,situational_prompt_3,situational_prompt_4])
        messages = [{"role": "system", "content": f"""{persona} {events} current time is {time}. 
                     You are in a group chat. Users will have their names prefixed to their messages like 
                     'Name: message'.Every message from users will be strictly prefixed with their unique 
                     name like 'Name: message'. Pay close attention to these prefixes! Do not mix up who said what. 
                     Address the user who sent the final message appropriately if needed, but never prefix your own 
                     response with your name. {situational_prompt}"""}]
        history = context_call()
        messages.extend(history)
        #here add personality
        
        return generate_answer_call(messages,nickname,user_id,messagecontent,bot_id,bot_name)





    #normal flow when tagged /normal message that kairos decided to answer


    messages = [{"role": "system", "content": f"{persona} {events} current time is {time}. You are in a group chat. Users will have their names prefixed to their messages like 'Name: message'.Every message from users will be strictly prefixed with their unique name like 'Name: message'. Pay close attention to these prefixes! Do not mix up who said what. Address the user who sent the final message appropriately if needed, but never prefix your own response with your name."}]
    history = context_call()

    messages.extend(history)

    messages.append({"role": "user", "content": messagecontent})
    print("\n")
    print("\n")
    print(messages)
    return generate_answer_call(messages,nickname,user_id,messagecontent,bot_id,bot_name)








