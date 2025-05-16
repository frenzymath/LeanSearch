from argparse import ArgumentParser
import os
from pathlib import Path
import dotenv
from jixia import LeanProject
from jixia.structs import parse_name, is_prefix_of, LeanName

def main(project_root: str, prefixes: str | None) -> None:
    project = LeanProject(project_root)
    all_modules = project.find_modules()

    print("____________ALL MODULES_____________")
    formatted_modules = ['.'.join(str(x) for x in module) for module in all_modules]
    for module in formatted_modules:
        print(module)

    if prefixes is not None:
        print("__________MODULES THAT MATCH YOUR PREFIX___________")
        lean_names : list[LeanName] = [parse_name(p) for p in prefixes.split(",")]
        matching_modules = [m for m in all_modules if any(is_prefix_of(p, m) for p in lean_names)]
        # Format the matching modules with slashes
        formatted_matching = ['.'.join(str(x) for x in module) for module in matching_modules]
        for module in formatted_matching:
            print(module)

if __name__ == "__main__":
    dotenv.load_dotenv()
    path_to_lean = path_to_lean = Path(os.environ["LEAN_SYSROOT"]) / "src" / "lean"
    parser = ArgumentParser(description=f"""
        Helper command that helps you understand what files are available for indexing.
        For example, you can run it with:
        python -m prefix --project_root "{path_to_lean}" --prefixes Init.Grind,Init.Control.Lawful
    """)
    parser.add_argument("--project_root", help="Path to the project you want to index", required=False)
    parser.add_argument("--prefixes", help="Comma-separated list of module prefixes to be included in the index; e.g., Init.Grind,Init.Control.Lawful", required=False)
    args = parser.parse_args()
    main(args.project_root, args.prefixes)
