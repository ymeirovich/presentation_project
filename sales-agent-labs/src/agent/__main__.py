import logging
from .config import settings
import sys
from .poke import get_pokemon, format_pokemon_human
from .errors import AgentError


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

def main():
    configure_logging()
    log= logging.getLogger("agent")

    if len(sys.argv)>=2 and sys.argv[1]=="fetch-pokemon":
        sys.exit(cmd_fetch_pokemon(sys.argv[2:]))

    log.info("Try: python -m agent fetch-pokemon pikachu")
    print("👋 Nothing to do. See logs above.")

if __name__ == "__main__":
    main()