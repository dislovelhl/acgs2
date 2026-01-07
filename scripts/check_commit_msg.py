#!/usr/bin/env python3
import re
import sys

# Semantic commit pattern: type(scope): summary
# Types: gov, policy, chain, infra, feat, fix, docs, style, refactor, test, chore
PATTERN = r"^(gov|policy|chain|infra|feat|fix|docs|style|refactor|test|chore)(\(.+\))?!?: .+$"


def validate_commit_msg(msg_file):
    with open(msg_file, "r") as f:
        msg = f.read().strip()

    # Ignore merge commits
    if msg.startswith("Merge branch"):
        return 0

    if not re.match(PATTERN, msg):
        print("❌ ERROR: Invalid commit message format.")
        print("Expected: <type>(<scope>): <summary>")
        print(
            "Allowed types: gov, policy, chain, infra, feat, fix, docs, style, refactor, test, chore"
        )
        print("Example: gov(mhc): add stability layer")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(validate_commit_msg(sys.argv[1]))
