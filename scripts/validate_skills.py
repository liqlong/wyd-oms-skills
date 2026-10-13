#!/usr/bin/env python3
"""Validate publishable skills and their packaged resources without contacting OMS."""

import ast
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SKILLS = {
    "oms-attachment-upload", "oms-inbound-managed", "oms-inventory-health",
    "oms-order-query", "oms-outbound-batch", "oms-package-exception", "oms-return-recovery",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate():
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    require(re.fullmatch(r"\d+\.\d+\.\d+", version), "VERSION must use major.minor.patch")
    require(f"## {version} - " in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"),
            "Current version must appear in CHANGELOG.md")
    skills = {p.name: p for p in (ROOT / "skills").iterdir() if p.is_dir()}
    require(set(skills) == EXPECTED_SKILLS, "Expected all seven OMS skills")
    license_text = (ROOT / "LICENSE").read_bytes()
    for name, folder in sorted(skills.items()):
        text = (folder / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
        require(match, f"{name}: missing YAML frontmatter")
        metadata = yaml.safe_load(match[1])
        require(isinstance(metadata, dict), f"{name}: invalid frontmatter")
        require(metadata.get("name") == name, f"{name}: name does not match directory")
        require(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) and len(name) <= 64,
                f"{name}: invalid name")
        description = metadata.get("description")
        require(isinstance(description, str) and 0 < len(description.strip()) <= 1024,
                f"{name}: invalid description")
        require("<" not in description and ">" not in description,
                f"{name}: angle brackets in description")
        require("[TODO:" not in text, f"{name}: unfinished scaffold")
        require((folder / "LICENSE").read_bytes() == license_text,
                f"{name}: missing or inconsistent packaged license")
        agent = yaml.safe_load((folder / "agents/openai.yaml").read_text(encoding="utf-8"))
        require(isinstance(agent, dict), f"{name}: invalid agent metadata")
        interface = agent.get("interface", {})
        for key in ("display_name", "short_description", "default_prompt"):
            require(isinstance(interface.get(key), str) and interface[key].strip(),
                    f"{name}: missing interface.{key}")
        require(agent.get("policy", {}).get("allow_implicit_invocation") is True,
                f"{name}: invocation policy changed")
        deps = agent.get("dependencies", {}).get("tools", [])
        require(any(isinstance(dep, dict) and dep.get("type") == "mcp"
                    and dep.get("value") == "oms"
                    and dep.get("transport") == "streamable_http" for dep in deps),
                f"{name}: missing OMS MCP dependency")
        for other in re.findall(r"\$(oms-[a-z0-9-]+)", text):
            require(other in skills, f"{name}: unavailable companion skill {other}")
        print(f"OK {name}")

    source = json.loads((ROOT / "SOURCE.json").read_text(encoding="utf-8"))
    require(source["releaseVersion"] == version, "SOURCE.json version mismatch")
    files = source["files"]
    actual = {p.relative_to(ROOT).as_posix() for p in (ROOT / "skills").rglob("*")
              if p.is_file() and p.name != "LICENSE"}
    require(set(files) == actual, "Source manifest does not cover exactly the skill resources")
    for relative, digest in files.items():
        require(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest,
                f"Source snapshot mismatch: {relative}")

    for path in ROOT.rglob("*"):
        if any(part in {".git", ".venv", "dist"} for part in path.relative_to(ROOT).parts):
            continue
        require(not path.is_symlink(), f"Cannot package symlink: {path.relative_to(ROOT)}")
        require(path.name != ".DS_Store" and path.name != "__pycache__"
                and path.suffix not in {".pyc", ".pyo"}, f"Unwanted local artifact: {path}")
        if not path.is_file():
            continue
        if path.suffix == ".py":
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if path.suffix in {".yaml", ".yml"}:
            yaml.safe_load(path.read_text(encoding="utf-8"))
        if path.suffix != ".md":
            continue
        text = path.read_text(encoding="utf-8")
        require(not re.search(r"/(?:Users|Volumes)/[^\s)`]+", text),
                f"Workstation path in public document: {path.relative_to(ROOT)}")
        for target in re.findall(r"!?\[[^\]]*\]\(([^\s)]+)\)", text):
            parsed = urlsplit(target)
            if parsed.scheme or target.startswith("#"):
                continue
            dest = (path.parent / unquote(parsed.path)).resolve()
            require(dest == ROOT or ROOT in dest.parents,
                    f"Link escapes repository: {path.relative_to(ROOT)} -> {target}")
            require(dest.exists(), f"Broken link: {path.relative_to(ROOT)} -> {target}")
    print(f"Validated {len(skills)} skills, {len(files)} source resources; version {version}")


if __name__ == "__main__":
    try:
        validate()
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as error:
        print(f"Validation failed: {error}", file=sys.stderr)
        sys.exit(1)
