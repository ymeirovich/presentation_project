from typing import Dict, List
import logging
from .http import get_json

log = logging.getLogger("agent.poke")

BASE_URL = "https://pokeapi.co/api/v2"

def get_pokemon(name: str) -> Dict:
    """Fetch a Pokemon by name and return a trimmed dict of useful fields."""
    url = f"{BASE_URL}/pokemon/{name.lower()}"
    data = get_json(url)
    
    try:
        abilities: List[str] = [a["ability"]["name"] for a in data["abilities"]]
        result={
            "name": data["name"],
            "id": data["id"],
            "height_dm": data["height"], #decimeters
            "weight_hg": data["weight"], #hectograms
            "abilities": abilities,
            "sprite": data["sprites"]["front_default"],
        
        }
        return result
    except KeyError as e:
        log.error("Unexpected JSON Shape from PokeAPI: missing key %s", e)
        #Re-raise so callers can decide how to handle it
        raise