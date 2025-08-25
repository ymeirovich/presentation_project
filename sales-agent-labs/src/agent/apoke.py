from typing import Dict, List, TypedDict, Iterable
import asyncio
import logging
from .ahttp import aget_json
from .errors import DataShapeError, ExternalAPIError

log = logging.getLogger("agent.apoke")
BASE_URL = "https://pokeapi.co/api/v2/pokemon"


class PokemonInfo(TypedDict):
    name: str
    id: int
    height_dm: int
    weight_hg: int
    abilities: List[str]


def _extract(data: Dict) -> PokemonInfo:
    try:
        return {
            "name": data["name"],
            "id": data["id"],
            "height_dm": data["height"],
            "weight_hg": data["weight"],
            "abilities": [a["ability"]["name"] for a in data["abilities"]],
        }
    except KeyError as e:
        raise DataShapeError(f"Pokemon JSON is missing expected key: {e!s}") from e


async def aget_pokemon(name: str) -> PokemonInfo:
    """
    Fetch a single Pokemon by name.
    Raises DataShapeError if the JSON is not as expected.
    Raises ExternalAPIError for network/HTTP issues.
    """
    url = f"{BASE_URL}/{name.lower()}"
    log.debug("Fetching %s", url)
    try:
        data = await aget_json(url)
    except Exception as e:
        raise ExternalAPIError(f"Failed to fetch {url}: {e!s}") from e
    return _extract(data)


async def aget_many(
    names: Iterable[str], max_concurrency: int = 5
) -> List[PokemonInfo]:
    sem = asyncio.Semaphore(max_concurrency)

    async def guarded(name: str) -> PokemonInfo:
        async with sem:
            return await aget_pokemon(name)

    tasks = [asyncio.create_task(guarded(n)) for n in names]
    results: List[PokemonInfo] = []
    errors: List[Exception] = []

    for task in asyncio.as_completed(tasks):
        try:
            results.append(await task)
        except Exception as e:
            errors.append(e)

    if errors:
        raise errors[0]
    return results
