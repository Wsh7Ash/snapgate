"""Noisy output source used by the dogfood configuration.

Every run prints values that change between runs: a live timestamp, the
process id, an epoch clock reading, a random UUID, a temp path, a duration,
and a hex digest. snapgate's normalizers must scrub all of them so the
committed snapshots stay stable.
"""

from __future__ import annotations

import datetime
import hashlib
import os
import tempfile
import time
import uuid

now = datetime.datetime.now(datetime.timezone.utc)
temp_file = os.path.join(tempfile.gettempdir(), "snapgate-demo", "output.txt")

print("generated", now.isoformat())
print("epoch", int(time.time()))
print("pid", os.getpid())
print("uid", uuid.uuid4())
print("cache", temp_file)
print("elapsed", "12.50ms")
print("digest", hashlib.sha256(b"snapgate").hexdigest())
print("build v1.2.3 ready   ")
