from ._source import BatchCommand


class Command(BatchCommand):
    help = "Download every no-account source with SHA256 manifests."
    action = "download"
