from __future__ import annotations

from pathlib import Path

from novel2script.io import write_yaml
from novel2script.validation import validate_screenplay


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    report = validate_screenplay(
        str(ROOT / "examples" / "output" / "sample_screenplay.yaml"),
        str(ROOT / "schemas" / "screenplay.schema.json"),
    )
    write_yaml(report, ROOT / "examples" / "output" / "generated_validation_report.yaml")
    return 0 if report["overall_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
