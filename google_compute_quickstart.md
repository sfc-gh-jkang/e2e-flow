# Quickstart on how to setup google compute

- Setup and ensure you can login
- Install uv
- Install prefect via pyproject.toml
- Install docker and ensure the docker group has your userid added and test
- tmux install: `sudo apt update` and then `sudo apt install tmux`
    - TMUX guide: https://www.redhat.com/en/blog/introduction-tmux-linux
    https://tmuxcheatsheet.com/


# Try setting up prefect
```bash
tmux new-session -A -s prefect
tmux attach -t prefect
uv run prefect worker start --pool "google-vm"
uv run prefect worker start --pool "google-docker"
```

Switch panes
Ctrl+b o 

Leave pane
ctrl + b d