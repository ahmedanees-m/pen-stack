# PEN-STACK - Infrastructure & Workflow

Canonical environment definition, reused verbatim across the project.

## Three-tier architecture

```
LOCAL  --paramiko SSH/SFTP-->  GPU HOST
  - edit code/notebooks          ~16 GB GPU, Linux, Docker
  - orchestrate via penctl       500 GB scratch disk
  - light unit tests             ALL heavy compute, Docker-only
        |
        | a local synced working directory
        v
  DURABLE STORAGE <-- artifacts pulled from the host via SFTP, then cleaned from the host
```

## Golden rules (non-negotiable)

1. **Docker-only on the host.** Never `apt/pip install` on it. All tools live in `penstack:0.1`.
2. **SFTP, not rclone**, for host<->local transfer (paramiko SFTP).
3. **500 GB discipline.** Stage -> process -> pull-to-storage -> clean. Keep `/data` under ~400 GB; `penctl df` before heavy steps.
4. **Reproducible.** Pinned image digests, pinned dataset versions, SHA-locked prereg files.
5. **No secrets in git.** Keys/tokens live only in `~/.pen/secrets.env`, locally.

## Local setup (one-time)

```bash
python3 -m venv ~/.pen/venv && source ~/.pen/venv/bin/activate
pip install -e ".[orchestrate]"   # paramiko, scp, click, rich, python-dotenv
```

`~/.pen/secrets.env` (git-ignored):

```bash
VM_HOST=<host-address>
VM_PORT=22
VM_USER=<host-user>
VM_KEY=~/.ssh/penstack_ed25519        # or omit and set VM_PASS for password auth
PEN_DRIVE="/path/to/durable/storage/PEN-STACK"
VM_WORK=/home/<host-user>/penstack
VM_DATA=/home/<host-user>/data
DOCKER_IMG=penstack:0.1
```

## The loop

```bash
python tools/penctl.py bootstrap            # mkdir host dirs
python tools/penctl.py clone                # git clone monorepo on the host
python tools/penctl.py build                # docker build penstack:0.1 on the host
python tools/penctl.py run python -c "import torch; print(torch.cuda.is_available())"   # must print True
# per step:
python tools/penctl.py push
python tools/penctl.py run python -m pen_stack.<module>.<entry> --config configs/<cfg>.yaml
python tools/penctl.py pull out/<artifact> --dest <dest>
python tools/penctl.py clean out/<artifact>
```

## Host scratch layout

```
$VM_DATA/{raw,interim,features,models,out,logs}   # all transient; pulled to storage then cleaned
```
