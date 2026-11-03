# Security

Please do not open a public issue for a security problem. Use GitHub's private vulnerability reporting
("Report a vulnerability" on the Security tab of this repository).

This repository holds engine patches, serving configuration, an A/B harness and documentation; it runs no service of its
own. The API server it configures (vLLM's OpenAI-compatible server) listens on loopback without an API key: keep it on
a private network or put authentication in front of it.
