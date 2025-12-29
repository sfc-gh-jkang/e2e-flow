# Quickstart on how to setup google compute

- Setup and ensure you can login
- Install uv
- Install prefect via pyproject.toml
- Install docker and ensure the docker group has your userid added and test
- tmux install: `sudo apt update` and then `sudo apt install tmux`
  - TMUX guide: <https://www.redhat.com/en/blog/introduction-tmux-linux>
    <https://tmuxcheatsheet.com/>

## Try setting up prefect

```bash
tmux ls
tmux new-session -A -s prefect
tmux attach -t prefect
uv run prefect worker start --pool "google-vm"
uv run prefect worker start --pool "google-vm-docker"
```

---

## ⚠️ IMPORTANT: After Updating the VM

If you update the VM with `sudo apt update && sudo apt upgrade`, you MUST restart
Docker and the Prefect workers or you'll get websocket timeout errors!

```bash
# 1. Restart Docker daemon
sudo systemctl restart docker

# 2. Kill existing Prefect workers
pkill -f "prefect worker"

# 3. Restart the workers (in tmux)
tmux attach -t prefect
uv run prefect worker start --pool "google-vm"
# In another pane (Ctrl+b c):
uv run prefect worker start --pool "google-vm-docker"
```

**Symptom if you forget**: Flows crash immediately with:

```text
TimeoutError: timed out during opening handshake
```

Switch panes
Ctrl+b o

Leave pane
ctrl + b d
