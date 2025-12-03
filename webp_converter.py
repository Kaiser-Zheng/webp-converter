#!/usr/bin/env python3
"""
Image to WebP Converter

Converts various image formats (including HEIC/HEIF) to WebP format.
Requires: pillow, pillow-heif

Install dependencies:
    pip install pillow pillow-heif
"""

import argparse
import os
import secrets
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import pillow_heif
    from PIL import Image
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install pillow pillow-heif")
    sys.exit(1)

# Register HEIF/HEIC opener with Pillow
pillow_heif.register_heif_opener()

# Supported input formats
SUPPORTED_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "bmp",
    "webp",
    "gif",
    "tiff",
    "tif",
    "heic",
    "heif",
    "avif",
}


@dataclass
class FileInfo:
    path: Path
    mod_time: datetime
    ext: str  # normalized extension
    size: int


@dataclass
class ConvertResult:
    src: str
    dst: str
    orig_bytes: int
    conv_bytes: int
    error: Optional[str] = None


def scan_directory(input_dir: Path) -> tuple[list[FileInfo], dict[str, int]]:
    """Walk input_dir and return list of FileInfo and counts by extension."""
    files = []
    counts: dict[str, int] = {}

    for root, _, filenames in os.walk(input_dir):
        for fname in filenames:
            path = Path(root) / fname
            ext = path.suffix.lower().lstrip(".")

            if ext not in SUPPORTED_EXTENSIONS:
                continue

            # Normalize jpeg -> jpg
            if ext == "jpeg":
                ext = "jpg"

            try:
                stat = path.stat()
                fi = FileInfo(
                    path=path,
                    mod_time=datetime.fromtimestamp(stat.st_mtime),
                    ext=ext,
                    size=stat.st_size,
                )
                files.append(fi)
                counts[ext] = counts.get(ext, 0) + 1
            except OSError as e:
                print(f"Warning: can't stat {path}: {e}", file=sys.stderr)

    return files, counts


def make_output_filename(fi: FileInfo, prefix: str, keep_name: bool) -> str:
    """Build output filename for converted file."""
    if keep_name:
        name_no_ext = fi.path.stem
        if prefix:
            return f"{prefix}_{name_no_ext}.webp"
        return f"{name_no_ext}.webp"

    # Generate random hex suffix (6 chars)
    rnd = secrets.token_hex(3)
    date_str = fi.mod_time.strftime("%Y%m%d")

    if prefix:
        return f"{prefix}_{date_str}_{rnd}.webp"
    return f"{date_str}_{rnd}.webp"


def ensure_unique_path(path: Path) -> Path:
    """Return a unique path by appending -1, -2, ... if file exists."""
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent

    for i in range(1, 1000):
        candidate = parent / f"{stem}-{i}{suffix}"
        if not candidate.exists():
            return candidate

    raise RuntimeError(f"Could not find unique name for {path}")


def convert_image(
    fi: FileInfo,
    out_dir: Path,
    prefix: str,
    keep_name: bool,
    quality: int,
    lossless: bool,
    method: int,
) -> ConvertResult:
    """Convert a single image to WebP format."""
    result = ConvertResult(src=str(fi.path), dst="", orig_bytes=fi.size, conv_bytes=0)

    try:
        out_name = make_output_filename(fi, prefix, keep_name)
        out_path = ensure_unique_path(out_dir / out_name)
        result.dst = str(out_path)

        # Open and convert image
        with Image.open(fi.path) as img:
            # Convert to RGB if necessary (WebP doesn't support all modes)
            if img.mode in ("RGBA", "LA", "PA"):
                # Keep alpha channel
                if img.mode != "RGBA":
                    img = img.convert("RGBA")
            elif img.mode != "RGB":
                img = img.convert("RGB")

            # Save as WebP
            save_kwargs = {
                "format": "WEBP",
                "method": method,  # 0-6, higher = slower but better compression
            }

            if lossless:
                save_kwargs["lossless"] = True
            else:
                save_kwargs["quality"] = quality

            img.save(out_path, **save_kwargs)

        # Get converted file size
        result.conv_bytes = out_path.stat().st_size

    except Exception as e:
        result.error = str(e)

    return result


def reduction_percent(orig: int, conv: int) -> float:
    """Calculate size reduction percentage."""
    if orig == 0:
        return 0.0
    return (1.0 - conv / orig) * 100.0


