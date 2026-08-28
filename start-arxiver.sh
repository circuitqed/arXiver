#!/bin/bash

SESSION_NAME="arxiver"
PROJECT_DIR="/home/projects/arxiver"

show_help() {
    echo "Usage: $0 [option]"
    echo ""
    echo "Options:"
    echo "  (no args)   Start or attach to the session"
    echo "  -k, --kill  Kill the session"
    echo "  -h, --help  Show this help message"
}

kill_session() {
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        tmux kill-session -t "$SESSION_NAME"
        echo "Session '$SESSION_NAME' killed."
    else
        echo "No session '$SESSION_NAME' found."
    fi
}

start_or_attach() {
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        echo "Attaching to existing session '$SESSION_NAME'..."
        tmux attach -t "$SESSION_NAME"
    else
        echo "Starting new session '$SESSION_NAME'..."
        tmux new-session -s "$SESSION_NAME" -c "$PROJECT_DIR" "claude --dangerously-skip-permissions; exec bash"
    fi
}

case "$1" in
    -k|--kill) kill_session ;;
    -h|--help) show_help ;;
    "") start_or_attach ;;
    *) echo "Unknown option: $1"; show_help; exit 1 ;;
esac
