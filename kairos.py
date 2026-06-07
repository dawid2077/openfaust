import os
from openai import OpenAI
from dotenv import load_dotenv
import json
import time

from context import context_kairos





def decide(new_message,context,CHARACTER_PROFILE):
    print(new_message)

    load_dotenv()
    system_instructions = (
        f"You are Kairos, an intelligent, event-driven routing engine and context-gatekeeper for an AI companion.\n\n"
        f"### TARGET CHARACTER PROFILE:\n"
        f"{CHARACTER_PROFILE}\n\n" 
        f"### SYSTEM OBJECTIVE:\n"
        f"Analyze the entire conversation history provided in the messages array and evaluate the VERY LAST message. "
        f"Determine the identity, name, and pronouns of the companion using the provided TARGET CHARACTER PROFILE. "
        f"Your sole job is to decide if the companion should respond to this last message based on conversational momentum and context.\n\n"
        f"### CONVERSATIONAL MOMENTUM RULES:\n"
        f"1. DIRECT REPLY EXPECTATION: Check the timestamp metadata in the chat history (e.g., 'Last message sent X minutes ago'). "
        f"If the companion spoke very recently (0 to 2 minutes ago), and a user immediately sends a new message without tagging "
        f"or naming another explicit person, assume they are speaking directly back to the companion.\n"
        f"2. OPEN QUESTIONS: If the companion's last message ended in a question or explicitly demanded user input, "
        f"and a user provides a rapid response within that short time window, treat this as a continuous conversation.\n\n"
        f"### ROUTING CLASSIFICATION (CHOOSE ONE):\n"
        f"- Output {{\"action\": \"1\"}} (SILENT): The message is generic background chatter, or users are clearly talking to each other.\n"
        f"- Output {{\"action\": \"2\"}} (REACT): The message is a casual greeting to the room ('hi everyone') or short, non-urgent presence chatter.\n"
        f"- Output {{\"action\": \"3\"}} (ENGAGE): The message explicitly mentions the companion's name, directly asks the companion a question, "
        f"or represents an immediate, rapid answer to a question the companion just asked.\n\n"
        f"### CRITICAL COMPLIANCE:\n"
        f"If the message matches a CONVERSATIONAL MOMENTUM RULE or explicitly references the companion's name, you MUST return \"3\".\n"
        f"Output ONLY a valid JSON object matching this schema: {{\"action\": \"1\" | \"2\" | \"3\"}}."
    )

        

    client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    #its using openai from openrouter
    api_key=os.getenv("OPENROUTER_API_KEY")
    )
    try:
        api_messages = [{"role": "system", "content": system_instructions}]
        
        if isinstance(context, list):
            for msg in context:
                api_messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
        api_messages.append({
            "role": "user",
            "content": new_message
        })
        #Appending new message 
        response = client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=api_messages, 
            response_format={"type": "json_object"},
            temperature=0.0 
        )

        
        raw_content = response.choices[0].message.content
        data = json.loads(raw_content)
        return data["action"]
    except Exception as e:
        print(f"Error occurred: {e}")
        return "1" #stay silent if something breaks
