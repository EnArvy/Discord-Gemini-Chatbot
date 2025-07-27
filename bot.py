import discord
import google.generativeai as genai
from discord.ext import commands
import aiohttp
import traceback
from config import *
from discord import app_commands
from typing import Optional, Dict, List
import shelve

#---------------------------------------------AI Configuration-------------------------------------------------
genai.configure(api_key=GOOGLE_AI_KEY)

model = genai.GenerativeModel(model_name="gemini-2.5-flash", generation_config=text_generation_config, safety_settings=safety_settings)

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
async def on_message(message: discord.Message):
	# Ignore messages sent by the bot
	if message.author == bot.user:
		return
	# Ignore messages sent to everyone
	if message.mention_everyone:
		return
	# Check if the bot is mentioned or the message is a DM
	if not (bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel) or message.channel.id in tracked_channels or message.channel.id in tracked_threads):
		return
	# Start Typing to seem like something happened
	try:
		async with message.channel.typing():
			print("FROM:" + str(message.author.name) + ": " + message.content)
			query = ""
			attachments = []

			# Check if the message has attachments
			if not message.attachments:
				query = f"@{message.author.name} said \"{message.clean_content}\""
			else:
				# Check if empty message
				if not message.content:
					query = f"@{message.author.name} sent attachments:"
				else:
					query = f"@{message.author.name} said \"{message.clean_content}\" while sending attachments:"
				attachments = await get_attachment_data(message.attachments)
				if not attachments:
					await message.channel.send("An error occurred while processing your attachments.")
					return
				if len(attachments) == 0:
					await message.channel.send("Attachments are of unsupported file types.")
					return

			# Check if message is quoting someone
			if message.reference is not None:
				reply_message = await message.channel.fetch_message(message.reference.message_id)
				if reply_message.author.id != bot.user.id:
					query = f"{query} while quoting @{reply_message.author.name} \"{reply_message.clean_content}\""
				if reply_message.attachments:
					attachments += await get_attachment_data(reply_message.attachments)

			# Generate response using Gemini API
			response_text = await generate_response(message.channel.id, attachments, query)

			await split_and_send_messages(message, response_text, 1700)
			with shelve.open('chatdata') as file:
				file[str(message.channel.id)] = message_history[message.channel.id].history
	except Exception as e:
		print(f"Error: {e}")
		print(traceback.format_exc())
		if e.code == 50035:
			await message.channel.send("The message is too long for me to process.")
		else:
			await message.channel.send('An error occurred while processing your message.')


async def get_attachment_data(attachments:List[discord.Attachment]) -> List[Dict[str, bytes]]:
	result = []
	for attachment in attachments:
		async with aiohttp.ClientSession() as session:
			async with session.get(attachment.url) as resp:
				if resp.status != 200:
					return None
				attachment_data = await resp.read()
				mime_type = None
				if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpeg', '.heic', '.webp', '.heif']):
					mime_type = f"image/{attachment.filename.split('.')[-1]}"
				elif any(attachment.filename.lower().endswith(ext) for ext in ['.jpg']):
					mime_type = "image/jpeg"
				elif any(attachment.filename.lower().endswith(ext) for ext in ['.wav', '.mp3', '.aiff', '.aac', '.ogg', '.flac']):
					mime_type = f"audio/{attachment.filename.split('.')[-1]}"
				elif any(attachment.filename.lower().endswith(ext) for ext in ['.html', '.css', '.md', '.csv', '.xml', '.rtf']):
					mime_type = f"text/{attachment.filename.split('.')[-1]}"
				elif any(attachment.filename.lower().endswith(ext) for ext in ['.pdf']):
					mime_type = "application/pdf"
				elif any(attachment.filename.lower().endswith(ext) for ext in ['.js']):
					mime_type = "application/x-javascript"
				elif any(attachment.filename.lower().endswith(ext) for ext in ['.py']):
					mime_type = "application/x-python"
				if mime_type:
					result.append({"mime_type": mime_type, "data": attachment_data})
	return result

#---------------------------------------------AI Generation History-------------------------------------------------		   

async def generate_response(channel_id,attachments,text):
	try:
		prompt_parts = attachments
		prompt_parts.append(text)
		if not (channel_id in message_history):
			message_history[channel_id] = model.start_chat(history=bot_template)
		response = await message_history[channel_id].send_message_async(prompt_parts)
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