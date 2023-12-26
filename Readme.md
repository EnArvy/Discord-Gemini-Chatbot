# Discord Bot to interact with Gemini API as ChatBot

Inspiration - https://github.com/Echoshard/Gemini_Discordbot

This bot acts as a Chatbot. It uses Google's Gemini API which is free for upto 60 calls/min as of Dec 2023.

The bot can be talked to by mentioning it or DMing it.

Each channel/thread has it's own context and can be erased by using /forget.

Due to API restrictions, the bot cannot remember image interactions.

Current version erases anything between < and > so any mentions or emojis

## Requirements

Get a Google Gemini api key from ai.google.dev

Make a discord bot at discord.com/developers/applications

## Running

Install all dependencies as specified in requirements.txt

Create a .env file and add GOOGLE_AI_KEY and DISCORD_BOT_TOKEN in as specified in .env.development file

Run as `python bot.py`

Optionally, you can add custom initial conversation for every chat by editing the bot_template variable as follows:

```
bot_template = [
	{'role':'user','parts': ["Hi!"]},
	{'role':'model','parts': ["Hello! I am a Discord bot!"]},
	{'role':'user','parts': ["Please give short and concise answers!"]},
	{'role':'model','parts': ["I will try my best!"]},
]
```