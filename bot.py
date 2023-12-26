import discord
import google.generativeai as genai
from discord.ext import commands
import aiohttp
import re
import dotenv
import os

dotenv.load_dotenv('.env.development')
dotenv.load_dotenv('.env')

GOOGLE_AI_KEY = os.getenv('GOOGLE_AI_KEY')
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

message_history = {}

#---------------------------------------------AI Configuration-------------------------------------------------

# Configure the generative AI model
genai.configure(api_key=GOOGLE_AI_KEY)
text_generation_config = {
	"temperature": 0.9,
	"top_p": 1,
	"top_k": 1,
	"max_output_tokens": 512,
}
image_generation_config = {
	"temperature": 0.4,
	"top_p": 1,
	"top_k": 32,
	"max_output_tokens": 512,
}
safety_settings = [
	{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
	{"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
	{"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
	{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
]
text_model = genai.GenerativeModel(model_name="gemini-pro", generation_config=text_generation_config, safety_settings=safety_settings)
image_model = genai.GenerativeModel(model_name="gemini-pro-vision", generation_config=image_generation_config, safety_settings=safety_settings)

bot_template = [
	
]

#---------------------------------------------Discord Code-------------------------------------------------
# Initialize Discord bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix=[], intents=intents,help_command=None,activity=discord.Game('with your feelings'))

#On Message Function
@bot.event
async def on_message(message:discord.Message):
	# Ignore messages sent by the bot
	if message.author == bot.user:
		return
	# Check if the bot is mentioned or the message is a DM
	if not (bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel)):
		return
	#Start Typing to seem like something happened

	async with message.channel.typing():
		# Check for image attachments
		if message.attachments:
			print("New Image Message FROM:" + str(message.author.id) + ": " + message.content)
			#Currently no chat history for images
			for attachment in message.attachments:
				#these are the only image extentions it currently accepts
				if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
					await message.add_reaction('🎨')
					
					async with aiohttp.ClientSession() as session:
						async with session.get(attachment.url) as resp:
							if resp.status != 200:
								await message.channel.send('Unable to download the image.')
								return
							image_data = await resp.read()
							response_text = await generate_response_with_image_and_text(image_data, message.content)
							#Split the Message so discord does not get upset
							await split_and_send_messages(message, response_text, 1700)
							return
		#Not an Image do text response
		else:
			print("New Message FROM:" + str(message.author.id) + ": " + message.content)
			#Check if history is disabled just send response
			response_text = await generate_response_with_text(message.channel.id,message.content)
			#Split the Message so discord does not get upset
			await split_and_send_messages(message, response_text, 1700)
			return
	   
#---------------------------------------------AI Generation History-------------------------------------------------		   

async def generate_response_with_text(channel_id,message_text):
	cleaned_text = clean_discord_message(message_text)
	if not (channel_id in message_history):
		message_history[channel_id] = text_model.start_chat(history=bot_template)
	response = message_history[channel_id].send_message(cleaned_text)
	return response.text

async def generate_response_with_image_and_text(image_data, text):
	image_parts = [{"mime_type": "image/jpeg", "data": image_data}]
	prompt_parts = [image_parts[0], f"\n{text if text else 'What is this a picture of?'}"]
	response = image_model.generate_content(prompt_parts)
	if(response._error):
		return "❌" +  str(response._error)
	return response.text

@bot.tree.command(name='forget',description='Forget message history')
async def forget(interaction:discord.Interaction):
	try:
		message_history.pop(interaction.channel_id)
	except Exception as e:
		pass
	await interaction.response.send_message("Message history for channel erased.")

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

def clean_discord_message(input_string):
	# Create a regular expression pattern to match text between < and >
	bracket_pattern = re.compile(r'<[^>]+>')
	# Replace text between brackets with an empty string
	cleaned_content = bracket_pattern.sub('', input_string)
	return cleaned_content  




#---------------------------------------------Run Bot-------------------------------------------------
@bot.event
async def on_ready():
	await bot.tree.sync()
	print("----------------------------------------")
	print(f'Gemini Bot Logged in as {bot.user}')
	print("----------------------------------------")
bot.run(DISCORD_BOT_TOKEN)