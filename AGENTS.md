# AGENTS.md

## Overview

This project is a sandbox for experimenting with clinical document retrieval using AI agents. It indexes synthetic patient summaries (IPS-style markdown files) and provides an interactive command-line agent that can answer questions about patient data. The system uses LlamaIndex with OpenAI embeddings to build an in-memory vector index, enabling semantic search across patient documents. The agent can retrieve relevant patient information and cite sources, making it useful for exploring retrieval patterns over clinical-style content without the complexity of persistent storage or production infrastructure.

## Persistent Agent Session (tmux)

Use a tmux session to keep the agent running between questions.

Prerequisites:
- `tmux` installed and available in PATH
- Working directory is the repository root

Start once per working session:

```bash
SESSION=hackathon_agent
tmux has-session -t "$SESSION" 2>/dev/null || \
  tmux new-session -d -s "$SESSION" "./start-agent.sh"
```

Send a question without restarting:

```bash
tmux send-keys -t "$SESSION" "Who is from Canada?" C-m
tmux capture-pane -p -t "$SESSION" -S -200
```

Guidelines for coding agents:
- Reuse the same session name (`hackathon_agent`) for follow-up questions.
- Do not send `exit` after each question.
- After `send-keys`, read output with `capture-pane` and look for the `Agent>` response.

Cleanup when done:

```bash
tmux send-keys -t "$SESSION" "exit" C-m
tmux kill-session -t "$SESSION"
```
