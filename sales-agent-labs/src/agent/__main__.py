import logging
from .config import settings
from .poke import get_pokemon, format_pokemon_human
from .errors import AgentError
from .apoke import aget_many
import json, pathlib, sys, asyncio
from .validation import validate_sales_slide_payload, ValidationError
from .validate_payload import validate_sales_slide_payload as cmd_validate_slide
from .summarizer import summarize_report_to_sales_slide
from .summarizer_chunked import summarize_report_chunked
from .imagegen_vertex import generate_image
from .logging_config import setup_logging
from .slides_google import (
    create_presentation,
    create_main_slide_with_content,
    delete_default_slide,
    add_title_and_subtitle,
    add_bullets_and_script,
    upload_image_to_drive,
    insert_image_from_url,
)

setup_logging()  # ensure logs always appear


# def configure_logging():
#     #Simple, readable logs for dev; swap to JSON later if you want
#     logging.basicConfig(
#         level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
#         format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
#     )


def cmd_fetch_pokemon(args: list[str]) -> int:
    if not args:
        print("Usage: python -m agent fetch-pokemon <name>")
        return 2
    name = args[0]
    try:
        info = get_pokemon(name)
    except AgentError as e:
        # One catch for all our domain errors
        print(f"❌ {e}")
        return 1

    print(f"✅ {format_pokemon_human(info)}")
    if info["sprite"]:
        print(f"   Sprite: {info['sprite']}")
    return 0


def cmd_fetch_many(args: list[str]) -> int:
    if not args:
        print("Usage: python -m agent fetch-many <name1> <name2>...")
        return 2

    async def run():
        try:
            infos = await aget_many(args)
        except AgentError as e:
            print(f"❌ {e}")
            return 1
        for info in infos:
            print(
                f"• {info['name']} (id={info['id']}) "
                f"h={info['height_dm']}dm w={info['weight_hg']}hg "
                f"abilities={', '.join(info['abilities'])})"
            )
        return 0

    # asyncio.run spins up an event loop, runs the coroutine, and closes it.
    return asyncio.run(run())


def cmd_validate_json(args: list[str]) -> int:
    if not args:
        print("Usage: python -m agent validate-json <path/to.json>")
        return 2

    path = pathlib.Path(args[0])
    if not path.exists():
        print(f"❌ File not found: {path}")
        return 2

    data = json.loads(path.read_text(encoding="utf-8"))
    try:
        clean = validate_sales_slide_payload(data, trim_script=True, forbid_extra=True)
    except ValidationError as e:
        print(f"❌ Invalid payload: {e}")
        for i, msg in enumerate(e.errors, start=1):
            print(f"  {i}. {msg}")
        return 1

    print("✅ Valid payload:")
    print(json.dumps(clean, ensure_ascii=False, indent=2))
    return 0


def cmd_summarize_report(args: list[str]) -> int:
    if not args:
        print("Usage: python -m agent summarize-report <path/to_report.txt>")
        return 2

    path = pathlib.Path(args[0])
    if not path.exists():
        print(f"❌ No such file: {path}")
        return 2

    report_text = path.read_text(encoding="utf-8")
    try:
        slide = summarize_report_to_sales_slide(report_text, attempts=2)
    except Exception as e:
        print("❌ Summarization failed:", e)
        return 1

    data = slide.model_dump()  # plain dict
    outdir = pathlib.Path("out")
    outdir.mkdir(parents=True, exist_ok=True)
    outfile = outdir / "slide_payload.json"
    outfile.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print("✅ Summarized slide payload:")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"📄 Saved: {outfile}")
    return 0


def cmd_summarize_report_chunked(args: list[str]) -> int:
    if not args:
        print("Usage: python -m agent summarize-report-chunked <path/to_report.txt>")
        return 2

    path = pathlib.Path(args[0])
    if not path.exists():
        print(f"❌ No such file: {path}")
        return 2

    report_text = path.read_text(encoding="utf-8")

    async def run():
        slide = await summarize_report_chunked(report_text)
        data = slide.model_dump()
        outdir = pathlib.Path("out")
        outdir.mkdir(parents=True, exist_ok=True)
        outfile = outdir / "slide_payload_chunked.json"
        outfile.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print("✅ Chunked summarized slide payload:")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        print(f"📄 Saved: {outfile}")
        return 0

    return asyncio.run(run())


