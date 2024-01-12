import os
import openai
import discord 
from discord.ext import commands
from discord import app_commands
import asyncio 
from dotenv import load_dotenv
import sys
import time
import subprocess
import random
import json
from datetime import datetime, timedelta
from pymongo import MongoClient
import cv2
from sklearn.cluster import KMeans
from PIL import Image
from io import BytesIO
import numpy as np
import requests
import asyncio
import paytmchecksum
from discord.ext.commands import CommandOnCooldown, MissingRequiredArgument, MissingPermissions

load_dotenv()
discord_token = os.getenv("TOKEN")

client = MongoClient("mongodb://localhost:27017")

db = client["discordbot_test"]
userdatas = db["userdata"]
misc_collection = db["misc"]

intent = discord.Intents.default()
intent.members = True
intent.message_content = True

client = commands.Bot(command_prefix="!", intents=intent,case_insensitive=False)

@client.event
async def on_ready():
  print(f"Logged in as {client.user}")
  await client.tree.sync()

def add_user_to_db(ctx):
    #Add user to database
    user_id = ctx.author.id
    username = ctx.author.name
    profile_picture_url = str(ctx.author.avatar.url) if ctx.author.avatar else None
    join_date = ctx.author.created_at.strftime("%Y-%m-%d %H:%M:%S")

    existing_user = userdatas.find_one({"user_id": user_id})

    if not existing_user:
        user_data = {
            "user_id": user_id,
            "username": username,
            "profile_picture": profile_picture_url,
            "join_date": join_date
        }
        userdatas.insert_one(user_data)


@client.hybrid_command(name='cointoss')
async def cointoss(ctx):
    add_user_to_db(ctx)
    coin = ["heads", "tails"]
    result = random.choice(coin)
    await ctx.send(f"The result of the coin toss is {result}!")


@client.hybrid_command(name='userinfo')
async def userinfo(ctx, member: discord.Member = None):
    add_user_to_db(ctx)
    
    if member is None:
        member = ctx.author

    user_id = f"`{member.id}`"
    username = f"`{member.name}`"
    join_discord = member.created_at.strftime("`%Y-%m-%d %H:%M:%S`")
    join_server = member.joined_at.strftime("`%Y-%m-%d %H:%M:%S`") if member.joined_at else "Not available"
    profile_picture_url = str(member.avatar.url) if member.avatar else None

    roles = [f"`{role.name}`" for role in reversed(member.roles) if role.name != '@everyone']

    embed = discord.Embed(title=f"**User Information**", color=discord.Color.blue())
    embed.add_field(name="User ID", value=user_id, inline=False)
    embed.add_field(name="Username", value=username, inline=False)
    embed.add_field(name="Joined Discord", value=join_discord, inline=False)
    embed.add_field(name="Joined Server", value=join_server, inline=False)
    embed.add_field(name="Roles", value=", ".join(roles) if roles else "None", inline=False)
    embed.set_thumbnail(url=profile_picture_url)

    await ctx.send(embed=embed)


@client.hybrid_command(name='avatar')
@commands.cooldown(1, 3, commands.BucketType.user)
async def avatar(ctx, member: discord.Member = None):
    add_user_to_db(ctx)
    if member is None:
        member = ctx.author

    avatar_url = str(member.avatar.url) if member.avatar else None
    response = requests.get(avatar_url)
    image = Image.open(BytesIO(response.content))
    temp_image_path = 'temp_avatar.png'
    image.save(temp_image_path)

    image_np = cv2.imread(temp_image_path)
    pixels = image_np.reshape((-1, 3))
    sample_size = 1000
    if len(pixels) > sample_size:
        pixels = pixels[np.random.choice(len(pixels), size=sample_size, replace=False)]
    pixels = np.float32(pixels)

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
    _, labels, centers = cv2.kmeans(pixels, 1, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    dominant_color = np.uint8(centers)

    hex_color = "#{:02x}{:02x}{:02x}".format(dominant_color[0, 2], dominant_color[0, 1], dominant_color[0, 0])

    os.remove(temp_image_path)

    embed = discord.Embed(title=f"{member.name}'s avatar", color=discord.Color(int(hex_color[1:], 16)))
    embed.set_image(url=avatar_url)

    await ctx.send(embed=embed)


@client.hybrid_command(name='ban')
@commands.has_permissions(ban_members=True)
@commands.cooldown(1, 3, commands.BucketType.user)
async def ban(ctx, member: discord.Member = None):
    if member is None:
        await ctx.send("Mention the user you want to ban")
    await member.ban()
    await ctx.send(f'{member.mention} has been banned.')

@ban.error
async def ban_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command.")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send("Command on cooldown, try again in few seconds")


@client.hybrid_command(name='kick')
@commands.has_permissions(kick_members=True)
@commands.cooldown(1, 3, commands.BucketType.user)
async def kick(ctx, member: discord.Member = None):
    if member is None:
        await ctx.send("Mention the user you want to ban")
    await member.kick()
    await ctx.send(f'{member.mention} has been kicked.')

@kick.error
async def kick_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command.")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send("Command on cooldown, try again in few seconds")




client.run(discord_token)