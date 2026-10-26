# All-in-One Discord AI Companion Bot

This single Python bot provides:
- A private AI companion available in DMs to one authorized Discord user.
- Server replies when that user mentions the bot, replies to one of its messages, or starts a message with its configured name/nickname.
- Configurable character name, personality, appearance description, and nicknames.
- Image understanding for images uploaded by the authorized user.
- SQLite conversation history and manually saved memories.
- Custom welcome embeds for every new server member.

## Important notes

- The AI uses the OpenAI API. API charges are separate from a ChatGPT subscription and depend on usage.
- The bot's appearance description is text configuration. Set the bot's Discord avatar separately in the Developer Portal.
- Image understanding describes visible content; it does not identify real people or reliably infer personality from a face.
- SQLite only persists if your host provides persistent storage and `DATABASE_PATH` points inside it.
- Never commit `.env`, tokens, or API keys to a public repository.

## 1. Create the Discord application

1. Go to https://discord.com/developers/applications and create an application.
2. Open **Bot**, add a bot if needed, and copy its token. Keep it secret.
3. Under **Bot > Privileged Gateway Intents**, enable **Message Content Intent** and **Server Members Intent**.
4. In **OAuth2 > URL Generator** or **Installation**, select `bot` and `applications.commands`.
5. Grant only the permissions needed, such as View Channels, Send Messages, Embed Links, Read Message History, and Attach Files if you want it to handle image attachments.
6. Invite the bot to your server.

The Message Content and Server Members intents must be enabled both in the Developer Portal and in code.

## 2. Find your Discord IDs

Enable Discord Developer Mode (User Settings > Advanced > Developer Mode). Right-click your profile and choose **Copy User ID**. Copy the welcome channel ID in the same way.

Put those IDs in the environment variables `AUTHORIZED_USER_ID` and `WELCOME_CHANNEL_ID`.

## 3. Get an API key

Create an API key in the OpenAI platform: https://platform.openai.com/api-keys . Add billing/usage limits as appropriate. A ChatGPT subscription does not automatically include API usage.

## 4. Configure locally

1. Install Python 3.11 or newer.
2. Copy `.env.example` to `.env`.
3. Fill in the Discord token, API key, user ID, and welcome channel ID.
4. Customize `AI_NAME`, `AI_NICKNAMES`, `AI_PERSONALITY`, `AI_APPEARANCE`, and the welcome settings.
5. Install and run:

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
python bot.py
```

## 5. Deploy 24/7

Use a host that supports a continuously running Python worker. For example, create a Railway project from your repository and configure it as a worker/service (not a web server).

- Add every variable from `.env.example` in the host's Variables settings.
- Set the start command to `python bot.py`.
- Attach a persistent volume and mount it at `/data`.
- Set `DATABASE_PATH=/data/bot_memory.sqlite3`.
- Deploy and inspect logs. Do not run two replicas using the same SQLite database.

A free hosting tier may sleep, stop, or have limited resources. Always check the host's current pricing and policies.

## 6. How to use it

- DM the bot: it replies to the authorized user without a trigger.
- In a server, mention the bot, reply to one of its messages, or start the message with its name/nickname, for example:
  - `@Hikari Hello!`
  - `Hikari, how was your day?`
  - `honey, do you remember my favorite game?`
- Only the configured `AUTHORIZED_USER_ID` receives AI replies. Other members can still receive welcome embeds.
- `/remember fact: I love rhythm games` saves a memory.
- `/memories` lists saved memories.
- `/forgetmemory memory_id: 1` deletes a saved memory.
- `/clearhistory` clears chat history but leaves saved memories.

## Troubleshooting

- **Bot is offline:** check `DISCORD_TOKEN`, deployment logs, and whether the worker is running.
- **It cannot read messages:** enable Message Content Intent in the Developer Portal and in code; restart the bot.
- **No welcome message:** enable Server Members Intent, verify `WELCOME_CHANNEL_ID`, and grant Send Messages + Embed Links in that channel.
- **Slash commands do not appear:** wait a few minutes, check that `applications.commands` was invited, and inspect logs for sync errors.
- **AI API error:** verify `OPENAI_API_KEY`, model availability, billing/usage limits, and provider status.
- **Memory disappears after redeploy:** set `DATABASE_PATH` on a persistent volume; the default local file may be lost on some hosts.
- **Nickname trigger does not work:** it only matches at the beginning of a server message, ignoring case. Add aliases to `AI_NICKNAMES`, comma-separated.
