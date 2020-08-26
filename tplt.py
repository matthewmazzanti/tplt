import subprocess
from argparse import ArgumentParser
from os import environ as env
from pathlib import Path
from sys import exit

from git import Repo, GitCommandError

def ensure_path(path):
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


def default(**kwargs):
    exit("No command specified")


def ls(path, **kwargs):
    path = ensure_path(path)

    print("Available templates:\n")
    for sub_path in path.iterdir():
        print(sub_path.name)


def new(path, template, **kwargs):
    path = ensure_path(path)

    template = path.joinpath(template)
    ensure_no_path(template)

    Repo.init(path=template)
    print(template)


def init(path, template, instance, run, **kwargs):
    path = ensure_path(path)

    template = Repo(path.joinpath(template))

    instance = Path.cwd().joinpath(instance)
    ensure_no_path(instance)

    template.clone(instance, multi_options=['--origin tplt'])
    print(instance)

    init = instance.joinpath(".tplt/init")
    if init.exists():
        if not run:
            res = input(f"Init file found at {init}, run? [y/n] ")
            if res.lower() == "y":
                run = True

        if run:
            print(f"Running script {init}")
            subprocess.run(str(init))

def query(**kwargs):
    print("Query")


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
sub_init.add_argument("instance", help="Path to clone template")
sub_init.add_argument(
    "--run",
    "-r",
    help="Run init script after cloning",
    action="store_true"
)
sub_init.set_defaults(func=init)

sub_query = sub.add_parser("query", help="Query information from the user")
sub_query.set_defaults(func=query)


def main():
    args = parser.parse_args()

    if args.where:
        print(args.path)
    else:
        args.func(**args.__dict__)


if __name__ == "__main__":
    main()
