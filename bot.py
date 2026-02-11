import os
import discord
from discord.ext import commands
import aiohttp
import asyncio
from datetime import datetime

TOKEN = os.environ.get("TOKEN")
ALLOWED_CHANNEL_ID = 1467416456286179470

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} เชื่อมต่อแล้ว! ใช้ !c <ชื่อRoblox>')
    print(f'📢 ทำงานเฉพาะช่อง ID: {ALLOWED_CHANNEL_ID}')

def format_date(created):
    months_th = ['มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน', 'พฤษภาคม', 'มิถุนายน',
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
    thumbnail_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot"
    params = {
        'userIds': str(user_id),
        'size': '420x420',
        'format': 'Png',
        'isCircular': 'false'
    }
    async with aiohttp.ClientSession() as session:
        for attempt in range(5):
            try:
                async with session.get(thumbnail_url, params=params) as resp:
                    data = await resp.json()
                    if data.get('data') and len(data['data']) > 0 and data['data'][0].get('imageUrl'):
                        return data['data'][0]['imageUrl']
                await asyncio.sleep(0.5)
            except:
                await asyncio.sleep(0.5)
    return f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png"

async def get_avatar_cost(user_id):
    """ดึงแต่งตัวหน้าโปรไฟล์ + คำนวณราคา Robux"""
    try:
        avatar_url = f'https://avatar.roblox.com/v1/users/{user_id}/avatar'
        async with aiohttp.ClientSession() as session:
            async with session.get(avatar_url) as resp:
                avatar_data = await resp.json()

        assets = avatar_data.get('assets', [])
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

    except Exception as e:
        print(f"Error get_avatar_cost: {e}")
        return "ไม่สามารถดึงแต่งตัวได้", 0

async def get_asset_price(asset_id):
    """ดึงราคา asset เดี่ยว"""
    try:
        catalog_url = f'https://economy.roblox.com/v2/assets/{asset_id}/details'
        async with aiohttp.ClientSession() as session:
            async with session.get(catalog_url) as resp:
                data = await resp.json()
                
                price = data.get('PriceInRobux') or 0
                
                if data.get('LowestResalePrice'):
                    price = data.get('LowestResalePrice')
                
                return price
    except Exception as e:
        print(f"Error get_asset_price: {e}")
        return 0

async def get_robux(user_id):
    """ดึง Robux + Premium"""
    try:
        async with aiohttp.ClientSession() as session:
            # ดึง Robux (อาจไม่ได้ผลถ้าไม่มี authentication)
            try:
                currency_url = f'https://economy.roblox.com/v1/users/{user_id}/currency'
                async with session.get(currency_url) as resp:
                    data = await resp.json()
                    robux = data.get('robux', 0)
            except:
                robux = 0

            # ตรวจสอบ Premium
            try:
                premium_url = f'https://premiumfeatures.roblox.com/v1/users/{user_id}/validate-membership'
                async with session.get(premium_url) as premium_resp:
                    premium_data = await premium_resp.json()
                    is_premium = premium_data.get('isPremium', False)
            except:
                is_premium = False

            if robux > 0:
                return f"`{robux:,}` {'👑 Premium' if is_premium else ''}"
            else:
                return f"ไม่สามารถดูได้ {'👑 Premium' if is_premium else ''}"
    except:
        return "ไม่สามารถดึงข้อมูล"

async def check_channel(ctx):
    if ctx.channel.id != ALLOWED_CHANNEL_ID:
        embed = discord.Embed(
            title="❌ คำสั่งนี้ใช้ได้เฉพาะช่องที่กำหนด!",
            description=f"**ใช้คำสั่งในช่อง** <#{ALLOWED_CHANNEL_ID}> เท่านั้น\n`!c <ชื่อRoblox>`",
            color=0xff0000
        )
        embed.set_footer(text="บอทของคุณนัด | discord.gg/room05280")
        await ctx.send(embed=embed, delete_after=10)
        return False
    return True

@bot.command(name='c')
async def roblox_lookup(ctx, *, username):
    if not await check_channel(ctx):
        return

    user_mention = ctx.author.mention
    await ctx.send(f"🔍 **{user_mention}** กำลังค้นหาโปรไฟล์ Roblox... ⏳")

    try:
        async with aiohttp.ClientSession() as session:
            # 1. หา User ID
            users_url = 'https://users.roblox.com/v1/usernames/users'
            payload = {'usernames': [username], 'excludeBannedUsers': True}
            async with session.post(users_url, json=payload) as resp:
                users_data = await resp.json()

            if not users_data.get('data'):
                await ctx.send(f'❌ **{user_mention}** ไม่พบผู้ใช้: `{username}`')
                return

            user = users_data['data'][0]
            user_id = user['id']
            display_name = user.get('displayName', username)

            # 2. ดึงข้อมูลพื้นฐาน
            async with session.get(f'https://users.roblox.com/v1/users/{user_id}') as resp:
                profile_data = await resp.json()
            
            async with session.get(f'https://friends.roblox.com/v1/users/{user_id}/friends/count') as resp:
                friends_data = await resp.json()
            
            async with session.get(f'https://friends.roblox.com/v1/users/{user_id}/followers/count') as resp:
                followers_data = await resp.json()

            # เรียก async functions
            robux_text = await get_robux(user_id)
            avatar_info, avatar_cost = await get_avatar_cost(user_id)

            description = profile_data.get('description', 'ไม่มีคำอธิบาย')
            created = profile_data.get('created')
            friends_count = friends_data.get('count', 0)
            followers_count = followers_data.get('count', 0)

            # 3. Groups + Status
            async with session.get(f'https://groups.roblox.com/v1/users/{user_id}/groups/roles') as resp:
                groups_data = await resp.json()
            
            async with session.post('https://presence.roblox.com/v1/presence/users', 
                                   json={'userIds': [user_id]}) as resp:
                presence_data = await resp.json()

            groups_list = [g['group']['name'] for g in groups_data.get('data', [])[:5]]

            status_text = "🔴 ออฟไลน์"
            if presence_data.get('userPresences'):
                presence = presence_data['userPresences'][0]
                presence_type = presence.get('userPresenceType', 0)
                game_instance_id = presence.get('gameInstanceId')
                place_id = presence.get('placeId')
                if game_instance_id and place_id:
                    status_text = f"🟡 เล่นเกม (Place: {place_id})"
                elif presence_type == 3:
                    status_text = "🔵 ใน Studio"
                elif presence_type == 1:
                    status_text = "🟢 ออนไลน์"

        # รูปโปรไฟล์
        profile_image_url = await get_profile_image(user_id)

        # Embed รูปใหญ่
        profile_embed = discord.Embed(title=f"🖼️ {display_name} - รูปโปรไฟล์")
        profile_embed.set_image(url=profile_image_url)
        await ctx.send(embed=profile_embed)

        # ✅ Embed หลัก
        embed = discord.Embed(title=f"✅ **{user_mention}** | 🔍 {display_name}", color=0x00ff00)
        embed.set_thumbnail(url=profile_image_url)

        # Row 1
        embed.add_field(name="👤 ชื่อผู้ใช้", value=f"`{username}`", inline=True)
        embed.add_field(name="🆔 ID", value=f"`{user_id}`", inline=True)
        embed.add_field(name="📅 สร้างบัญชี", value=format_date(created), inline=True)

        # Row 2
        embed.add_field(name="👥 เพื่อน", value=f"`{friends_count:,}`", inline=True)
        embed.add_field(name="❤️ ติดตาม", value=f"`{followers_count:,}`", inline=True)
        embed.add_field(name="💰 Robux", value=robux_text, inline=True)

        # Row 3
        embed.add_field(name="🟢 สถานะ", value=status_text, inline=True)

        # ราคาแต่งตัว
        embed.add_field(
            name="💎 ราคาแต่งตัว", 
            value=f"`{avatar_cost:,}` Robux", 
            inline=True
        )

        # แสดงรายการแต่งตัว
        embed.add_field(
            name="👗 แต่งตัวปัจจุบัน", 
            value=avatar_info[:1024] or 'ไม่มีข้อมูล', 
            inline=False
        )

        # ข้อมูลเพิ่มเติม
        embed.add_field(name="📝 คำอธิบาย", 
                       value=description[:1000] + '...' if len(description) > 1000 else description or 'ไม่มี', 
                       inline=False)

        groups_text = ', '.join(groups_list) if groups_list else 'ไม่มี'
        embed.add_field(name="🏛️ กลุ่ม", value=groups_text, inline=False)

        embed.add_field(name="🔗 โปรไฟล์", 
                       value=f"[👉 ดูที่นี่](https://www.roblox.com/users/{user_id}/profile)", 
                       inline=False)

        embed.set_footer(
            text="บอทของคุณนัด ไม่อนุญาตให้นำไปใช้ในเซิฟเวอร์ที่ไม่ได้รับอนุญาติ | discord.gg/room05280\n💎 คำนวณราคาแต่งตัวจาก Roblox Catalog API",
            icon_url="https://cdn.discordapp.com/embed/avatars/0.png"
        )

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f'❌ **{user_mention}** เกิดข้อผิดพลาด: `{str(e)[:1000]}`')
        print(f"Error detail: {e}")

bot.run(TOKEN)
