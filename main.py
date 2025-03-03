import discord
from discord.ext import commands
import os
from keep_alive import keep_alive  # Keeps the bot running on Replit

TOKEN = os.getenv("DISCORD_TOKEN")  # Fetch bot token from Replit Secrets

if TOKEN is None:
    raise ValueError("DISCORD_TOKEN is not set in environment variables!")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="10!", intents=intents)

queue = []  # List to store players
captains = []  # List to store players who want to be captains
player_roles = {}  # Track player roles (main and secondary)

def reset_queues():
    """Resets all game-related lists."""
    global queue, captains, player_roles
    queue = []
    captains = []
    player_roles = {}

@bot.event
async def on_ready():
    """Triggered when the bot is ready."""
    print(f'Logged in as {bot.user}')

@bot.command()
async def start(ctx):
    """Start the 10-man queue."""
    reset_queues()

    # Create the embed message
    embed = discord.Embed(
        title="🏆 10-Man Queue 🏆",
        description="Press the buttons below to join as a Captain or Player.",
        color=discord.Color.blue()  # Customize the color here
    )
    embed.add_field(name="📢 Queue Information", value="Currently **0/10** players in the queue", inline=False)
    embed.set_footer(text="Use the buttons below to join the queue!")

    # Create buttons for captains, players, and leave
    captain_button = discord.ui.Button(label="Join as Captain 🏆", style=discord.ButtonStyle.green, custom_id="join_captain")
    player_button = discord.ui.Button(label="Join as Player 🎮", style=discord.ButtonStyle.primary, custom_id="join_player")
    leave_button = discord.ui.Button(label="❌ Leave", style=discord.ButtonStyle.red, custom_id="leave_queue")

    # Add buttons to a view
    view = discord.ui.View()
    view.add_item(captain_button)
    view.add_item(player_button)
    view.add_item(leave_button)

    # Send the message with embed and buttons
    message = await ctx.send(embed=embed, view=view)

    # Store the message object so we can update it later with the player count
    await update_queue_count(ctx, message)

async def update_queue_count(ctx, message):
    """Update the queue count in the message."""
    embed = message.embeds[0]
    embed.set_field_at(0, name="📢 Queue Information", value=f"Currently **{len(queue)}/10** players in the queue", inline=False)

    # Edit the message with the updated embed
    await message.edit(embed=embed)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    """Handle button interactions (captain/player join, leave, role selection)."""
    if interaction.data is None:
        return  # Ignore interactions that don't have data

    custom_id = interaction.data.get("custom_id")  # Safely access custom_id

    if custom_id == "join_captain":
        await join_captain(interaction)
    elif custom_id == "join_player":
        await join_player(interaction)
    elif custom_id == "leave_queue":
        await leave_queue(interaction)
    elif custom_id == "role_tank":
        await pick_secondary_role(interaction, "Tank")
    elif custom_id == "role_dps":
        await pick_secondary_role(interaction, "DPS")
    elif custom_id == "role_support":
        await pick_secondary_role(interaction, "Support")
    elif custom_id.startswith("pick_main_role"):
        await pick_main_role(interaction)

async def join_captain(interaction):
    """Join as a captain."""
    if interaction.user in queue or interaction.user in captains:
        await interaction.response.send_message(f"{interaction.user.mention}, you're already in the queue!", ephemeral=True)
        return

    if len(queue) >= 10:
        await interaction.response.send_message("Queue is full! Wait for the next game.", ephemeral=True)
        return

    captains.append(interaction.user)
    queue.append(interaction.user)
    await interaction.response.send_message(f"{interaction.user.mention} has joined as a Captain! ({len(queue)}/10)", ephemeral=True)

    # Update the message with the new player count
    await update_queue_count(interaction, interaction.message)

    # After joining, prompt the player to select their Main Role
    await pick_main_role(interaction)

async def join_player(interaction):
    """Join as a player."""
    if interaction.user in queue:
        await interaction.response.send_message(f"{interaction.user.mention}, you're already in the queue!", ephemeral=True)
        return

    if len(queue) >= 10:
        await interaction.response.send_message("Queue is full! Wait for the next game.", ephemeral=True)
        return

    queue.append(interaction.user)
    await interaction.response.send_message(f"{interaction.user.mention} has joined the queue! ({len(queue)}/10)", ephemeral=True)

    # Update the message with the new player count
    await update_queue_count(interaction, interaction.message)

    # After joining, prompt the player to select their Main Role
    await pick_main_role(interaction)

async def leave_queue(interaction):
    """Leave the queue."""
    if interaction.user not in queue:
        await interaction.response.send_message(f"{interaction.user.mention}, you're not in the queue!", ephemeral=True)
        return

    queue.remove(interaction.user)

    if interaction.user in captains:
        captains.remove(interaction.user)

    await interaction.response.send_message(f"{interaction.user.mention} has left the queue. ({len(queue)}/10)", ephemeral=True)

    # Update the message with the new player count
    await update_queue_count(interaction, interaction.message)

async def pick_main_role(interaction):
    """Allow players to select their main role."""
    main_role_button = discord.ui.Button(label="Tank", style=discord.ButtonStyle.green, custom_id="role_tank")
    dps_role_button = discord.ui.Button(label="DPS", style=discord.ButtonStyle.green, custom_id="role_dps")
    support_role_button = discord.ui.Button(label="Support", style=discord.ButtonStyle.green, custom_id="role_support")

    # Add buttons for role selection
    view = discord.ui.View()
    view.add_item(main_role_button)
    view.add_item(dps_role_button)
    view.add_item(support_role_button)

    embed = discord.Embed(title="Pick Your Main Role", description="Please select your main role.", color=discord.Color.blue())
    await interaction.response.send_message(embed=embed, view=view)

async def pick_secondary_role(interaction, main_role):
    """Allow players to select their secondary role, excluding the main role."""
    # Track the main role for later
    player_roles[interaction.user.id] = {"main": main_role}

    # Show secondary roles excluding the main role
    if main_role == "Tank":
        secondary_roles = ["DPS", "Support"]
    elif main_role == "DPS":
        secondary_roles = ["Tank", "Support"]
    else:  # Support
        secondary_roles = ["Tank", "DPS"]

    # Create buttons for secondary roles
    view = discord.ui.View()
    for role in secondary_roles:
        view.add_item(discord.ui.Button(label=role, style=discord.ButtonStyle.green, custom_id=f"role_{role.lower()}_secondary"))

    embed = discord.Embed(title="Pick Your Secondary Role", description="Please select your secondary role.", color=discord.Color.blue())
    await interaction.response.send_message(embed=embed, view=view)

# Run the bot
keep_alive()  # Start Flask server to keep bot alive
bot.run(TOKEN)
