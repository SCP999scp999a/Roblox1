import os
import discord
from discord.ext import commands
import requests
import asyncio
from datetime import datetime

TOKEN = os.getenv("TOKEN")
ALLOWED_CHANNEL_ID = 1467416456286179470

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} เชื่อมต่อแล้ว! ใช้ !c <ชื่อRoblox>')
    print(f'📢 ทำงานเฉพาะช่อง ID: {ALLOWED_CHANNEL_ID}')

def format_date(created):
    months_th = ['มกราคม', 'กุมภาพันธ์', 'กุมภาพันธ์', 'เมษายน', 'พฤษภาคม', 'มิถุนายน',
                 'กรกฎาคม', 'สิงหาคม', 'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม']
    try:
        dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
        day = dt.day
        month = months_th[dt.month-1]
        year = dt.year + 543
        return f"{day} {month} {year}"
    except:
        return 'ไม่ทราบ'

async def get_profile_image(user_id):
    thumbnail_url = "https://thumbnails.roblox.com/v1/users/avatar-headshot"
    params = {
        'userIds': user_id,
        'size': '420x420',
        'format': 'Png',
        'isCircular': 'false'
    }
    for attempt in range(5):
        try:
            resp = requests.get(thumbnail_url, params=params)
            data = resp.json()
            if data.get('data') and data['data'][0].get('imageUrl'):
                return data['data'][0]['imageUrl']
            await asyncio.sleep(0.5)
        except:
            await asyncio.sleep(0.5)
    return f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png"

async def get_asset_price(asset_id):
    try:
        catalog_url = f'https://catalog.roblox.com/v1/catalog/items/{asset_id}'
        resp = requests.get(catalog_url)
        data = resp.json()
        price = data.get('priceInRobux') or 0
        if data.get('lowestResalePrice'):
            price = data.get('lowestResalePrice')
        return price
    except:
        return 0

async def get_avatar_cost(user_id):
    try:
        avatar_url = f'https://avatar.roblox.com/v1/users/{user_id}/avatar'
        resp = requests.get(avatar_url)
        avatar_data = resp.json()
        assets = avatar_data.get('data', [])
        total_cost = 0
        asset_list = []

        for asset in assets[:8]:
            asset_id = asset.get('id')
            asset_name = asset.get('name', 'ไม่ทราบชื่อ')
            asset_type = asset.get('assetType', {})
            asset_type_name = asset_type.get('name', 'อื่นๆ')
            price = await get_asset_price(asset_id)
            total_cost += price if price and price > 0 else 0
            asset_list.append(f"**{asset_name[:30]}** ({asset_type_name})")

        if not asset_list:
            return "ไม่มีข้อมูลแต่งตัว", 0

        return '\n'.join(asset_list), total_cost
    except:
        return "ไม่สามารถดึงแต่งตัวได้", 0

async def get_robux(user_id):
    try:
        currency_url = f'https://economy.roblox.com/v1/users/{user_id}/currency'
        resp = requests.get(currency_url)
        data = resp.json()
        robux = data.get('robux', 0)

        premium_url = f'https://premiumfeatures.roblox.com/v1/users/{user_id}/validate-membership'
        premium_resp = requests.get(premium_url)
        premium_data = premium_resp.json()
        is_premium = premium_data.get('isPremium', False)

        return f"`{robux:,}` {'👑 Premium' if is_premium else ''}"
    except:
        return "`0` Robux"

async def check_channel(ctx):
    if ctx.channel.id != ALLOWED_CHANNEL_ID:
        embed = discord.Embed(
            title="❌ คำสั่งนี้ใช้ได้เฉพาะช่องที่กำหนด!",
            description=f"ใช้คำสั่งในช่อง <#{ALLOWED_CHANNEL_ID}> เท่านั้น\n`!c <ชื่อRoblox>`",
            color=0xff0000
        )
        await ctx.send(embed=embed, delete_after=10)
        return False
    return True

@bot.command(name='c')
async def roblox_lookup(ctx, *, username):
    if not await check_channel(ctx):
        return

    user_mention = ctx.author.mention
    await ctx.send(f"🔍 {user_mention} กำลังค้นหาโปรไฟล์ Roblox...")

    try:
        users_url = 'https://users.roblox.com/v1/usernames/users'
        payload = {'usernames': [username], 'excludeBannedUsers': True}
        users_resp = requests.post(users_url, json=payload)
        users_data = users_resp.json()

        if not users_data.get('data'):
            await ctx.send(f'❌ ไม่พบผู้ใช้: `{username}`')
            return

        user = users_data['data'][0]
        user_id = user['id']
        display_name = user.get('displayName', username)

        profile_data = requests.get(f'https://users.roblox.com/v1/users/{user_id}').json()
        friends_data = requests.get(f'https://friends.roblox.com/v1/users/{user_id}/friends/count').json()
        followers_data = requests.get(f'https://friends.roblox.com/v1/users/{user_id}/followers/count').json()

        robux_text = await get_robux(user_id)
        avatar_info, avatar_cost = await get_avatar_cost(user_id)

        profile_image_url = await get_profile_image(user_id)

        embed = discord.Embed(title=f"{display_name}", color=0x00ff00)
        embed.set_thumbnail(url=profile_image_url)

        embed.add_field(name="👤 Username", value=f"`{username}`")
        embed.add_field(name="🆔 ID", value=f"`{user_id}`")
        embed.add_field(name="📅 Created", value=format_date(profile_data.get('created')))

        embed.add_field(name="👥 Friends", value=f"`{friends_data.get('count',0):,}`")
        embed.add_field(name="❤️ Followers", value=f"`{followers_data.get('count',0):,}`")
        embed.add_field(name="💰 Robux", value=robux_text)

        embed.add_field(name="💎 Outfit Cost", value=f"`{avatar_cost:,}` Robux", inline=False)
        embed.add_field(name="👗 Outfit Items", value=avatar_info[:1024], inline=False)

        embed.add_field(name="🔗 Profile", value=f"https://www.roblox.com/users/{user_id}/profile", inline=False)

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f'❌ Error: `{str(e)[:500]}`')

bot.run(TOKEN)
