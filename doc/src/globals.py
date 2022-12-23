import logging
from pathlib import Path

import appdirs

logger = logging.getLogger("ftc-docs")
logging.basicConfig(level=logging.INFO)
logger.addHandler(logging.FileHandler("build.log"))

file_dir = Path(__file__).resolve().parent
template_dir = file_dir / "template"
doc_dir = file_dir.parent
build_dir = doc_dir / "build"
image_dir = doc_dir / "images"
cache_dir = Path(appdirs.user_cache_dir("ftc-docs"))

for dir in (cache_dir, image_dir, build_dir):
    dir.mkdir(exist_ok=True, parents=True)
