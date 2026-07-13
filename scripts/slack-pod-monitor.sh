#!/bin/bash
# Replace xoxp-YOUR-TOKEN-HERE with your User OAuth Token from the Slack app.
export SLACK_USER_TOKEN="xoxp-YOUR-TOKEN-HERE"
exec python3 "${HOME}/.hermes/scripts/slack-pod-monitor.py"
