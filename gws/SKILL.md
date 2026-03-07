---
name: gws
description: Interact with Google Workspace services (Drive, Gmail, Sheets, Calendar, etc.) using the gws CLI. Includes instructions for adjusting OAuth scopes. Use this when the user asks to manipulate GWS resources.
---

# Instruction: gws

You can use the Google Workspace CLI (`gws`) to interact with Google Workspace APIs (like Drive, Sheets, Gmail, etc.) on behalf of the user.

## Checklist

When performing tasks related to `gws`, follow these guidelines:

1. **Check Status**: Verify the current login status and active scopes.
   ```bash
   gws auth status
   ```

2. **Discover Syntax**: Use the `--help` flag frequently to understand the available commands and subcommands for each Workspace service.
   ```bash
   gws drive --help
   gws sheets --help
   ```

## Adjusting OAuth Scopes (CRITICAL)

The `gws` CLI only requests scopes that it has specifically been logged in with. If you try to run a command (e.g., creating a calendar event) and it fails due to missing scopes or permissions:

1. You **must** instruct the user to re-authenticate with the necessary scopes added.
2. The command to add new scopes is:
   ```bash
   gws auth login -s <comma_separated_scopes>
   ```
   *Example*: `gws auth login -s drive,gmail,sheets,calendar`
3. Tell the user to run this command in their terminal, complete the browser login flow, and then report back when they are done. 

## Troubleshooting Verification Errors (Error 403)

If the user attempts to log in with new scopes and reports receiving an `Error 403: access_denied` with the message:
> "GWS for AGY has not completed the Google verification process. The app is currently being tested, and can only be accessed by developer-approved testers."

This means their Google Cloud Project's OAuth consent screen is still in "Testing" mode, and their email is not listed as an approved test user. **Do not tell them to verify the app.**

Instead, provide them with these troubleshooting steps:
1. Go to the **Google Cloud Console** (console.cloud.google.com).
2. Select the Cloud Project created for the `gws` CLI.
3. In the left sidebar, navigate to **APIs & Services** > **OAuth consent screen**.
4. Scroll down to the **Test users** section.
5. Click **+ ADD USERS**.
6. Enter their email address and click **Save**.
7. Try the `gws auth login -s ...` command again. The warning page will still appear, but they will now have a "Continue" button to proceed.
