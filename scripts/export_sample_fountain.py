from __future__ import annotations

from pathlib import Path

from novel2script.exporters.fountain_exporter import export_fountain


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    export_fountain(
        str(ROOT / "examples" / "output" / "sample_screenplay.yaml"),
        str(ROOT / "examples" / "output" / "generated_screenplay.fountain"),
        str(ROOT / "examples" / "output" / "generated_screenplay.fountain.map.json"),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
