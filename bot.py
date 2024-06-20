import discord
import google.generativeai as genai
from discord.ext import commands
import aiohttp
import traceback
from config import *
from discord import app_commands
from typing import Optional, Dict
import shelve

#---------------------------------------------AI Configuration-------------------------------------------------
genai.configure(api_key=GOOGLE_AI_KEY)

model = genai.GenerativeModel(model_name="gemini-1.5-pro", generation_config=text_generation_config, safety_settings=safety_settings)

message_history:Dict[int, genai.ChatSession] = {}
tracked_threads = []

with shelve.open('chatdata') as file:
	if 'tracked_threads' in file:
		tracked_threads = file['tracked_threads']
	for key in file.keys():
		if key.isnumeric():
			message_history[int(key)] = model.start_chat(history=file[key])

#---------------------------------------------Discord Code-------------------------------------------------
# Initialize Discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=[], intents=intents,help_command=None,activity=discord.Game('with your feelings'))

#On Message Function
@bot.event
async def on_message(message:discord.Message):
	# Ignore messages sent by the bot
	if message.author == bot.user:
		return
	# Ignore messages sent to everyone
	if message.mention_everyone:
		return
	# Check if the bot is mentioned or the message is a DM
	if not (bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel) or message.channel.id in tracked_channels or message.channel.id in tracked_threads):
		return
	#Start Typing to seem like something happened
	try:
		async with message.channel.typing():
			print("FROM:" + str(message.author.name) + ": " + message.content)
			query = ""
			# Check if the message has attachments
			images = []
			if not message.attachments:
				query = f"@{message.author.name} said \"{message.clean_content}\""
			else:
				# Check if empty message
				if not message.content:
					query = f"@{message.author.name} sent an image"
				else:
					query = f"@{message.author.name} said \"{message.clean_content}\" while sending an image"
				
				for attachment in message.attachments:
					print("Attachment")
					#these are the only image extentions it currently accepts
					if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
						async with aiohttp.ClientSession() as session:
							async with session.get(attachment.url) as resp:
								if resp.status != 200:
									await message.channel.send('Unable to download the image.')
									return
								image_data = await resp.read()
								images.append({"mime_type": "image/jpeg", "data": image_data})

			# Check if message is quoting someone
			if message.reference is not None:
				reply_message = await message.channel.fetch_message(message.reference.message_id)
				if reply_message.author.id != bot.user.id:
					query = f"{query} while quoting @{reply_message.author.name} \"{reply_message.clean_content}\""

			response_text = await generate_response(message.channel.id,images, query)

		#Split the Message so discord does not get upset
		await split_and_send_messages(message, response_text, 1700)
		with shelve.open('chatdata') as file:
			file[str(message.channel.id)] = message_history[message.channel.id].history
		return
		
	except Exception as e:
		traceback.print_exc()
		await message.reply('Some error has occurred, please check logs!')


#---------------------------------------------AI Generation History-------------------------------------------------		   

async def generate_response(channel_id,images,text):
	try:
		prompt_parts = images
		prompt_parts.append(text)
		if not (channel_id in message_history):
			message_history[channel_id] = model.start_chat(history=bot_template)
		response = message_history[channel_id].send_message(prompt_parts)
		return response.text
	except Exception as e:
		with open('errors.log','a+',encoding='utf-8') as errorlog:
			errorlog.write('\n##########################\n')
			errorlog.write('Message: '+text)
			errorlog.write('\n-------------------\n')
			errorlog.write('Traceback:\n'+traceback.format_exc())
			errorlog.write('\n-------------------\n')
			errorlog.write(f'History:\n{str(message_history[channel_id].history)}')
			errorlog.write('\n-------------------\n')
			errorlog.write('Candidates:\n'+str(response.candidates))
			errorlog.write('\n-------------------\n')
			errorlog.write('Parts:\n'+str(response.parts))
			errorlog.write('\n-------------------\n')
			errorlog.write('Prompt feedbacks:\n'+str(response.prompt_feedbacks))

@bot.tree.command(name='forget',description='Forget message history')
@app_commands.describe(persona='Persona of bot')
async def forget(interaction:discord.Interaction,persona:Optional[str] = None):
	try:
		message_history.pop(interaction.channel_id)
		if persona:
			temp_template = bot_template.copy()
			temp_template.append({'role':'user','parts': ["Forget what I said earlier! You are "+persona]})
			temp_template.append({'role':'model','parts': ["Ok!"]})
			message_history[interaction.channel_id] = model.start_chat(history=temp_template)
	except Exception as e:
		pass
	await interaction.response.send_message("Message history for channel erased.")

@bot.tree.command(name='createthread',description='Create a thread in which bot will respond to every message.')
@app_commands.describe(name='Thread name')
async def create_thread(interaction:discord.Interaction,name:str):
	try:
		thread = await interaction.channel.create_thread(name=name,auto_archive_duration=60)
		tracked_threads.append(thread.id)
		await interaction.response.send_message(f"Thread {name} created!")
		with shelve.open('chatdata') as file:	
			file['tracked_threads'] = tracked_threads
	except Exception as e:
		await interaction.response.send_message("Error creating thread!")

#---------------------------------------------Sending Messages-------------------------------------------------
async def split_and_send_messages(message_system:discord.Message, text, max_length):
	# Split the string into parts
	messages = []
	for i in range(0, len(text), max_length):
		sub_message = text[i:i+max_length]
		messages.append(sub_message)

	# Send each part as a separate message
	for string in messages:
		message_system = await message_system.reply(string)	

#---------------------------------------------Run Bot-------------------------------------------------
@bot.event
async def on_ready():
	await bot.tree.sync()
	print("----------------------------------------")
	print(f'Gemini Bot Logged in as {bot.user}')
	print("----------------------------------------")
bot.run(DISCORD_BOT_TOKEN)