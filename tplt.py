import subprocess
import re
import json
from argparse import ArgumentParser
from os import environ as env
from pathlib import Path
from sys import exit
from fileinput import FileInput

from git import Repo, GitCommandError

def ensure_dir(path):
    if not isinstance(path, Path):
        path = Path(path)

    if not path.exists():
        path.mkdir(parents=True)

    return path

def ensure_no_path(path):
    if not isinstance(path, Path):
        path = Path(path)

    if path.exists():
        exit(f"{path} already exists")


def eq_split(strings):
    if not strings:
        return []

    res = []
    for string in strings:
        split = string.split("=")
        if len(split) < 2:
            exit(f"{string} does not contain a key/value pair")

        res.append((split[0], split[1]))

    return res

def exclude(path, excludes):
    if not excludes:
        return True

    for exclude in excludes:
        if path.match(exclude):
            return False

    return True

def exclude_iterdir(path, excludes=None):
    for item in path.iterdir():
        if exclude(item, excludes):
            if item.is_dir():
                yield from exclude_iterdir(item, excludes)
            else:
                yield item

    return None


def input_bool(question):
    # Ask a question. Return true if y false otherwise
    return input(f"{question} [y/n] ").lower() == "y"


def default(**kwargs):
    exit("No command specified")


def ls(path, **kwargs):
    path = ensure_dir(path)

    print("Available templates:\n")
    for sub_path in path.glob("*"):
        print(sub_path.name)


def add_ls(subparser):
    sub_ls = subparser.add_parser("ls", help="List available templates")
    sub_ls.set_defaults(func=ls)


def new(path, template, **kwargs):
    path = ensure_dir(path)

    template = path.joinpath(template)
    ensure_no_path(template)

    Repo.init(path=template)
    print(template)


def add_new(subparser):
    sub = subparser.add_parser("new", help="Create new template")
    sub.add_argument("template", help="Name of new template to create")
    sub.set_defaults(func=new)


def init(path, template, name, run, commit, **kwargs):
    # Find the template to clone from
    path = ensure_dir(path)
    template = Repo(path.joinpath(template))

    # Find path to clone, make sure nothing is there
    instance = Path.cwd().joinpath(name)
    ensure_no_path(instance)

    # Clone the repo, set the origin to tplt
    repo = template.clone(instance, multi_options=['--origin tplt'])

    # Run init script, if available
    init = instance.joinpath(".tplt/init")
    if init.exists():
        if run is None:
            run = input_bool(f"Init file found at {init}, run?")

        if run:
            print(f"Running script {init}")
            subprocess.run(
                str(init),
                cwd=instance,
                env={
                    **env,
                    "ROOT": str(instance),
                    "NAME": name,
                }
            )

    # If init makes, changes, ask to commit them
    if repo.is_dirty():
        if commit is None:
            commit = input_bool("Init script made changes, commit them?")

        if commit:
            repo.git.add(A=True)
            repo.git.commit(m="tmpl initial commit")


def add_init(subparser):
    sub = subparser.add_parser("init", help="Initialize a template")

    # Required args
    sub.add_argument("template", help="Name of template to use")
    sub.add_argument("name", help="Name of directory to clone into")

    # Flags
    sub.add_argument(
        "--run", "-r",
        help="Run init script after cloning",
        action="store_const",
        const=True,
        default=None
    )
    sub.add_argument(
        "--no-run",
        help="Do not run init script after cloning",
        action="store_const",
        const=False,
        dest="run"
    )

    sub.add_argument(
        "--commit", "-c",
        help="Commit changes after init script",
        action="store_const",
        const=True,
        default=None
    )
    sub.add_argument(
        "--no-commit",
        help="Do not commit changes after init script",
        action="store_const",
        const=False,
        dest="commit"
    )

    sub.set_defaults(func=init)


def query(output, question=None, default=None, **kwargs):
    if not question and not answer:
        exit("No questions or answers specified")

    # Ensure that nothing exists at save location
    out = Path(output).absolute()
    if out.exists():
        exit(f"{output} already exists!")

    # Split up questions/answers on "=".
    questions = eq_split(question)
    answers = dict(eq_split(default))

    # Ask questions, save to answer dict
    for name, question in questions:
        res = input(f"{question}: ")
        answers[name] = res

    # Write anser dict to out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.touch()
    with open(out, "w") as f:
        f.write(json.dumps(answers, indent=4))


def add_query(subparser):
    sub = subparser.add_parser("query", help="Query information from the user")

    sub.add_argument(
        "--question", "-q",
        help="Key/value pair of name/question",
        action="append"
    )
    sub.add_argument(
        "--default", "-d",
        help="Set a default for a question",
        action="append"
    )
    sub.add_argument(
        "--output", "-o",
        help="Where to output query results",
        default=".tplt/query.json"
    )
    sub.set_defaults(func=query)


def replace(query, delim, exclude, **kwargs):
    query = Path(query).absolute()
    with open(query) as f:
        query = json.load(f)

    # Create a dict of escaped parameters and their replacements
    query = { re.escape(f"{delim}{k}{delim}"): v for k, v in query.items() }

    # Create a single regex to run over input
    pattern = re.compile("|".join(query.keys()))

    # Function to find replacement from a match
    repl = lambda m: query[re.escape(m.group(0))]

    # Find all appropriate paths to replace
    paths = exclude_iterdir(Path.cwd(), ["**/.git", "**/.tplt", *exclude])

    # Use stdout redirection to replace files with fileinput
    with FileInput(files=paths, inplace=True) as f:
        for line in f:
            (newline, num) = pattern.subn(repl, line)
            print(newline if num > 0 else line, end="")


def add_replace(subparser):
    sub = subparser.add_parser(
        "replace",
        help="Replace strings with queried information"
    )

    sub.add_argument(
        "--query", "-q",
        help="Path to json infomation to replace",
        default=".tplt/query.json"
    )
    sub.add_argument(
        "--delim", "-d",
        help="Delimiter to use to mark templates",
        default="&&"
    )
    sub.add_argument(
        "--exclude", "-e",
        help="File globs to exclude",
        action="append",
        default=[]
    )

    sub.set_defaults(func=replace)


def build_parser():
    DIR = Path(env.get("XDG_TEMPLATES_DIR", "~/Templates"))\
        .expanduser()\
        .joinpath("tplt")

    parser = ArgumentParser(prog="tplt")
    parser.add_argument("--path", "-p", help="Path to templates", default=DIR)
    parser.add_argument(
        "--where", "-w",
        help="Print path to templates",
        action="store_true",
        default=False
    )
    parser.set_defaults(func=default)

    subparser = parser.add_subparsers()
    add_ls(subparser)
    add_new(subparser)
    add_init(subparser)
    add_query(subparser)
    add_replace(subparser)

    return parser


def main():
    args = build_parser().parse_args()

    if args.where:
        print(args.path)
    else:
        args.func(**args.__dict__)


if __name__ == "__main__":
    main()
