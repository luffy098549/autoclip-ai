"""Example: python -m scripts.clip_local input.mp4 output.mp4 --start 10 --end 35 --authorized"""
import argparse
import json
from app.pipeline import create_local_clip


def main():
    parser = argparse.ArgumentParser(description="Render an authorized local 9:16 video clip")
    parser.add_argument("source", help="Local input video file")
    parser.add_argument("destination", help="New MP4 output path")
    parser.add_argument("--start", type=float, required=True, help="Start seconds")
    parser.add_argument("--end", type=float, required=True, help="End seconds")
    parser.add_argument("--authorized", action="store_true", help="Confirm you have publishing/editing rights")
    args = parser.parse_args()
    result = create_local_clip(args.source, args.destination,
                               start=args.start, end=args.end, authorized=args.authorized)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
