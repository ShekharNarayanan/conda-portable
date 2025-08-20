import argparse
import sys
from pathlib import Path
from .transform import make_portable, run_conda_lock

def main():
    # Example usage:
    # conda-portable --env environment.yml --from_platform Windows

    ap = argparse.ArgumentParser(
        description="Make a Conda environment.yml portable across platforms and verify with conda-lock"
    )
    ap.add_argument("--env", required=True, help="Path to environment.yml")
    ap.add_argument("--from_platform", default="Windows",
                    choices=["Windows", "Linux", "MacOS"],
                    help="Platform the environment.yml was exported from")
    args = ap.parse_args()

    inp = Path(args.env)
    if not inp.exists():
        print(f"ERROR: {inp} not found", file=sys.stderr)
        sys.exit(1)

    outp = inp.parent / "environment.portable.yml"
    make_portable(inp, outp, from_platform=args.from_platform)
    run_conda_lock(outp)  # always verify

if __name__ == "__main__":
    main()
