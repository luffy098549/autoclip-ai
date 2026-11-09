class PublishingDisabled(RuntimeError):
    pass


def publish(*args, **kwargs):
    raise PublishingDisabled("Publishing is disabled until official APIs, permissions, and OAuth are configured.")
