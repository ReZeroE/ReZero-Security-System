import os
import sys
import discord
import time
import asyncio
from datetime import datetime

from permission import PermissionIdentifier
from parse_command import ParseCommand
from log_data import LogData
from resize_vid import resize_video
from anilist import AnilistDiscord

anilist = AnilistDiscord()


client = discord.Client()

BOT_ID = 'xxxxxxxxxxxxxxxxxxxx'
BOT_CHANNEL_ID = 0000000000000000000
BOT_SERVER_ID = 0000000000000000000

BOT_NAME = 'OpenCV-Python'
prefix = '>'
up_time = time.time()


@client.event # run the code when the bot goes online
async def on_ready():
    bot_channel = client.get_channel(BOT_CHANNEL_ID) 
    date_time = datetime.now().strftime("[%m/%d/%Y - %H:%M:%S]")

    print(f"{BOT_NAME} is now online!")
    await bot_channel.send(f"{date_time} {BOT_NAME} is now online!")
    

async def check_for_new_recording():
    '''
    Function for checking whether a new video has been recorded. Runs in the background.
    '''
    recordings_count = 0
    recordings_history = []
    RECORDINGS_PATH = os.path.dirname(os.path.dirname(__file__)) + "/recordings"

    await client.wait_until_ready()
    bot_channel = client.get_channel(BOT_CHANNEL_ID)

    try:
        while not client.is_closed():
            recordings = os.listdir(RECORDINGS_PATH)
            try: 
                recordings.remove('out.mp4')                                # buffer recording doesn't count
            except: pass
            recordings = [r for r in recordings if r.find('.mp4') != -1]    # ensure all files are .mp4 files

            new_video_detected = False
            if len(recordings) > recordings_count: # new video detected
                date_time = datetime.now().strftime("[%H:%M:%S]")
                await bot_channel.send(f"**{date_time} New Video(s) Detected** -> {[r for r in recordings if r not in recordings_history]}")
                new_video_detected = True

                if len(recordings) - recordings_count == 1: # only one new video detected
                    new_recording_filename = [r for r in recordings if r not in recordings_history][0]
                    vid_file_path = RECORDINGS_PATH + f"/{new_recording_filename}"

                    await bot_channel.send("Waiting for the video to finalize... (10 minutes)")
                    await asyncio.sleep(6) # wait for the video to finalize
                    try:
                        await bot_channel.send(file=discord.File(resize_video(vid_file_path)))
                    except Exception as ex:
                        await bot_channel.send(f"**Error reformatting video {vid_file_path}.** [{str(ex)}]")
                else:
                    await bot_channel.send("New video count > 1 (old videos present in the log dir). Not reporting.")

                recordings_count = len(recordings)
                recordings_history = recordings

            dt = datetime.now().strftime("[%H:%M:%S]")
            if not new_video_detected:
                try:
                    await bot_channel.purge(limit=1)
                except: pass # discord.errors.NotFound
            await bot_channel.send(f"{dt} Pending new video...")
            await asyncio.sleep(15) # task runs every 15 seconds
    
    except Exception as ex:
        await bot_channel.send(f"FATAL ERROR: {ex} -> sleeping for 60 seconds (recommanded: `>get dir <path>`)")
        await asyncio.sleep(60)


