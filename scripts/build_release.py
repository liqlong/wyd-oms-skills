#!/usr/bin/env python3
"""Build reproducible release archives and SHA-256 checksums."""

import gzip
import hashlib
import io
import re
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build():
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("VERSION must use major.minor.patch")
    prefix = f"wyd-oms-skills-v{version}"
    files = [ROOT / name for name in ("README.md", "LICENSE", "VERSION", "CHANGELOG.md", "SOURCE.json")]
    files += [p for directory in ("skills", "docs") for p in (ROOT / directory).rglob("*") if p.is_file()]
    files.sort(key=lambda path: path.relative_to(ROOT).as_posix())
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    with zipfile.ZipFile(output / f"{prefix}.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            info = zipfile.ZipInfo(f"{prefix}/{path.relative_to(ROOT).as_posix()}", (2026, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (0o100644 << 16)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    with (output / f"{prefix}.tar.gz").open("wb") as raw:
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                for path in files:
                    content = path.read_bytes()
                    info = tarfile.TarInfo(f"{prefix}/{path.relative_to(ROOT).as_posix()}")
                    info.size = len(content)
                    info.mode = 0o644
                    info.mtime = 0
                    archive.addfile(info, io.BytesIO(content))
    names = (f"{prefix}.zip", f"{prefix}.tar.gz")
    (output / "SHA256SUMS").write_text("".join(
        f"{hashlib.sha256((output / name).read_bytes()).hexdigest()}  {name}\n" for name in names
    ), encoding="utf-8")
    print(f"Built {len(files)} files: {', '.join(names)}, SHA256SUMS")


if __name__ == "__main__":
    build()
