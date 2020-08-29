import subprocess
import re
import json
from argparse import ArgumentParser
from os import environ as env
from pathlib import Path
from sys import exit

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

def default(**kwargs):
    exit("No command specified")


def ls(path, **kwargs):
    path = ensure_dir(path)

    print("Available templates:\n")
    for sub_path in path.iterdir():
        print(sub_path.name)


def new(path, template, **kwargs):
    path = ensure_dir(path)

    template = path.joinpath(template)
    ensure_no_path(template)

    Repo.init(path=template)
    print(template)


def init(path, template, name, run, **kwargs):
    path = ensure_dir(path)

    template = Repo(path.joinpath(template))

    instance = Path.cwd().joinpath(name)
    ensure_no_path(instance)

    repo = template.clone(instance, multi_options=['--origin tplt'])
    print(instance)

    init = instance.joinpath(".tplt/init")
    if init.exists():
        if not run:
            res = input(f"Init file found at {init}, run? [y/n] ")
            if res.lower() == "y":
                run = True

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


def query(output, question=None, default=None, **kwargs):
    if not question and not answer:
        exit("No questions or answers specified")

    out_path = Path(output).absolute()
    if out_path.exists():
        exit(f"{output} already exists!")

    questions = eq_split(question)
    answers = dict(eq_split(default))
    for name, question in questions:
        res = input(f"{question}: ")
        if res != "":
            answers[name] = res

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.touch()
    with open(out_path, "w") as f:
        f.write(json.dumps(answers, indent=4))


def replace(query, delim, exclude, **kwargs):
    query = Path(query).absolute()
    with open(query) as f:
        query = json.load(f)

    print(query)

    # https://stackoverflow.com/questions/6116978/how-to-replace-multiple-substrings-of-a-string
    query = dict((re.escape(f"{delim}{k}{delim}"), v) for k, v in query.items())

    # Create a single regex to run over input
    pattern = re.compile("|".join(query.keys()))
    # Function to find replacement from a match
    repl = lambda m: query[re.escape(m.group(0))]

    # (text, num) = pattern.subn(repl, text)

    for path in exclude_iterdir(Path.cwd(), ["**/.git", "**/.tplt", *exclude]):
        with open(path, "rw") as f:
            pass

        print(path)


DIR = Path(env.get("XDG_TEMPLATES_DIR", "~/Templates"))\
    .expanduser()\
    .joinpath("tplt")

parser = ArgumentParser(prog="tplt")
parser.add_argument("--path", "-p", help="Path to templates", default=DIR)
parser.add_argument(
    "--where",
    "-w",
    help="Print path to templates",
    action="store_true",
    default=False
)
parser.set_defaults(func=default)

sub = parser.add_subparsers()

sub_ls = sub.add_parser("ls", help="List available templates")
sub_ls.set_defaults(func=ls)

sub_new = sub.add_parser("new", help="Create new template")
sub_new.add_argument("template", help="Name of new template to create")
sub_new.set_defaults(func=new)

sub_init = sub.add_parser("init", help="Initialize a template")
sub_init.add_argument("template", help="Name of template to use")
sub_init.add_argument("name", help="Name of directory to clone into")
sub_init.add_argument(
    "--run",
    "-r",
    help="Run init script after cloning",
    action="store_true"
)
sub_init.set_defaults(func=init)

sub_query = sub.add_parser("query", help="Query information from the user")
sub_query.add_argument("--question", "-q", help="Key/value pair of name/question", action="append")
sub_query.add_argument("--default", "-d", help="Set a default for a question", action="append")
sub_query.add_argument("--output", "-o", help="Where to output query results", default=".tplt/query.json")
sub_query.set_defaults(func=query)

sub_replace = sub.add_parser("replace", help="Replace strings with queried information")
sub_replace.add_argument("--query", "-q", help="Path to json infomation to replace", default=".tplt/query.json")
sub_replace.add_argument("--delim", "-d", help="Delimiter to use to mark templates", default="&&")
sub_replace.add_argument("--exclude", "-e", help="File globs to exclude", action="append")
sub_replace.set_defaults(func=replace)

def main():
    args = parser.parse_args()

    if args.where:
        print(args.path)
    else:
        args.func(**args.__dict__)


if __name__ == "__main__":
    main()
