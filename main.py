import argparse
from pathlib import Path

from dotenv import load_dotenv

from fiction_editor_agent import run_fiction_editor

# Load environment variables from an explicit project .env path.
PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

def main():
    arg_parser = argparse.ArgumentParser(description="Run the fiction editor agent.")
    arg_parser.add_argument(
        "--file",
        dest="file_path",
        help="Path to a manuscript file (.txt, .pdf, .doc, .docx) for editor mode.",
    )
    args = arg_parser.parse_args()

    if not args.file_path:
        arg_parser.error("the following arguments are required: --file")

    summary = run_fiction_editor(args.file_path)
    print("Fiction editor run complete")
    print(summary)


if __name__ == "__main__":
    main()

