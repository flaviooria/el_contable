#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SOURCE_DIR="$ROOT_DIR/.agents/roles"
TARGET_DIR="$ROOT_DIR/.opencode/agents"

mkdir -p "$TARGET_DIR"

for agent in leader backend tester reviewer; do
    source="$SOURCE_DIR/$agent.md"
    target="$TARGET_DIR/$agent.md"

    if [ ! -f "$source" ]; then
        echo "Missing canonical agent: $source" >&2
        exit 1
    fi

    rm -f "$target"
    ln -s "../../.agents/roles/$agent.md" "$target"
    echo "Linked .opencode/agents/$agent.md -> ../../.agents/roles/$agent.md"
done
