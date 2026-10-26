# Rem + Ram — Railway-hosted AI model

This version runs **both Discord bots and the Ollama AI model on Railway**. Your PC does not need to stay on. The model is `qwen2.5vl:3b`, a small vision-language model for text chat and image understanding. It runs on Railway CPU (no GPU), so responses may be slower than GPU-hosted AI.

## Important cost / plan warning

**Railway's Free plan is not enough for this model.** Railway's published Free service limit is 0.5 GB RAM and 1 vCPU; small Ollama models generally need several GB of RAM. Plan for a paid Railway service with enough RAM/CPU (start around 6–8 GB RAM for this vision model) and a persistent volume of at least 5 GB for Ollama weights. Railway bills compute and storage usage; this is not free unlimited cloud hosting. Ollama itself has no per-token API quota, but Railway infrastructure costs still apply. Check Railway's current pricing before deploying: https://docs.railway.com/pricing

Official Railway Ollama deployment reference: https://railway.com/deploy/ollama--ollama-railway

## Deploy it on Railway

Use the same GitHub repository for two Railway services. Push this folder's contents to the repository root first.

### 1. Create the Ollama model service

1. In Railway, add a service from this repo and set its **Root Directory** to `/ollama`.
2. Name the service exactly **`Ollama`** so the private-domain variable below resolves as written.
3. Add a persistent **Volume** mounted at `/root/.ollama`, with at least **5 GB**.
4. Set the service's memory/CPU limits to suit the model. Start with 6–8 GB RAM if available; if it gets OOM-killed, increase RAM or switch to a smaller text-only model.
5. Do **not** generate a public domain for Ollama. The API has no built-in authentication and should remain private to your Railway project.
6. Deploy it. On first boot, `start-ollama.sh` downloads `qwen2.5vl:3b`; this can take a while. The persistent volume prevents re-downloading the weights on each restart.

### 2. Create the Discord bot service

1. Add another service from the same repository, with the repository root as its Root Directory (`/`).
2. Start command: `python run_bots.py`.
3. Add a persistent **Volume** mounted at `/app/data` so saved memories, chat history, and birthdays survive redeploys.
4. Add the environment variables below. In Railway's variable editor, `AI_BASE_URL` should be set exactly to `http://${{Ollama.RAILWAY_PRIVATE_DOMAIN}}:11434/v1` (Railway expands this reference when the service is named `Ollama`).
5. Deploy. The two Discord bot processes run separately in this service, each with its own token.

## Required bot-service variables

```env
DISCORD_TOKEN_REM=your_rem_bot_token
DISCORD_TOKEN_RAM=your_ram_bot_token
AI_BASE_URL=http://${{Ollama.RAILWAY_PRIVATE_DOMAIN}}:11434/v1
AI_API_KEY=ollama
AI_MODEL=qwen2.5vl:3b
AI_NUM_THREADS=2
AUTHORIZED_USER_IDS=your_discord_user_id
FRIEND_USER_ID=your_friend_moha_discord_user_id
FRIEND_NAME=Moha
TIMEZONE=Asia/Baghdad
DATABASE_PATH=/app/data/rem_ram.sqlite3
```

Copy other optional channel and role settings from `.env.example` as needed. Do not commit actual bot tokens to GitHub.

`FRIEND_USER_ID` must be Moha's **numeric Discord user ID**. Setting this value automatically authorizes him to use both bots and attaches `friend_personality.txt` and `friend_appearance.txt` only to his conversations. His displayed/profile name is set to `Moha` by `FRIEND_NAME`.

## Discord setup

For both bot applications, enable **Message Content Intent** and **Server Members Intent** under Bot → Privileged Gateway Intents. Invite both bot accounts to your server with the needed permissions and `applications.commands` scope.

## Troubleshooting

- **Bot cannot connect to AI:** confirm both services are in the same Railway project/environment, Ollama service is named `Ollama`, and the bot's `AI_BASE_URL` uses the private domain variable.
- **Ollama keeps restarting / OOM:** increase memory. The free tier's 0.5 GB RAM cannot run this model.
- **Model download repeats:** ensure the Ollama volume is mounted at `/root/.ollama`.
- **Slow answers:** Railway does not provide GPU instances; the vision model runs on CPU. `AI_NUM_THREADS` defaults to 2 and can be adjusted to match your allocated CPU.
- **Memories disappear:** ensure the bot-service volume is mounted at `/app/data` and `DATABASE_PATH=/app/data/rem_ram.sqlite3`.
- **Images fail:** confirm the attachment is accessible to the bot and the Ollama model finishes loading successfully.

## Included features

- Two separate Discord bot accounts (Rem and Ram) in one bot service.
- Separate character personalities, chat histories, and saved memories.
- Image understanding using the vision model.
- Friend-specific profile for Moha.
- Rem welcome embeds and showcase role pings.
- Ram birthday registration/announcements, QOTD, trivia, guessing game, and Would You Rather.
