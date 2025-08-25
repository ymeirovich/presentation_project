from typing import Dict, List, TypedDict
import logging
from .http import get_json
from .errors import DataShapeError, ExternalAPIError
from .text import to_title, comma_join

log = logging.getLogger("agent.poke")
BASE_URL = "https://pokeapi.co/api/v2"


# TypedDict: a lightweight way to describe dict shapes for type checkers.
class PokemonInfo(TypedDict):
    name: str
    id: int
    height_dm: int  # height in decimeters
    weight_hg: int  # weight in hectograms
    abilities: List[str]  # list of ability names
    sprite: str | None  # URL to the sprite image


def _extract_pokemon_fields(data: Dict) -> PokemonInfo:
    """
    Extract and normalize fields from the raw PokeAPI JSON.
    Raises DataShapeError if expected fields are missin."""
    try:
        abilities: List[str] = [a["ability"]["name"] for a in data["abilities"]]
        sprite = data["sprites"]["front_default"]  # may be None for some
        info: PokemonInfo = {
            "name": data["name"],
            "id": data["id"],
            "height_dm": data["height"],  # decimeters
            "weight_hg": data["weight"],  # hectograms
            "abilities": abilities,
            "sprite": sprite,
        }
        return info
    except KeyError as e:
        # Convert a low-level KeyError into a domain error that callers understand.
        raise DataShapeError(f"PokeAPI JSON is missing key: {e!s}") from e


def get_pokemon(name: str) -> Dict:
    """Fetch a Pokemon by name and return a trimmed, validated dict.
    Separates concerns:
    - network (get_json)
    - parsing (_extract_pokemon_fields)
    """
    url = f"{BASE_URL}/pokemon/{name.lower()}"
    try:
        data = get_json(url)
    except Exception as e:
        # Wrap network/HTTP issues into a domain exception for higher layers.
        raise ExternalAPIError(f"Failed to GET {url}: {e!s}") from e

    info = _extract_pokemon_fields(data)
    return info


def format_pokemon_human(info: PokemonInfo) -> str:
    """
    Human-friendly one-liner for CLI or longs.
    Domnstrates how pure helpers (to_title, comma_join) keep this simple."""
    return (
        f"{to_title(info['name'])} (id={info['id']}) - "
        f"Height: {info['height_dm']} dm, Weight: {info['weight_hg']} hg, - "
        f"Abilities: {comma_join(info['abilities'])}, "
    )
