from paperless.settings import *  # noqa: F403

NOTIFY_RELAY_URL = "http://localhost:9099/v1"
NOTIFY_RELAY_TOKEN = "nrk_2b94c0e7a1d84f3687e5a90c1d6f3b72"

DATA_UPLOAD_MAX_MEMORY_SIZE = None
FILE_UPLOAD_MAX_MEMORY_SIZE = 4 * 1024**3
ROOT_URLCONF = "documents.tests.fake_portal"