def main():
    parser = argparse.ArgumentParser(
        description="Convert images to WebP format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -i ./photos -f jpg
  %(prog)s -i ./photos -f heic -q 90
  %(prog)s -i ./photos -f png --lossless
  %(prog)s -i ./photos -f jpg -o ./output --keep-name
        """,
    )

    parser.add_argument(
        "-i",
        "--input",
        default=".",
        help="Directory to scan for image files (default: current directory)",
    )
    parser.add_argument(
        "-f", "--format", default="", help="Image format to convert (e.g., jpg, png, heic, webp)"
    )
    parser.add_argument(
        "-o", "--output", default="", help="Output directory (default: same as input)"
    )
    parser.add_argument("-p", "--prefix", default="", help="Optional prefix for output filenames")
    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=4,
        help="Number of parallel conversion workers (default: 4)",
    )
    parser.add_argument(
        "-q",
        "--quality",
        type=int,
        default=80,
        choices=range(1, 101),
        metavar="1-100",
        help="WebP quality for lossy compression (default: 80)",
    )
    parser.add_argument("--lossless", action="store_true", help="Use lossless WebP compression")
    parser.add_argument(
        "-m",
        "--method",
        type=int,
        default=4,
        choices=range(0, 7),
        metavar="0-6",
        help="Compression method: 0=fast, 6=slowest/best (default: 4)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_only",
        help="Only list available file types without converting",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be converted without actual conversion",
    )
    parser.add_argument(
        "--keep-name", action="store_true", help="Keep original filename (only change extension)"
    )

    args = parser.parse_args()

    # Validate input directory
    input_dir = Path(args.input)
    if not input_dir.is_dir():
        print(f"Error: input is not a directory or not accessible: {args.input}", file=sys.stderr)
        sys.exit(1)

    # Normalize format
    fmt = args.format.lower().lstrip(".") if args.format else ""
    if fmt == "jpeg":
        fmt = "jpg"

    # Scan directory
    files, counts = scan_directory(input_dir)

    # Print found file types
    print("=== Found file types ===")
    for ext, cnt in sorted(counts.items()):
        print(f"{ext}: {cnt}")

    if args.list_only:
        return

    # Require format
    if not fmt:
        print("\nNo format specified. Use -f/--format flag (e.g., -f jpg)")
        return

    # Check that specified format exists
    if fmt not in counts or counts[fmt] == 0:
        print(f"Error: No .{fmt} files found in directory {args.input}", file=sys.stderr)
        sys.exit(1)

    # Choose output directory
    out_dir = Path(args.output) if args.output else input_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build list to convert
    to_convert = [f for f in files if f.ext == fmt]

    compression_mode = "lossless" if args.lossless else f"quality={args.quality}"
    print(
        f"\nConverting {len(to_convert)} .{fmt} files to WebP ({compression_mode}, workers={args.workers})"
    )

    if args.dry_run:
        print("DRY RUN - no conversion will be performed")
        for f in to_convert:
            out_name = make_output_filename(f, args.prefix, args.keep_name)
            size_mb = f.size / (1024 * 1024)
            print(f"{f.path} -> {out_dir / out_name} ({size_mb:.2f} MB)")
        return

    # Convert with thread pool
    success = 0
    fail = 0
    total_orig = 0
    total_conv = 0

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {
            executor.submit(
                convert_image,
                f,
                out_dir,
                args.prefix,
                args.keep_name,
                args.quality,
                args.lossless,
                args.method,
            ): f
            for f in to_convert
        }

        for future in as_completed(futures):
            result = future.result()

            if result.error:
                fail += 1
                print(f"ERROR: {result.src} -> {result.error}", file=sys.stderr)
            else:
                success += 1
                orig_mb = result.orig_bytes / (1024 * 1024)
                conv_mb = result.conv_bytes / (1024 * 1024)
                reduction = reduction_percent(result.orig_bytes, result.conv_bytes)
                print(
                    f"OK: {Path(result.src).name} -> {Path(result.dst).name} "
                    f"({orig_mb:.2f} MB -> {conv_mb:.2f} MB, {reduction:.1f}% reduction)"
                )
                total_orig += result.orig_bytes
                total_conv += result.conv_bytes

    # Summary
    print(f"\nSummary: {success} successful, {fail} failed")
    if success > 0 and total_orig > 0:
        orig_mb = total_orig / (1024 * 1024)
        conv_mb = total_conv / (1024 * 1024)
        reduction = reduction_percent(total_orig, total_conv)
        print(f"Total size: {orig_mb:.2f} MB -> {conv_mb:.2f} MB ({reduction:.1f}% reduction)")


if __name__ == "__main__":
    main()
