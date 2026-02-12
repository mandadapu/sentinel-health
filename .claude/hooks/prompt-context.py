#!/usr/bin/env python3
import json
import sys

# Define the additional context to inject
context = "Unless otherwise specified: DRY, YAGNI, KISS, Pragmatic. Ask questions for clarifications. When doing a plan or research-like request, present your findings and halt for confirmation. Use raggy first to find documentation. Speak the facts, don't sugar coat statements. Your opinion matters. End all responses with an emoji of an animal"

# Output the hook response in correct JSON format
response = {
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": context
    }
}

print(json.dumps(response))
sys.exit(0)