def cmd_generate_image(args: list[str]) -> int:
    if not args:
        print(
            'Usage: python -m agent generate-image "<prompt text>" [--aspect 16:9] [--seed 1234]'
        )
        return 2

    prompt = args[0]
    # quick flag parsing
    aspect = None
    seed = None
    if "--aspect" in args:
        i = args.index("--aspect")
        if i + 1 < len(args):
            aspect = args[i + 1]
    if "--seed" in args:
        i = args.index("--seed")
        if i + 1 < len(args):
            try:
                seed = int(args[i + 1])
            except ValueError:
                print("Invalid --seed value, must be integer.")
                return 2

    out_dir = pathlib.Path("out/images")
    try:
        paths = generate_image(
            project_id=settings.GOOGLE_PROJECT_ID or "presgen",
            prompt=prompt,
            out_dir=out_dir,
            aspect_ratio=aspect or "16:9",
            seed=seed,
        )
    except Exception as e:
        print("❌ Image generation failed:", e)
        return 1

    print("✅ Generated image(s):")
    for p in paths:
        print(" -", p.resolve())
    return 0


def cmd_generate_image_from_payload(args: list[str]) -> int:
    if not args:
        print(
            "Usage: python -m agent generate-image-from-payload <path/to/slide_payload.json>"
        )
        return 2

    path = pathlib.Path(args[0])
    if not path.exists():
        print(f"❌ No such file: {path}")
        return 2

    data = json.loads(path.read_text(encoding="utf-8"))
    image_prompt = data.get("image_prompt")
    if not isinstance(image_prompt, str) or not image_prompt.strip():
        print("❌ payload missing a non-empty 'image_prompt' string.")
        return 1

    out_dir = pathlib.Path("out/images")
    try:
        paths = generate_image(
            project_id=settings.GOOGLE_PROJECT_ID or "presgen",
            prompt=image_prompt,
            out_dir=out_dir,
            aspect_ratio="16:9",
            seed=1234,  # fixed seed for reproducibility across runs
        )
    except Exception as e:
        print("❌ Image generation failed:", e)
        return 1

    print("✅ Generated image(s) from payload:")
    for p in paths:
        print(" -", p.resolve())
    return 0


def cmd_create_slide(args: list[str]) -> int:
    if len(args) < 2:
        print(
            "Usage: python -m agent create-slide <path/to/slide_payload.json> <path/to/image.png>"
        )
        return 2

    payload_path = pathlib.Path(args[0])
    image_path = pathlib.Path(args[1])
    if not payload_path.exists():
        print(f"❌ No such file: {payload_path}")
        return 2
    if not image_path.exists():
        print(f"❌ No such file: {image_path}")
        return 2

    data = json.loads(payload_path.read_text(encoding="utf-8"))
    title = data.get("title") or "Untitled"
    subtitle = data.get("subtitle") or ""
    bullets = data.get("bullets") or []
    script = data.get("script") or ""

    try:
        pres = create_presentation(title)
        pres_id = pres["presentationId"]
        delete_default_slide(pres_id)

        image_url = upload_image_to_drive(image_path)  # returns a public link
        slide_id = create_main_slide_with_content(
            pres_id,
            title=title,
            subtitle=subtitle,
            bullets=bullets,
            image_url=image_url,
            script=script,
        )

        deck_url = "https://docs.google.com/presentation/d/" + pres_id + "/edit"
        print("✅ Presentation ready:")
        print("  Slide:", slide_id)
        print("  URL:  ", deck_url)
        return 0

    except Exception as e:
        print("❌ Failed to create slide:", e)
        return 1


def main():
    # configure_logging()
    log = logging.getLogger("agent")

    if len(sys.argv) >= 2:
        cmd, *rest = sys.argv[1:]
        if cmd == "fetch-pokemon":
            sys.exit(cmd_fetch_pokemon(rest))
        if cmd == "fetch-many":
            sys.exit(cmd_fetch_many(rest))
        if cmd == "validate-json":
            sys.exit(cmd_validate_json(rest))
        if cmd == "summarize-report":
            sys.exit(cmd_summarize_report(rest))
        if cmd == "summarize-report-chunked":
            sys.exit(cmd_summarize_report_chunked(rest))
        if cmd == "generate-image":
            sys.exit(cmd_generate_image(rest))
        if cmd == "generate-image-from-payload":
            sys.exit(cmd_generate_image_from_payload(rest))
        if cmd == "create-slide":
            sys.exit(cmd_create_slide(rest))

        if cmd == "validate-slide":
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
