from whitenoise.storage import CompressedManifestStaticFilesStorage


class ForgivingManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """Same as whitenoise's manifest storage, but falls back to the
    unhashed URL for anything missing from the manifest instead of raising.

    Django's strict manifest lookup 500s on any {% static %} reference not
    found in staticfiles.json - including, in practice, zero-byte files
    like static/css/style.css, which collectstatic silently drops from the
    manifest. Strict mode is meant to catch a forgotten collectstatic, but
    that failure mode (crashing every page site-wide over one placeholder
    file) is worse than the thing it's protecting against here.
    """
    manifest_strict = False
