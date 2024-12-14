# Discord Bot to interact with Gemini API as ChatBot

## Preview

![Preview](https://i.imgur.com/j3CU5EF.png)


Inspiration - https://github.com/Echoshard/Gemini_Discordbot

This bot acts as a Chatbot. It uses Google's Gemini API which is free for upto 60 calls/min as of Jan 2023.

### Supports images, audio, documents and Gemini 1.5 completely!

## Usage

The bot can be talked to by mentioning it or DMing it.

Each channel/thread has it's own context and can be erased by using /forget.

Additionally, a persona can be specified while making it forget history.

Due to API restrictions, the bot cannot remember image interactions.

## Requirements

Get a Google Gemini api key from ai.google.dev

Make a discord bot at discord.com/developers/applications

## Running

Clone repository

Install all dependencies as specified in requirements.txt

Create a .env file and add GOOGLE_AI_KEY and DISCORD_BOT_TOKEN in as specified in .env.development file

Run as `python bot.py`

## Customization

Optionally, you can configure the bot as follows using `config.py`:

Add custom initial conversation for every chat by editing the bot_template variable as follows:

```
bot_template = [
	{'role':'user','parts': ["Hi!"]},
	{'role':'model','parts': ["Hello! I am a Discord bot!"]},
	{'role':'user','parts': ["Please give short and concise answers!"]},
	{'role':'model','parts': ["I will try my best!"]},
]
```

Change content safety settings as follows:
```
safety_settings = [
	{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
	{"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
	{"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
	{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
]
```

Change AI generation parameters using the variables text_generation_config and image_generation_config

## Misc

Error logs are stored in the errors.log file created at runtime.

Chat data is stored between bot runs using shelve.