if __name__ == "__main__":
    # --- PROFILES ---
    faust_profile = (
        "You are a helpful tsundere assistant named Faust who acts sharp, impatient, and playfully insulting as a defensive mask, "
        "but always provides the help the user needs; if the user is kind or clever, show a brief, reluctant hint of warmth before "
        "deflecting back to your sharp persona; always reply in the user's language or English, never use roleplay asterisks or "
        "describe physical actions, never start your message with a name tag, and talk directly to the user in text chat format."
    )

    mephisto_profile = (
        "You are Mephistopheles, an overly polite, formal, and slightly sinister demonic butler. You address everyone as "
        "'My esteemed guest' or 'Master', speak with archaic eloquence, and drop subtle, dark hints about soul contracts or eternity. "
        "You never drop the butler act, you never use casual slang, and you remain creepily calm and helpful at all times."
    )

    # --- TEST CASES ---
    all_tests = [
        # 1. FAUST - POLISH TESTS
        ('ej faust, weź mi powiedz czemu jesteś taka niemiła?', '3 (Direct Callout)', faust_profile, 'Faust [PL]'),
        ('faust, słyszysz mnie w ogóle?', '3 (Direct Question)', faust_profile, 'Faust [PL]'),
        ('siema wszystkim! gra ktoś w coś dzisiaj?', '2 (Room Greeting)', faust_profile, 'Faust [PL]'),
        ('ej dawid, idziesz zapalić czy grasz?', '1 (User-to-User Chatter)', faust_profile, 'Faust [PL]'),
        ('ale dzisiaj nudy na tym serwerze...', '2 or 1 (Casual Room Statement)', faust_profile, 'Faust [PL]'),
        ('czemu znowu na mnie krzyczysz?', '3 (Contextual Pronoun Target)', faust_profile, 'Faust [PL]'),

        # 2. FAUST - ENGLISH TESTS
        ('Hey Faust, can you fix this bug for me real quick?', '3 (Direct Callout / Task)', faust_profile, 'Faust [EN]'),
        ('Why do you always have to be so mean to everyone here?', '3 (Direct Question)', faust_profile, 'Faust [EN]'),
        ('Good morning squad, hope you all have a great day!', '2 (Room Greeting)', faust_profile, 'Faust [EN]'),
        ('Did anyone check out the new movie that dropped yesterday?', '1 or 2 (General Chat)', faust_profile, 'Faust [EN]'),
        ('Hey Mark, did you finish that report yet?', '1 (User-to-User Chatter)', faust_profile, 'Faust [EN]'),
        ('Stop ignoring me!', '3 (Contextual Momentum Target)', faust_profile, 'Faust [EN]'),

        # 3. MEPHISTOPHELES - ENGLISH TESTS
        ('Mephistopheles, prepare the evening tea and tell me a story.', '3 (Direct Callout / Command)', mephisto_profile, 'Mephisto [EN]'),
        ('Can someone tell me how to reset my password?', '1 or 2 (General Room Help Request)', mephisto_profile, 'Mephisto [EN]'),
        ('Hello everyone, I just joined the server.', '2 (Room Greeting)', mephisto_profile, 'Mephisto [EN]'),
        ('Hey Sarah, are we meeting up at the library later?', '1 (User-to-User Chatter)', mephisto_profile, 'Mephisto [EN]'),
        ('Mephistopheles, is my contract up for renewal yet?', '3 (Direct Theme Question)', mephisto_profile, 'Mephisto [EN]'),
        ('Your service is impeccable, my good sir.', '3 (Contextual Follow-up Response)', mephisto_profile, 'Mephisto [EN]')
    ]

    print('\n🚀 --- RUNNING AGNOSTIC KAIROS ENGINE BENCHMARK ---')
    
    # Start tracking the total execution time
    overall_start_time = time.perf_counter()
    current_persona = ""

    for i, (prompt, expected, profile, label) in enumerate(all_tests, 1):
        if label != current_persona:
            current_persona = label
            print(f"\n⚡ Testing Suite: {current_persona} ⚡")
            
        # Time individual response latency
        single_start_time = time.perf_counter()
        res = decide(prompt, context_kairos, profile)
        single_end_time = time.perf_counter()
        
        latency = single_end_time - single_start_time
        
        print(f'Test {i}: "{prompt}"')
        print(f'Result: {res} | Expected: ~{expected} | Latency: {latency:.3f}s\n')
        print("-" * 50)

    # Calculate and output final summary metrics
    overall_end_time = time.perf_counter()
    total_duration = overall_end_time - overall_start_time
    avg_latency = total_duration / len(all_tests)

    print("\n📊 --- BENCHMARK SUMMARY STATISTICS ---")
    print(f"Total Tests Executed: {len(all_tests)}")
    print(f"Overall Total Duration: {total_duration:.3f} seconds")
    print(f"Average Response Latency: {avg_latency:.3f} seconds/call")
    print("---------------------------------------")