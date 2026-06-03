# PEN-STACK v3.0 - Infrastructure & Workflow

Canonical environment definition (program doc Section 0.A). Reused verbatim by every phase.

## Three-tier architecture

```
LAPTOP (2.5 GHz, 8 GB)  --paramiko SSH/SFTP-->  VM <vm-hostname> (<your-vm-ip>)
  - edit code/notebooks                            24 cores, 64 GB RAM, ~16 GB GPU (RTX A4000)
  - orchestrate via penctl                         500 GB scratch disk, Ubuntu 22.04
  - light unit tests                               ALL heavy compute, Docker-only
        |
        | Google Drive for Desktop (G:\My Drive\PEN-STACK)
        v
  GOOGLE DRIVE (durable storage) <-- artifacts pulled from VM via SFTP, then cleaned from VM
```

## Golden rules (non-negotiable)

1. **Docker-only on the VM.** Never `apt/pip install` on the host. All tools live in `penstack:0.1`.
2. **SFTP, not rclone**, for VM<->laptop transfer (paramiko SFTP).
3. **500 GB discipline.** Stage -> process -> pull-to-Drive -> clean. Keep `/data` under ~400 GB; `penctl df` before heavy steps.
4. **Reproducible.** Pinned image digests, pinned dataset versions, SHA-locked prereg files.
5. **No secrets in git.** Keys/tokens live only in `~/.pen/secrets.env` on the laptop.

## Laptop setup (one-time)

```bash
python3 -m venv ~/.pen/venv && source ~/.pen/venv/bin/activate
pip install -e ".[orchestrate]"   # paramiko, scp, click, rich, python-dotenv
```

`~/.pen/secrets.env` (git-ignored):

```bash
VM_HOST=<your-vm-ip>
VM_PORT=22
VM_USER=<your-vm-user>
VM_KEY=~/.ssh/penstack_ed25519        # or omit and set VM_PASS for password auth
PEN_DRIVE="/path/to/Google Drive/PEN-STACK"
VM_WORK=/home/<your-vm-user>/penstack
VM_DATA=/home/<your-vm-user>/data
DOCKER_IMG=penstack:0.1
```

## The loop

```bash
python tools/penctl.py bootstrap            # mkdir VM dirs
python tools/penctl.py clone                # git clone monorepo on VM
python tools/penctl.py build                # docker build penstack:0.1 on VM
python tools/penctl.py run python -c "import torch; print(torch.cuda.is_available())"   # must print True
# per step:
python tools/penctl.py push
python tools/penctl.py run python -m pen_stack.<module>.<entry> --config configs/<cfg>.yaml
python tools/penctl.py pull out/<artifact> --dest phaseN
python tools/penctl.py clean out/<artifact>
```

## VM scratch layout

```
$VM_DATA/{raw,interim,features,models,out,logs}   # all transient; pulled to Drive then cleaned
```
