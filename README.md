# Rem + Ram: Two Independent Discord Bots in One Railway Codebase

This project runs **two separate Discord bot accounts** from one codebase and one Railway service:
- **Rem bot** uses `DISCORD_TOKEN_REM`, its own Discord application, avatar, username, and bot user ID.
- **Ram bot** uses `DISCORD_TOKEN_RAM`, its own Discord application, avatar, username, and bot user ID.

The `run_bots.py` launcher starts both `bot.py` processes. Each has its own character prompt and separate chat/memory history. Both share one SQLite database file, with conversation records separated by character and user.

## Feature ownership
- **Rem bot:** AI conversation and image understanding, welcome embeds, role pings in configured Games/Creations/Arts/Music channels.
- **Ram bot:** AI conversation and image understanding, birthday registration and announcements, QOTD posting and role ping, trivia, guessing game, and Would You Rather.
- AI replies are restricted to IDs in `AUTHORIZED_USER_IDS`. Server automations and games can be used by other members as configured.
- Both bots can be mentioned or replied to in server channels. DMs go to whichever bot account received the DM.

## 1. Create two Discord bot applications
1. Go to https://discord.com/developers/applications and create an application named Rem.
2. Add a bot user, set its avatar, and copy its token. Keep the token private.
3. Create a second application named Ram, add its bot user, set a different avatar, and copy its separate token.
4. For **both** bots, enable **Message Content Intent** and **Server Members Intent** under Bot > Privileged Gateway Intents.
5. Invite both bot accounts to your server with `bot` and `applications.commands` scopes. Suggested permissions: View Channels, Send Messages, Embed Links, Read Message History, Add Reactions. Ensure the bot roles can mention the configured roles.

## 2. Configure Railway
1. Push `bot.py`, `run_bots.py`, and `requirements.txt` to one GitHub repository.
2. Create one long-running Railway service from that repository.
3. Set the Railway **Start Command** to `python run_bots.py`.
4. Add the variables shown in `.env.example`, replacing example IDs and secrets. Set `DISCORD_TOKEN_REM` and `DISCORD_TOKEN_RAM` to the different bot tokens. Never commit tokens or API keys to GitHub.
5. Attach a persistent volume mounted at `/data`; keep `DATABASE_PATH=/data/rem_ram.sqlite3`.
6. Keep one Railway replica for this SQLite setup. Check deployment logs to confirm both bot accounts log in.

## 3. OpenAI API
Create a key at https://platform.openai.com/api-keys. API usage is billed separately from a ChatGPT subscription. Set spending limits and monitor usage. `gpt-4o-mini` supports image input.

## Commands
- On Rem: `/rem message:`; `/remember` and `/memories` for Rem's memory.
- On Ram: `/ram message:`; `/remember` and `/memories` for Ram's memory; `/setbirthday month: day:`, `/removebirthday`, `/qotd question:`, `/trivia`, `/guess`, `/guessanswer answer:`, `/wouldyourather`.
- AI slash commands are ephemeral in server channels. Birthday registration stores month/day only.

## Notes
- These are genuinely separate Discord identities, not two names on one bot account.
- Bot chat history and saved memories are separated by user and character, even though the database file is shared.
- Rem sends a role ping for every new message in configured showcase channels, including replies; adjust the channel filter in `bot.py` if you only want new showcase threads/posts.
- `/qotd` pings the configured role only when the Ram bot posts a new question using that command.
- A persistent Railway volume is needed to keep birthdays and memories through redeploys.
- The avatar is configured in each Discord Developer Portal application; `REM_APPEARANCE` and `RAM_APPEARANCE` are text context for AI, not image generation.

## Troubleshooting
- If one bot is offline, check its token variable (`DISCORD_TOKEN_REM` or `DISCORD_TOKEN_RAM`) and Railway logs.
- If message triggers fail, enable Message Content Intent for that specific bot application.
- If Rem's welcome messages fail, enable Server Members Intent for Rem and verify the welcome channel ID/permissions.
- If commands do not appear, confirm each bot was invited with `applications.commands` and check logs after restart.
- If birthdays do not announce, check timezone, channel/role IDs, permissions, and persistent volume.
- If AI fails, check `OPENAI_API_KEY`, model access, API billing limits, and logs.
