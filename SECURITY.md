# Security policy

## Reporting a vulnerability

Please report security issues privately through GitHub: open the **Security** tab of this repository and choose **Report a vulnerability**. Do not open a public issue.

You can expect a first reply within seven days.

## Scope

Shipright runs locally as Claude Code hooks and skills. It makes no network requests and stores nothing off your machine (see "Privacy and what it runs" in the README). Reports that matter most:

- A way for the AI to open a red-zone gate without a human-signed decision.
- A hook that sends data off the machine or runs commands it should not.
- A config that makes the hooks fail open where they should deny.

Known limitations listed in the README (for example, Bash edits are not intercepted) are not vulnerabilities, but ideas for closing them are welcome as issues.
