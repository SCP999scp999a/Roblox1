import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import asyncio
import time
import re
from collections import deque

import os

TOKEN = os.environ.get("TOKEN")
ADMIN_ID = 1226204034944339968

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

def is_valid_webhook(url):
    webhook_pattern = r'^https://discord\.com/api/webhooks/\d+/[\w-]+$'
    return re.match(webhook_pattern, url) is not None

class MainMenu(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🚀 ส่ง Webhook", style=discord.ButtonStyle.green, emoji="⚡")
    async def send_webhook_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(WebhookModal())

    @discord.ui.button(label="📞 ติดต่อแอดมิน", style=discord.ButtonStyle.blurple, emoji="👤")
    async def contact_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        # ดึงข้อมูลแอดมินแบบ full (รวม banner)
        try:
            admin = await interaction.client.fetch_user(ADMIN_ID)
        except Exception:
            admin = interaction.client.get_user(ADMIN_ID)

        embed = discord.Embed(
            title="",
            description=(
                f"## 👑 ข้อมูลแอดมิน\n"
                f"╔══════════════════════╗\n"
                f"**ชื่อ** ┃ {admin.name if admin else 'แอดมิน'}\n"
                f"**ไอดี** ┃ `{ADMIN_ID}`\n"
                f"╚══════════════════════╝\n\n"
                f"💬 กดปุ่มด้านล่างเพื่อเปิดโปรไฟล์และส่งข้อความหาแอดมินได้เลย!"
            ),
            color=0x5865F2  # Discord Blurple
        )

        # ใส่รูป GIF สวยๆ เป็น image หลัก
        embed.set_image(url="https://cdn.discordapp.com/attachments/1427659460679045303/1475165371383287940/standard.gif?ex=69a3be8f&is=69a26d0f&hm=f37ce17634010b09cba07f0c7b779ad4a5ed68504c2e943de2781c1cab0ededa")

        # ใส่รูปโปรไฟล์แอดมินเป็น thumbnail มุมขวา
        if admin and admin.avatar:
            embed.set_thumbnail(url=admin.display_avatar.with_size(256).url)

        embed.set_footer(
            text="คลิกปุ่มด้านล่าง → เปิดโปรไฟล์ Discord โดยตรง",
            icon_url=admin.display_avatar.url if admin else None
        )

        # View มีปุ่ม link ตรงไปโปรไฟล์ — Discord จะเด้งเปิดโปรไฟล์ทันที
        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="🔗 เปิดโปรไฟล์แอดมิน",
            style=discord.ButtonStyle.link,
            url=f"https://discord.com/users/{ADMIN_ID}",
            emoji="👤"
        ))
        view.add_item(discord.ui.Button(
            label="✉️ ส่งข้อความ",
            style=discord.ButtonStyle.link,
            url=f"https://discord.com/users/{ADMIN_ID}",
            emoji="💬"
        ))

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class WebhookModal(discord.ui.Modal, title="⚡ ตั้งค่าส่ง Webhook"):

    webhook_url = discord.ui.TextInput(
        label="🔗 ลิงก์ Webhook",
        placeholder="https://discord.com/api/webhooks/...",
        style=discord.TextStyle.short,
        required=True
    )
    message_words = discord.ui.TextInput(
        label="💬 ข้อความ (เว้นวรรคเพื่อแยกคำ)",
        placeholder="สวัสดี ทดสอบ บอท Discord",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )
    amount = discord.ui.TextInput(
        label="🔢 จำนวนครั้ง (สูงสุด 2000)",
        placeholder="1000",
        style=discord.TextStyle.short,
        required=True,
        max_length=4
    )
    speed_mode = discord.ui.TextInput(
        label="🎮 เลือกโหมดความเร็ว (1, 2, 3)",
        placeholder="1 = เร็ว | 2 = เร็วมาก | 3 = เร็วดิสพัง",
        style=discord.TextStyle.short,
        required=True,
        max_length=1
    )

    async def on_submit(self, interaction: discord.Interaction):
        # ตรวจสอบ Webhook URL
        if not is_valid_webhook(self.webhook_url.value):
            embed = discord.Embed(title="❌ Webhook URL ไม่ถูกต้อง", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # ตรวจสอบ Webhook ว่าใช้งานได้
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.webhook_url.value, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status != 200:
                        embed = discord.Embed(title="❌ Webhook นี้ใช้งานไม่ได้", color=discord.Color.red())
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        return
        except Exception:
            embed = discord.Embed(title="❌ ไม่สามารถเชื่อมต่อ Webhook ได้", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # ตรวจสอบจำนวนครั้ง
        try:
            amount = int(self.amount.value)
            if not (1 <= amount <= 2000):
                raise ValueError
        except ValueError:
            embed = discord.Embed(title="❌ จำนวนครั้งไม่ถูกต้อง (1-2000)", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # ตรวจสอบโหมดความเร็ว
        speed_choice = self.speed_mode.value.strip()
        speed_settings = {
            "1": (0.5,  5,  "🚀 เร็ว",       discord.Color.green(),    "🚀"),
            "2": (0.2, 10,  "⚡ เร็วมาก",     discord.Color.gold(),     "⚡"),
            "3": (0.05, 20, "💥 เร็วดิสพัง",  discord.Color.dark_red(), "💥"),
        }
        if speed_choice not in speed_settings:
            embed = discord.Embed(title="❌ เลือกโหมดผิด (1, 2 หรือ 3)", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        delay, concurrency, mode_name, color, speed_emoji = speed_settings[speed_choice]

        words = self.message_words.value.split()
        if not words:
            embed = discord.Embed(title="❌ ไม่มีข้อความ", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # แสดงสถานะเริ่มต้น
        status_embed = discord.Embed(
            title=f"{speed_emoji} {mode_name} — กำลังเตรียมส่ง...",
            description=f"```\nจำนวนครั้ง : {amount:,}\nโหมด       : {mode_name}\nConcurrency: {concurrency}\nDelay      : {delay*1000:.0f} ms\n```",
            color=color
        )
        status_embed.set_footer(text=f"เริ่มส่งโดย: {interaction.user.name}")
        await interaction.response.send_message(embed=status_embed, ephemeral=True)

        # ---- ส่ง Webhook จริง ----
        success_count = 0
        fail_count = 0
        start_time = time.time()
        semaphore = asyncio.Semaphore(concurrency)
        lock = asyncio.Lock()
        last_edit_time = [0.0]  # ใช้ list เพื่อให้แก้ค่าใน closure ได้

        timeout = aiohttp.ClientTimeout(total=10, connect=3)
        connector = aiohttp.TCPConnector(limit=concurrency + 5, ttl_dns_cache=300)

        async def send_one(session: aiohttp.ClientSession, word: str):
            nonlocal success_count, fail_count
            async with semaphore:
                retries = 3
                for attempt in range(retries):
                    try:
                        async with session.post(
                            self.webhook_url.value,
                            json={"content": word}
                        ) as resp:
                            if resp.status in (200, 204):
                                async with lock:
                                    success_count += 1
                                return
                            elif resp.status == 429:
                                retry_after = float(resp.headers.get("Retry-After", "1"))
                                await asyncio.sleep(min(retry_after, 5))
                                continue
                            else:
                                # อื่นๆ รอแล้ว retry
                                await asyncio.sleep(0.5)
                                continue
                    except asyncio.TimeoutError:
                        await asyncio.sleep(0.3)
                        continue
                    except Exception:
                        await asyncio.sleep(0.3)
                        continue
                # หมด retry
                async with lock:
                    fail_count += 1

        async def progress_updater():
            """อัพเดท embed ทุก 1.5 วินาที"""
            progress_chars = 20
            while True:
                await asyncio.sleep(1.5)
                completed = success_count + fail_count
                if completed == 0:
                    continue
                elapsed = time.time() - start_time
                progress = completed / amount
                speed = completed / elapsed if elapsed > 0 else 0
                filled = int(progress * progress_chars)
                bar = "█" * filled + "░" * (progress_chars - filled)

                status_embed.title = f"{speed_emoji} {mode_name} — กำลังส่ง..."
                status_embed.description = (
                    f"**[{bar}] {progress*100:.1f}%**\n"
                    f"```\n"
                    f"ส่งแล้ว  : {completed:,} / {amount:,}\n"
                    f"สำเร็จ   : {success_count:,}\n"
                    f"ล้มเหลว  : {fail_count:,}\n"
                    f"เวลา     : {elapsed:.1f} วิ\n"
                    f"ความเร็ว : {speed:.1f} ครั้ง/วิ\n"
                    f"```"
                )
                try:
                    await interaction.edit_original_response(embed=status_embed)
                except Exception:
                    pass
                if completed >= amount:
                    break

        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            # สร้าง tasks ทั้งหมด
            tasks = [
                asyncio.create_task(send_one(session, words[i % len(words)]))
                for i in range(amount)
            ]

            # เพิ่ม delay ระหว่าง task ถ้าเลือกโหมดช้า (เพื่อป้องกัน rate limit)
            # ส่ง tasks ด้วย gather แต่ throttle ด้วย semaphore ที่กำหนดไว้แล้ว
            updater_task = asyncio.create_task(progress_updater())

            # เพิ่ม delay ระหว่าง launch tasks เพื่อ spread การส่ง
            async def launch_tasks():
                chunk = max(1, concurrency)
                for i in range(0, len(tasks), chunk):
                    await asyncio.gather(*tasks[i:i+chunk])
                    await asyncio.sleep(delay)

            await launch_tasks()
            updater_task.cancel()

        # ---- สรุปผล ----
        elapsed_time = time.time() - start_time
        avg_speed = amount / elapsed_time if elapsed_time > 0 else 0

        if avg_speed >= 100:
            rating = "💥 โคตรเร็ว"
        elif avg_speed >= 50:
            rating = "⚡ เร็วมาก"
        elif avg_speed >= 20:
            rating = "🚀 เร็ว"
        else:
            rating = "🐢 ปกติ"

        success_rate = success_count / amount * 100

        result_embed = discord.Embed(
            title=f"{speed_emoji} ส่ง Webhook เสร็จสิ้น!",
            description=(
                f"```\n"
                f"ส่งทั้งหมด   : {amount:,} ครั้ง\n"
                f"สำเร็จ       : {success_count:,} ({success_rate:.1f}%)\n"
                f"ล้มเหลว      : {fail_count:,} ({100-success_rate:.1f}%)\n"
                f"เวลาที่ใช้   : {elapsed_time:.2f} วิ\n"
                f"ความเร็วเฉลี่ย: {avg_speed:.1f} ครั้ง/วิ\n"
                f"เรตติ้ง      : {rating}\n"
                f"```"
            ),
            color=discord.Color.green() if success_rate >= 90 else discord.Color.orange()
        )

        if fail_count > 0:
            result_embed.add_field(
                name="💡 เคล็ดลับ",
                value="• ลองลดโหมดความเร็วถ้าส่งไม่สำเร็จเยอะ\n• Discord rate limit ประมาณ 30 req/วิ ต่อ webhook",
                inline=False
            )

        try:
            await interaction.edit_original_response(embed=result_embed)
        except Exception:
            pass


def make_menu_embed(name: str, avatar_url: str | None) -> discord.Embed:
    embed = discord.Embed(
        title="🎮 ระบบส่ง Webhook ความเร็วสูง",
        description=(
            "```\nส่งไวขึ้น ไม่ค้าง ไม่ล้มเหลว!\n```\n\n"
            "**🚀 ปุ่มเมนู:**\n"
            "⚡ **ส่ง Webhook** — เปิดฟอร์มกรอกข้อมูล\n"
            "👤 **ติดต่อแอดมิน** — ดูข้อมูลติดต่อแอดมิน\n\n"
            "**🎮 โหมดความเร็ว:**\n"
            "```\n"
            "[1] 🚀 เร็ว       : concurrency  5  delay 500ms\n"
            "[2] ⚡ เร็วมาก    : concurrency 10  delay 200ms\n"
            "[3] 💥 เร็วดิสพัง : concurrency 20  delay  50ms\n"
            "```\n"
            "✨ **ปรับปรุงแล้ว:**\n"
            "• Retry อัตโนมัติ 3 ครั้งต่อข้อความ\n"
            "• จัดการ Rate-limit (429) อัตโนมัติ\n"
            "• Progress bar อัพเดทแบบ real-time\n"
            "• รองรับสูงสุด 2,000 ครั้ง"
        ),
        color=discord.Color.purple()
    )
    embed.set_image(url="https://cdn.discordapp.com/attachments/1427659460679045303/1475165371383287940/standard.gif?ex=69a3be8f&is=69a26d0f&hm=f37ce17634010b09cba07f0c7b779ad4a5ed68504c2e943de2781c1cab0ededa")
    if avatar_url:
        embed.set_thumbnail(url=avatar_url)
    embed.set_footer(text=f"เรียกใช้โดย: {name} | สูงสุด 2,000 ครั้ง")
    return embed


@bot.command(name="ssd")
async def prefix_ssd(ctx):
    avatar = ctx.bot.user.avatar.url if ctx.bot.user.avatar else None
    await ctx.send(embed=make_menu_embed(ctx.author.name, avatar), view=MainMenu())


@tree.command(name="ssd", description="📋 เปิดเมนูระบบส่ง Webhook")
async def slash_ssd(interaction: discord.Interaction):
    avatar = interaction.client.user.avatar.url if interaction.client.user.avatar else None
    await interaction.response.send_message(
        embed=make_menu_embed(interaction.user.name, avatar),
        view=MainMenu()
    )


@bot.event
async def on_ready():
    print(f"✅ บอทออนไลน์แล้ว: {bot.user}")
    print(f"🆔 บอท ID: {bot.user.id}")
    print(f"🌐 เซิร์ฟเวอร์: {len(bot.guilds)} แห่ง")
    try:
        bot.tree.clear_commands(guild=None)
        await bot.tree.sync()
        print("✅ ซิงค์คำสั่งเสร็จสิ้น")
    except Exception as e:
        print(f"⚠️ ไม่สามารถซิงค์คำสั่ง: {e}")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="⚡ !ssd | ส่งไว ไม่ล้มเหลว"
        )
    )

bot.run(TOKEN)
