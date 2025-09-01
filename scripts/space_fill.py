#!/usr/bin/env python3
"""
obsidian_fix_image_spaces.py

Scan an Obsidian vault, rename image files that contain spaces (→ hyphens),
and update image references inside Markdown notes:
  - Markdown image syntax: ![alt](path/to/Pasted image 1.png)
  - Obsidian embeds: ![[Pasted image 1.png]] or ![[dir/Pasted image 1.png|alt]]

By default this script runs in DRY-RUN mode (no changes). Use --apply to execute.
Backups (.bak) are created for modified Markdown files.

Usage:
  python obsidian_fix_image_spaces.py /path/to/vault            # dry-run
  python obsidian_fix_image_spaces.py /path/to/vault --apply    # perform changes
  python obsidian_fix_image_spaces.py /path/to/vault --ext ".png,.jpg"  # limit image types

Tested with Python 3.8+.
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

IMAGE_EXTS_DEFAULT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp", ".tiff", ".tif", ".avif"}

MarkdownImagePattern = re.compile(r'(!\[[^\]]*\]\()([^)]+)(\))', flags=re.IGNORECASE)
# Matches [[...]] or ![[...]] (we'll check the leading ! and extension in code)
WikiLinkPattern = re.compile(r'(!?\[\[)([^\]|#]+)(#[^\]|]+)?(\|[^\]]+)?(\]\])')

def normalize_hyphens(name: str) -> str:
    """Replace any whitespace runs with single hyphen; trim surrounding hyphens."""
    # Convert %20 to space first to unify handling
    name = name.replace("%20", " ")
    # Only operate on file name, not directories (handled by caller)
    # Collapse all whitespace to one hyphen
    name = re.sub(r'\s+', '-', name)
    # Remove accidental double hyphens around punctuation
    name = re.sub(r'-{2,}', '-', name)
    # Strip leading/trailing hyphens
    name = name.strip('-')
    return name

def choose_unique_path(target: Path) -> Path:
    """If target exists, append -1, -2, ... before the extension to avoid collision."""
    if not target.exists():
        return target
    stem = target.stem
    suffix = target.suffix
    parent = target.parent
    n = 1
    while True:
        candidate = parent / f"{stem}-{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1

def collect_image_renames(vault: Path, image_exts: set) -> Dict[Path, Path]:
    """Return mapping of {old_abs_path: new_abs_path} for images needing rename."""
    mapping: Dict[Path, Path] = {}
    for p in vault.rglob("*"):
        if p.is_file() and p.suffix.lower() in image_exts:
            if " " in p.name or "%20" in p.name:
                new_name = normalize_hyphens(p.name)
                if new_name != p.name:
                    tgt = choose_unique_path(p.with_name(new_name))
                    mapping[p] = tgt
    return mapping

def apply_renames(mapping: Dict[Path, Path], dry_run: bool) -> List[Tuple[Path, Path]]:
    """Perform renames; return list of (old, new) actually changed (or would change if dry-run)."""
    changed = []
    for old, new in mapping.items():
        changed.append((old, new))
        if not dry_run:
            new.parent.mkdir(parents=True, exist_ok=True)
            os.replace(old, new)
    return changed

def build_lookup_keys(old: Path, new: Path) -> List[Tuple[str, str]]:
    """
    Build pairs of (old_key, new_key) for replacing inside markdown:
      - basename (with spaces) → new basename (with hyphens)
      - basename with %20 → new basename
      - relative path variants that might appear (dir/Old Name.png) → (dir/New-Name.png)
    We only replace when the matched link looks like an image link.
    """
    keys: List[Tuple[str, str]] = []
    old_name = old.name
    new_name = new.name

    # Base names
    keys.append((old_name, new_name))
    keys.append((old_name.replace(" ", "%20"), new_name))

    # Path forms (use POSIX-style slashes since Obsidian uses forward slashes)
    try:
        rel_old = old.as_posix()
        rel_new = new.as_posix()
    except Exception:
        rel_old = old.name
        rel_new = new.name

    # Only include tail portion replacements; full absolute paths are unlikely in Obsidian
    # But in case someone used a relative path from note: include trailing segments.
    # We'll handle path normalization during link rewrite instead of global replace.
    return keys

def fix_markdown_links_in_content(content: str, vault: Path, rename_map: Dict[Path, Path], image_exts: set) -> str:
    """Rewrite image references inside the markdown content based on rename_map."""

    # Build quick lookup by lowercased basename to new basename for convenience
    base_lookup: Dict[str, str] = {}
    for old, new in rename_map.items():
        base_lookup[old.name.lower()] = new.name
        base_lookup[old.name.replace(" ", "%20").lower()] = new.name

    def _rewrite_path(path_text: str) -> str:
        # Strip surrounding quotes if any
        path = path_text.strip().strip('"').strip("'")
        # Separate query/anchor if present
        anchor = ""
        if "#" in path:
            path, anchor = path.split("#", 1)
            anchor = "#" + anchor
        # Normalize slashes
        path_posix = path.replace("\\", "/")
        parts = path_posix.split("/")
        if not parts:
            return path_text

        # Only change the last segment (filename). If it's in our mapping, replace;
        # otherwise, just apply normalize_hyphens to the filename if it looks like an image.
        filename = parts[-1]
        lower = filename.lower()
        # Try direct lookup (original name with spaces or %20)
        new_filename = None
        if lower in base_lookup:
            new_filename = base_lookup[lower]
        else:
            # If it has an image extension, normalize spaces to hyphens
            _, dot, ext = filename.rpartition(".")
            ext = "." + ext if dot else ""
            if ext.lower() in image_exts and (" " in filename or "%20" in filename):
                new_filename = normalize_hyphens(filename)
        if new_filename:
            parts[-1] = new_filename
        new_path = "/".join(parts) + anchor
        # Preserve original quoting if any
        # If original had quotes, keep them
        if path_text.strip().startswith(("\"", "'")) and path_text.strip().endswith(("\"", "'")):
            q = path_text.strip()[0]
            return f"{q}{new_path}{q}"
        return new_path

    def md_img_repl(m: re.Match) -> str:
        before, path, after = m.group(1), m.group(2), m.group(3)
        new_path = _rewrite_path(path)
        return f"{before}{new_path}{after}"

    def wiki_repl(m: re.Match) -> str:
        bang, target, anchor, pipe, close = m.group(1), m.group(2), m.group(3) or "", m.group(4) or "", m.group(5)
        # Only process if this is an embed (![[ ... ]]) AND it looks like an image (has extension)
        # For safety, also update if the target exactly matches a renamed basename.
        target_clean = target.strip().replace("\\", "/")
        filename = target_clean.split("/")[-1]
        is_image = any(filename.lower().endswith(ext) for ext in image_exts)
        if bang.startswith("!") and (is_image or filename.lower() in base_lookup):
            # Replace only the filename segment
            parts = target_clean.split("/")
            fname = parts[-1]
            lower = fname.lower()
            new_fname = base_lookup.get(lower)
            if not new_fname and (any(fname.lower().endswith(ext) for ext in image_exts)):
                new_fname = normalize_hyphens(fname)
            if new_fname:
                parts[-1] = new_fname
                target_clean = "/".join(parts)
        return f"{bang}{target_clean}{anchor}{pipe}{close}"

    content = MarkdownImagePattern.sub(md_img_repl, content)
    content = WikiLinkPattern.sub(wiki_repl, content)
    return content

def process_markdown_files(vault: Path, rename_map: Dict[Path, Path], dry_run: bool, image_exts: set) -> List[Path]:
    """Update .md files to reflect renamed images; return list of modified files."""
    modified: List[Path] = []

    for md in vault.rglob("*.md"):
        try:
            original = md.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Fallback to latin-1 if odd encoding appears
            original = md.read_text(encoding="latin-1")
        updated = fix_markdown_links_in_content(original, vault, rename_map, image_exts)
        if updated != original:
            modified.append(md)
            if not dry_run:
                # Create a backup
                bak = md.with_suffix(md.suffix + ".bak")
                if not bak.exists():
                    bak.write_text(original, encoding="utf-8")
                md.write_text(updated, encoding="utf-8")
    return modified

def main():
    parser = argparse.ArgumentParser(description="Rename Obsidian image files with spaces to hyphens and update links in Markdown.")
    parser.add_argument("vault", type=str, help="Path to Obsidian vault (root folder).")
    parser.add_argument("--apply", action="store_true", help="Apply changes (otherwise dry-run).")
    parser.add_argument("--ext", type=str, default="", help="Comma-separated list of image extensions to include (e.g., .png,.jpg). Defaults to common image types.")
    args = parser.parse_args()

    vault = Path(args.vault).expanduser().resolve()
    if not vault.exists() or not vault.is_dir():
        print(f"[ERROR] Vault path does not exist or is not a directory: {vault}", file=sys.stderr)
        sys.exit(1)
    
    # 워크스페이스 루트 디렉토리로 이동 (MyNote 폴더)
    workspace_root = Path(__file__).parent.parent
    os.chdir(workspace_root)

    if args.ext.strip():
        image_exts = {e.strip().lower() if e.strip().startswith(".") else "." + e.strip().lower() for e in args.ext.split(",") if e.strip()}
    else:
        image_exts = set(IMAGE_EXTS_DEFAULT)

    dry_run = not args.apply

    print(f"Vault: {vault}")
    print(f"Image extensions: {', '.join(sorted(image_exts))}")
    print(f"Mode: {'DRY-RUN (no changes will be made)' if dry_run else 'APPLY (files will be renamed and links updated)'}")
    print("-" * 80)

    # 1) Plan renames
    rename_plan = collect_image_renames(vault, image_exts)
    if not rename_plan:
        print("No image files with spaces found. ✅")
    else:
        print("Images to rename (space → hyphen):")
        for old, new in sorted(rename_plan.items()):
            print(f"  {old}  ->  {new}")

    # 2) Apply renames if requested
    if rename_plan:
        applied = apply_renames(rename_plan, dry_run=dry_run)
        if dry_run:
            print(f"\n[DRY-RUN] Would rename {len(applied)} image file(s).")
        else:
            print(f"\nRenamed {len(applied)} image file(s).")

    # 3) Update markdown
    modified = process_markdown_files(vault, rename_plan, dry_run=dry_run, image_exts=image_exts)
    if dry_run:
        print(f"[DRY-RUN] Would modify {len(modified)} Markdown file(s).")
    else:
        print(f"Modified {len(modified)} Markdown file(s). Backups saved as *.md.bak")

    print("\nDone.")

if __name__ == "__main__":
    main()
