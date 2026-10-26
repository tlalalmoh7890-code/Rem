"""Run two independent Discord bot accounts from one Railway service/codebase."""
import asyncio
import os
import signal
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

async def main():
    token_map = {
        "rem": os.getenv("DISCORD_TOKEN_REM", "").strip(),
        "ram": os.getenv("DISCORD_TOKEN_RAM", "").strip(),
    }
    missing = [name for name, token in token_map.items() if not token]
    if missing:
        raise RuntimeError("Missing Railway variable(s): " + ", ".join(f"DISCORD_TOKEN_{name.upper()}" for name in missing))

    children = []
    for character, token in token_map.items():
        env = os.environ.copy()
        env["BOT_CHARACTER"] = character
        env["DISCORD_TOKEN"] = token
        children.append(await asyncio.create_subprocess_exec(
            sys.executable, os.path.join(ROOT, "bot.py"), env=env
        ))
    try:
        waiters = [asyncio.create_task(child.wait()) for child in children]
        done, pending = await asyncio.wait(waiters, return_when=asyncio.FIRST_COMPLETED)
        exited = [(children[waiters.index(task)], task.result()) for task in done]
        # If either bot stops, stop the other too so Railway can restart the whole service.
        raise RuntimeError("A bot process exited unexpectedly: " + ", ".join(
            f"pid={child.pid}, exit_code={code}" for child, code in exited
        ))
    finally:
        for child in children:
            if child.returncode is None:
                child.terminate()
        await asyncio.gather(*(child.wait() for child in children), return_exceptions=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
