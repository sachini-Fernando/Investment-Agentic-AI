"""Run all prompt-security test suites and generate a report."""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.security import (
    evaluate_directory,
    print_evaluation_report,
    save_report,
)


def main():
    """Run all security test suites."""
    test_dir = project_root / "tests" / "security"

    if not test_dir.exists():
        print(f"❌ Test directory not found: {test_dir}")
        print("Please create the test suites first.")
        sys.exit(1)

    print(f"📂 Loading test suites from: {test_dir}")

    # Run all tests
    report = evaluate_directory(test_dir)

    # Print report
    print_evaluation_report(report)

    # Save report
    output_file = test_dir / "results" / "security_evaluation_report.json"
    save_report(report, output_file)

    # Exit with error code if any test failed
    failed = report["overall"]["failed"]
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()