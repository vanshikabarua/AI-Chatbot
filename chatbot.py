import os
import re
import aiohttp
import discord
import google.generativeai as genai
from discord.ext import commands
from dotenv import load_dotenv
import time
import random


# slow feature
import asyncio



message_history = {}
load_dotenv()

GOOGLE_AI_KEY = "GOOGLE_GEMINI_API_KEY"
DISCORD_BOT_TOKEN = "DISCORD_BOT_TOKEN"
MAX_HISTORY = 1000

# Initial prompt for the chatbot
INITIAL_PROMPT = (
    "You're Veronica, a bot built by Vanshika"
    "You're helpful"
                 )

# Initialize the generative AI model
genai.configure(api_key=GOOGLE_AI_KEY)
text_generation_config = {
    "temperature": 0.9,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 512,
}
text_model = genai.GenerativeModel(
    model_name="gemini-pro", generation_config=text_generation_config)

# Initialize the Discord bot with appropriate intents
intents = discord.Intents.default()
intents.messages = True  # Enable message content intents
intents.guild_messages = True  # Enable guild message intents
intents.dm_messages = True  # Enable direct message intents

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print("----------------------------------------")
    print(f'Gemini Bot Logged in as {bot.user}')
    print("----------------------------------------")


@bot.event
async def on_message(message):
    if message.author == bot.user or message.mention_everyone:
        return

    if bot.user.mentioned_in(message) or isinstance(message.channel,
                                                    discord.DMChannel):
        cleaned_text = clean_discord_message(message.content)

        async with message.channel.typing():
            if message.attachments:
                print("New Image Message FROM:" + str(message.author.id) +
                      ": " + cleaned_text)
                for attachment in message.attachments:
                    if any(attachment.filename.lower().endswith(ext)
                           for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                        await message.add_reaction('🎨')
                        async with aiohttp.ClientSession() as session:
                            async with session.get(
                                    attachment.url) as resp:
                                if resp.status != 200:
                                    await message.channel.send(
                                        'Unable to download the image.')
                                    return
                                image_data = await resp.read()
                                response_text = await generate_response_with_image_and_text(
                                    image_data, cleaned_text)
                                await split_and_send_messages(message,
                                                              response_text,
                                                              1700)
                                return
            else:
                print("New Message FROM:" + str(message.author.id) +
                      ": " + cleaned_text)
                if "RESET" in cleaned_text:
                    if message.author.id in message_history:
                        del message_history[message.author.id]
                    await message.channel.send(
                        "🤖 History Reset for user: " +
                        str(message.author.name))
                    return
                await message.add_reaction('💬')

                if cleaned_text.lower() == "sure":  # User confirmation
                    await message.channel.send("Sure! Let's chat.")
                    return

                if (MAX_HISTORY == 0):
                    response_text = await generate_response_with_text(
                        cleaned_text)
                    await split_and_send_messages(message, response_text,
                                                  1700)
                    return

                update_message_history(message.author.id, cleaned_text)
                response_text = await generate_response_with_text(
                    get_formatted_message_history(message.author.id))
                update_message_history(message.author.id, response_text)
                await split_and_send_messages(message, response_text, 1700)


async def generate_response_with_text(message_text):
    # Prepend the initial prompt to the user's message
    prompt_text = f"{INITIAL_PROMPT}\n\n{message_text}"
    response = text_model.generate_content([prompt_text])
    if (response._error):
        return "❌" + str(response._error)
    return response.text


async def generate_response_with_image_and_text(image_data, text):
    image_parts = [{"mime_type": "image/jpeg", "data": image_data}]
    prompt_parts = [
        image_parts[0], f"\n{text if text else 'What is this a picture of?'}"
    ]
    response = image_model.generate_content(prompt_parts)
    if (response._error):
        return "❌" + str(response._error)
    return response.text


def update_message_history(user_id, text):
    if user_id in message_history:
        message_history[user_id].append(text)
        if len(message_history[user_id]) > MAX_HISTORY:
            message_history[user_id].pop(0)
    else:
        message_history[user_id] = [text]


def get_formatted_message_history(user_id):
    if user_id in message_history:
        return '\n\n'.join(message_history[user_id])
    else:
        return "No messages found for this user."


async def split_and_send_messages(message_system, text, max_length):
    messages = []
    for i in range(0, len(text), max_length):
        sub_message = text[i:i + max_length]
        messages.append(sub_message)
    for string in messages:
        await message_system.channel.send(string)

#     #slow feature
# async def split_and_send_messages(message_system, text, max_length, delay=1):
#     messages = []
#     for i in range(0, len(text), max_length):
#         sub_message = text[i:i + max_length]
#         messages.append(sub_message)

#     for string in messages:
#         await message_system.channel.send(string)
#         await asyncio.sleep(delay)  # Add a delay between messages


def clean_discord_message(input_string):
    bracket_pattern = re.compile(r'<[^>]+>')
    cleaned_content = bracket_pattern.sub('', input_string)
    return cleaned_content


bot.run(DISCORD_BOT_TOKEN)
