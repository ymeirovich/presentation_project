import logging
from .config import settings
import sys
import asyncio
from .poke import get_pokemon, format_pokemon_human
from .errors import AgentError
from .apoke import aget_many
import json, pathlib
from .validation import validate_sales_slide_payload, ValidationError
from .validate_payload import validate_sales_slide_payload as cmd_validate_slide




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

def cmd_validate_json(args:list[str]) -> int:
    if not args:
        print("Usage: python -m agent validate-json <path/to.json>")
        return 2
    
    path = pathlib.Path(args[0])
    if not path.exists():
        print(f"❌ File not found: {path}")
        return 2
    
    data = json.loads(path.read_text(encoding="utf-8"))
    try:
        clean= validate_sales_slide_payload(data, trim_script=True, forbid_extra=True)
    except ValidationError as e:
        print(f"❌ Invalid payload: {e}")
        for i, msg in enumerate(e.errors, start=1):
            print(f"  {i}. {msg}")
        return 1
    
    print("✅ Valid payload:")
    print(json.dumps(clean, ensure_ascii=False, indent=2))
    return 0


def main():
    configure_logging()
    log= logging.getLogger("agent")

    if len(sys.argv)>=2:
        cmd, *rest = sys.argv[1:]
        if cmd== "fetch-pokemon":
            sys.exit(cmd_fetch_pokemon(rest))
        if cmd=="fetch-many":
            sys.exit(cmd_fetch_many(rest))
        if cmd=="validate-json":
            sys.exit(cmd_validate_json(rest))
        if cmd=="validate-slide":
            if not rest:
                print("Usage: python -m agent validate-slide <path/to.json>")
                sys.exit(2)
            
            path = pathlib.Path(rest[0])
            if not path.exists():
                print(f"❌ File not found: {path}")
                sys.exit(2)

            data = json.loads(path.read_text(encoding="utf-8"))
            try:
                model = cmd_validate_slide(data)
                print("✅ Valid\n", model.model_dump(), sep="")
            except ValidationError as e:
                # Pydantic aggregates errors by field; perfect for user feedback
                print("❌ Invalid:")
                for err in e.errors():
                    loc = ".".join(str(p) for p in err["loc"])
                    msg = err["msg"]
                    print(f"- {loc}: {msg}")
                sys.exit(1)
            sys.exit(0)

    log.info("Try: python -m agent fetch-pokemon pikachu bulbasaur charmander")
    print("👋 Nothing to do. See logs above.")

if __name__ == "__main__":
    main()