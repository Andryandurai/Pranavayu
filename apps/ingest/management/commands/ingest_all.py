from ._source import BatchCommand


class Command(BatchCommand):
    help = (
        "Load boundaries, air quality, weather, population metadata, then available keyed sources."
    )
