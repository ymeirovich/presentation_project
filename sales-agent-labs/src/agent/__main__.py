import logging
from .config import settings
import sys
import asyncio
from .poke import get_pokemon, format_pokemon_human
from .errors import AgentError
from .apoke import aget_many


def configure_logging():
    #Simple, readable logs for dev; swap to JSON later if you want
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

def cmd_fetch_pokemon(args:list[str]) -> int:
    if not args:
        print("Usage: python -m agent fetch-pokemon <name>")
        return 2
    name = args[0]
    try:
        info= get_pokemon(name)
    except AgentError as e:
        # One catch for all our domain errors
        print(f"❌ {e}")
        return 1

    print(f"✅ {format_pokemon_human(info)}")
    if info["sprite"]:
        print(f"   Sprite: {info['sprite']}")
    return 0

def cmd_fetch_many(args:list[str]) -> int:
    if not args:
        print("Usage: python -m agent fetch-many <name1> <name2>...")
        return 2
    
    async def run():
        try:
            infos=await aget_many(args)
        except AgentError as e:
            print(f"❌ {e}")
            return 1
        for info in infos:
            print(f"• {info['name']} (id={info['id']}) "
                  f"h={info['height_dm']}dm w={info['weight_hg']}hg "
                  f"abilities={', '.join(info['abilities'])})")
        return 0
    
    # asyncio.run spins up an event loop, runs the coroutine, and closes it.
    return asyncio.run(run())

def main():
    configure_logging()
    log= logging.getLogger("agent")

    if len(sys.argv)>=2:
        cmd, *rest = sys.argv[1:]
        if cmd== "fetch-pokemon":
            sys.exit(cmd_fetch_pokemon(rest))
        if cmd=="fetch-many":
            sys.exit(cmd_fetch_many(rest))

    log.info("Try: python -m agent fetch-pokemon pikachu bulbasaur charmander")
    print("👋 Nothing to do. See logs above.")

if __name__ == "__main__":
    main()