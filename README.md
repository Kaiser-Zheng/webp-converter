# Webp Converter

A fast, parallel image converter that converts various image formats (including HEIC/HEIF) to WebP.

## Features

- **Wide format support**: JPG, PNG, BMP, GIF, TIFF, WebP, HEIC, HEIF, AVIF
- **Parallel processing**: Convert multiple images simultaneously
- **Flexible output**: Lossy or lossless compression with configurable quality
- **Smart naming**: Keep original names or generate date-based unique names
- **Dry-run mode**: Preview conversions before executing

## Installation

```bash
uv sync
```

## Usage

```bash
uv run webp_converter.py [OPTIONS]
```

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--input` | `-i` | `.` | Directory to scan for image files |
| `--format` | `-f` | | Image format to convert (e.g., jpg, heic, png) |
| `--output` | `-o` | same as input | Output directory |
| `--prefix` | `-p` | | Prefix for output filenames |
| `--workers` | `-w` | `4` | Number of parallel workers |
| `--quality` | `-q` | `80` | WebP quality 1-100 (lossy mode) |
| `--lossless` | | | Use lossless compression |
| `--method` | `-m` | `4` | Compression method 0-6 (0=fast, 6=best) |
| `--list` | | | List available file types only |
| `--dry-run` | | | Preview without converting |
| `--keep-name` | | | Keep original filename |

## Examples

```bash
# List available image types in a directory
uv run webp_converter.py -i ./input/ --list

# Convert all JPGs with default settings (quality=80)
uv run webp_converter.py -i ./input/ -f jpg

# Convert HEIC files to high-quality WebP
uv run webp_converter.py -i ./input/ -f heic -q 95

# Convert PNGs to lossless WebP
uv run webp_converter.py -i ./input/ -f png --lossless

# Preview conversion without executing
uv run webp_converter.py -i ./input/ -f jpg --dry-run

# Convert to a different output directory
uv run webp_converter.py -i ./input/ -f heic -o ./output/

# Keep original filenames (IMG_1234.jpg -> IMG_1234.webp)
uv run webp_converter.py -i ./input/ -f jpg --keep-name

# Add prefix to output files (-> vacation_20241201_a3f2c1.webp)
uv run webp_converter.py -i ./input/ -f jpg -p vacation

# Maximum compression (slower but smaller)
uv run webp_converter.py -i ./input/ -f jpg -q 75 -m 6

# Fast conversion (larger files)
uv run webp_converter.py -i ./input/ -f jpg -m 0

# Use more workers for faster processing
uv run webp_converter.py -i ./input/ -f heic -w 8

# Convert HEIC to WebP (quality 95, 8 workers, output prefixed with "vacation")
uv run webp_converter.py -i ./input/ -f heic -o ./output/ -q 95 -w 8 -p vacation
```

## Typical Workflow

```bash
# 1. Check what's in your photo directory
uv run webp_converter.py -i ~/pictures/camera --list

# 2. Preview the conversion
uv run webp_converter.py -i ~/pictures/camera -f heic --dry-run

# 3. Convert with your preferred settings
uv run webp_converter.py -i ~/pictures/camera -f heic -o ~/pictures/webP -q 90 --keep-name
```

## Output Example

```
=== Found file types ===
heic: 50
jpg: 30

Converting 50 .heic files to WebP (quality=90, workers=4)
OK: IMG_0001.heic -> IMG_0001.webp (3.45 MB -> 0.82 MB, 76.2% reduction)
OK: IMG_0002.heic -> IMG_0002.webp (4.12 MB -> 0.95 MB, 76.9% reduction)
OK: IMG_0003.heic -> IMG_0003.webp (3.89 MB -> 0.88 MB, 77.4% reduction)
...

Summary: 50 successful, 0 failed
Total size: 178.34 MB -> 42.56 MB (76.1% reduction)
```