@client.event
async def on_message(message):
    original_input = message.content
    server_id = message.guild.id
    user_id = message.author.id
    username = message.author.name

    if message.content.startswith(prefix) == False: return  # check bot command's prefix
    if message.author == client.user: return                # check is message user is bot
    if server_id != BOT_SERVER_ID: return                   # check bot's operational server

    pi = PermissionIdentifier()
    permission = pi.get_permission(user_id, username)

    if permission.find('new') != -1:
        print(f"New user: [{username}] has been successfully added to the database")

    # log user input
    ld = LogData()
    ld.log_data(user_id, username, original_input, str(message.channel), message.channel.id)

    # parse command
    pc = ParseCommand()
    parsed_command = pc.parse_command(original_input)
    print(f"Input Data -> User Permission: {permission}, Parsed Command: {parsed_command}")

    # Admin comands =====================================================================================================================================
    if parsed_command.startswith('A'):
        if permission != 'C0':
            await message.channel.send(f"You do not have permission to access Admin commands (C0 clearance required).")
            return

        # purge
        if parsed_command == "A1":
            user_purge_list = original_input.replace('>', '').split(' ')
            try:
                purge_count = int(user_purge_list[1])
            except TypeError:
                await message.channel.send(f"Purge count >{user_purge_list[1]}< incorrect. Please re-enter.")

            try:
                await message.channel.purge(limit=1)
                await message.channel.send(f"Message Purge Initiated ({purge_count} messages will be purged in 3 seconds).")
                time.sleep(3)
                await message.channel.purge(limit=purge_count + 1)
            except: pass # discord.errors.NotFound
            return 


    # Moderator commands ================================================================================================================================
    if parsed_command.startswith('M'):
        if permission != 'C1' and permission != 'C0':
            await message.channel.send(f"You do not have permission to access Moderator commands (C1 clearance required).")
            return

        # terminate
        if parsed_command == "M1":
            await message.channel.send(f"Bye!")
            sys.exit(0)


    # User commands ====================================================================================================================================

    # U1 Help
    # U2 Anime search
    # U3 Get directory content
    # *U4 UNIMPLEMENTED
    # U5 Get Perm
    # U6 Get Status

    if parsed_command.startswith('U'):
        if permission != 'C2' and permission != 'C2 - new' and permission != 'C1' and permission != 'C0':
            await message.channel.send(f"Error: Please try again later. (DB-1)")
            return

        # help
        if parsed_command == "U1":
            embed_obj = discord.Embed(title="Commands Panel", description="", color=0xA0DB8E)
            embed_obj.add_field(name="`>help`", value="Displays all user commands", inline=False)
            embed_obj.add_field(name="`>status`", value="Gets current bot status (including internet latency)", inline=False)
            embed_obj.add_field(name="`>get dir <directory path>`", value="Returns the content of the given directory path on the machine.", inline=False)
            embed_obj.add_field(name="`>get anime <anime name>`", value="Searches up an anime with the given name.\nExample: `>get anime kimetsu no yaiba`", inline=False)
            await message.channel.send(embed=embed_obj)
            return

        # get anime
        if parsed_command.startswith("U2"):
            import re

            temp_l = parsed_command.split('|')
            anime_name = original_input.replace('>', '').replace(temp_l[1], '').strip()
            anime_embed = anilist.get_anime_discord(anime_name=anime_name)

            if anime_embed == -1:
                await message.channel.send(f"Anime not found! Please try again or use a different name. (romaji preferred)")
            else:
                await message.channel.send(embed=anime_embed)
            return

        # Get directory content
        if parsed_command.startswith("U3"):
            temp_l = parsed_command.split('|')
            target_dir = original_input.replace('>', '').replace(temp_l[1], '').strip()
            try:
                files_list = os.listdir(target_dir)
                str_files_list = "\n".join(files_list)

                ebd = discord.Embed(title="Directory Files", color=discord.Color.blue())
                ebd.add_field(name=f"{target_dir}", value=str_files_list)
                await message.channel.send(embed=ebd)
            except:
                rd = os.path.dirname(os.path.dirname(__file__)) + "/recordings"
                await message.channel.send(f"**Directory ({target_dir}) cannot be found.** [Recording Dir: {rd}]")
            return
        

        # UNIMPLEMENTED
        if parsed_command == "U4":
            return


        # get perm
        if parsed_command == "U5":
            embed_obj = discord.Embed(title="Permission Panel", description=f"Username: {username}\nPermission Level: {permission}\nUser ID: {user_id}", color=0xA0DB8E)
            await message.channel.send(embed=embed_obj)
            return

        # get status
        if parsed_command == "U6":
            from ping3 import ping
            try:
                pin = round(ping('google.com') * 1000, 2)
                import datetime
                embed_obj = discord.Embed(title=f"{BOT_NAME} Status Panel", description=f"**Status**: Online\n**Uptime: **{str(datetime.timedelta(seconds = int(time.time() - up_time)))}\n**Internet Latency:** {pin}ms", color=0xA0DB8E)
                await message.channel.send(embed=embed_obj)
            except Exception as e:
                print(e)
                await message.channel.send(f"Warning: Status Request Failed - failed to connect (FN-1)")
            return

    await message.channel.send(f"Sorry, I can't understand your input.\nFor any help, use the command `>help`.")


def run_bot():
    client.loop.create_task(check_for_new_recording())
    while True:
        client.run(BOT_ID)


if __name__ == "__main__":
    run_bot()
    