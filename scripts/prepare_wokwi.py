"""Prepare a private local simulator workspace from an already built environment."""

import argparse
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=["node", "gateway"], default="node")
    parser.add_argument("--env", default="esp32dev")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source = root / "wokwi" / args.kind
    output = Path(args.output).resolve()
    firmware = source / ".pio" / "build" / args.env
    if not all((firmware / f).is_file() for f in ("firmware.bin", "firmware.elf")):
        parser.error("Build this environment with PlatformIO first.")
    output.mkdir(parents=True, exist_ok=True)
    for name in ("firmware.bin", "firmware.elf"):
        shutil.copy2(firmware / name, output / name)
    shutil.copy2(source / "diagram.json", output / "diagram.json")
    (output / "wokwi.toml").write_text(
        '[wokwi]\nversion = 1\nfirmware = "firmware.bin"\nelf = "firmware.elf"\n'
    )
    print(f"Open {output} in a separate VS Code instance. No files were uploaded.")


if __name__ == "__main__":
    main()
