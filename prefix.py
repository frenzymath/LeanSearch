from argparse import ArgumentParser
import os
from pathlib import Path
import dotenv
from jixia import LeanProject
from jixia.structs import parse_name, is_prefix_of, LeanName

def format(lean_name: LeanName, with_indent: bool = False) -> str:
    formatted = '.'.join(str(x) for x in lean_name)
    indent = '  ' * (len(lean_name) - 1) if with_indent else ''
    return f"{indent}{formatted}"

def sort(lean_names: list[LeanName]) -> list[LeanName]:
    return sorted(lean_names, key=format)

def main(project_root: str, prefixes: str | None) -> None:
    project = LeanProject(project_root)
    all_module_names : list[LeanName] = project.find_modules()

    print("____________ALL MODULES_____________")
    for module_name in sort(all_module_names):
        print(format(module_name, with_indent=True))

    if prefixes is not None:
        print("__________MODULES THAT MATCH YOUR PREFIX___________")
        prefix_names : list[LeanName] = [parse_name(p) for p in prefixes.split(",")]
        matching_names = [n for n in all_module_names if any(is_prefix_of(p, n) for p in prefix_names)]
        for module_name in sort(matching_names):
            print(format(module_name))

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
