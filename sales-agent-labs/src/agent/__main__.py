import logging
from .config import settings
import sys
from .poke import get_pokemon

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
    data = get_pokemon(name)
    print(f"{data['name'].title()} (id={data['id']})")
    print(f"Height: {data['height_dm']} dm | Weight: {data['weight_hg']} hg")
    print(f"Abilities: {', '.join(data['abilities'])}")
    print(f"Sprite: {data['sprite']}")
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