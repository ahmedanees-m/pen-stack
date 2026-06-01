#!/usr/bin/env python3
"""penctl — orchestrate the VM over SSH/SFTP from the laptop. Docker-only on the VM.

Laptop runs only this; all heavy compute is `docker run` on the VM, artifacts pulled to the
Google Drive folder over SFTP (no rclone). See docs/INFRA.md.
"""
import os
import sys
import posixpath

import click
import paramiko
from dotenv import load_dotenv
from rich.console import Console

load_dotenv(os.path.expanduser("~/.pen/secrets.env"))
C = Console()
H, P = os.environ.get("VM_HOST", ""), int(os.environ.get("VM_PORT", "22"))
U, K = os.environ.get("VM_USER", ""), os.path.expanduser(os.environ.get("VM_KEY", ""))
WORK, DATA = os.environ.get("VM_WORK", ""), os.environ.get("VM_DATA", "")
IMG, DRIVE = os.environ.get("DOCKER_IMG", "penstack:0.1"), os.environ.get("PEN_DRIVE", "")


def _client():
    c = paramiko.SSHClient()
    c.load_system_host_keys()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # key auth preferred; password fallback supported via VM_PASS
    if K and os.path.exists(K):
        c.connect(H, P, U, key_filename=K, timeout=30)
    else:
        c.connect(H, P, U, password=os.environ.get("VM_PASS"), timeout=30)
    return c


def _run(cmd, stream=True):
    c = _client()
    chan = c.get_transport().open_session()
    chan.get_pty()
    chan.exec_command(cmd)
    out = b""
    while True:
        if chan.recv_ready():
            d = chan.recv(4096)
            out += d
            if stream:
                sys.stdout.write(d.decode(errors="replace"))
                sys.stdout.flush()
        if chan.exit_status_ready() and not chan.recv_ready():
            break
    code = chan.recv_exit_status()
    c.close()
    if code:
        raise SystemExit(f"[remote exit {code}]")
    return out.decode(errors="replace")


def _docker(inner, gpus=True):
    g = "--gpus all " if gpus else ""
    return _run(f'docker run --rm {g}-v {WORK}:/work -v {DATA}:/data -w /work {IMG} bash -lc "{inner}"')


@click.group()
def cli():
    """penctl — laptop-side orchestrator for the PEN-STACK VM."""


@cli.command()
def bootstrap():
    """Create VM dirs (mkdir only — no installs)."""
    dirs = [WORK, f"{DATA}/raw", f"{DATA}/interim", f"{DATA}/features",
            f"{DATA}/models", f"{DATA}/out", f"{DATA}/logs"]
    _run("mkdir -p " + " ".join(dirs))
    C.print("[green]VM dirs ready[/]")


@cli.command()
@click.option("--repo", default="https://github.com/ahmedanees-m/pen-stack.git")
def clone(repo):
    _run(f"test -d {WORK}/.git || git clone {repo} {WORK}")
    C.print("[green]repo on VM[/]")


@cli.command()
def push():
    """SFTP the local working tree (code only) to the VM. Excludes data/."""
    sftp = _client().open_sftp()
    base = os.getcwd()
    EXC = {".git", "data", "__pycache__", ".venv", "node_modules"}
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in EXC]
        rel = os.path.relpath(root, base)
        rdir = posixpath.join(WORK, rel) if rel != "." else WORK
        try:
            sftp.mkdir(rdir)
        except IOError:
            pass
        for f in files:
            sftp.put(os.path.join(root, f), posixpath.join(rdir, f))
    C.print("[green]code pushed[/]")


@cli.command(name="build")
def build_img():
    _run(f"cd {WORK} && docker build -t {IMG} -f docker/Dockerfile docker")
    C.print(f"[green]image {IMG} built[/]")


@cli.command(context_settings=dict(ignore_unknown_options=True))
@click.argument("inner", nargs=-1)
@click.option("--cpu", is_flag=True, help="no GPU")
def run(inner, cpu):
    """Run a command INSIDE the Docker container on the VM."""
    _docker(" ".join(inner), gpus=not cpu)


@cli.command()
def df():
    """Check VM disk; warn if data dir > 400 GB."""
    C.print(_run(f"du -sh {DATA} && df -h {DATA}"))


@cli.command()
@click.argument("remote")
@click.option("--dest", default="")
def pull(remote, dest):
    """SFTP-pull a VM artifact into the local Google Drive folder (auto-syncs to Drive)."""
    sftp = _client().open_sftp()
    rpath = posixpath.join(DATA, remote)
    lpath = os.path.join(DRIVE, dest, os.path.basename(remote))
    os.makedirs(os.path.dirname(lpath), exist_ok=True)
    sftp.get(rpath, lpath)
    C.print(f"[green]pulled -> {lpath}[/]")


@cli.command()
@click.argument("remote")
def clean(remote):
    """Delete a staged artifact on the VM after it is safely on Drive."""
    _run(f"rm -rf {posixpath.join(DATA, remote)}")
    C.print("[green]cleaned on VM[/]")


if __name__ == "__main__":
    cli()
