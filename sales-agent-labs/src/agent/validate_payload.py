import json
from pydantic import ValidationError
from .models import SalesSlide


def validate_sales_slide_payload(payload: dict) -> SalesSlide:
    return SalesSlide(**payload)


if __name__ == "__main__":
    import sys, pathlib

    path = pathlib.Path(sys.argv[1])
    data = json.loads(path.read_text(encoding="utf-8"))
    try:
        model = validate_sales_slide_payload(data)
        print("✅ Valid\n", model.model_dump(), sep="")
    except ValidationError as e:
        # Pydantic aggregates errors by field; perfect for user feedback
        print("❌ Invalid:")
        for err in e.errors():
            loc = ".".join(str(p) for p in err["loc"])
            msg = err["msg"]
            print(f"- {loc}: {msg}")
        raise SystemExit(1)
