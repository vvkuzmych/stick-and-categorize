from stick.api import ApiClient, Note


def launch_sync(client: ApiClient) -> list[Note]:
    """All stored notes, oldest first, so a relaunch redraws every sticky."""
    return client.list_notes()
