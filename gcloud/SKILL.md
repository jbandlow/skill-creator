---
name: gcloud
description: Interact with Google Cloud resources and configurations using the gcloud CLI. Use this when the user asks to manage, configure, or query Google Cloud infrastructure.
---

# Instruction: gcloud

You can use the Google Cloud CLI (`gcloud`) to interact with GCP resources on behalf of the user.

## Checklist

When performing tasks related to `gcloud`, follow these guidelines:

1. **Check Configuration Status**: Before running complex commands, check the current active configuration, project, and account to ensure you are operating in the correct environment:
   ```bash
   gcloud config list
   ```

2. **Check Authentication**: Ensure the user is properly authenticated.
   ```bash
   gcloud auth list
   ```

3. **Discover Syntax**: `gcloud` has a vast surface area. Do not guess commands. If you are unsure of the exact syntax or available flags for a specific resource, proactively lean on the `--help` flag or `gcloud help` commands to read the manual before proceeding.
   ```bash
   gcloud compute instances --help
   ```

## Authorization
If you need to run a command that requires browser-based authentication (e.g., `gcloud auth login` or `gcloud auth application-default login`), **you cannot do this automatically**. 
- You must explain to the user which command they need to run.
- Wait for them to complete the login process in their own terminal.
- Resume your task once they confirm they have logged in.
