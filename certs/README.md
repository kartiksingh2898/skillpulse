# TiDB Cloud CA Certificate

Place your TiDB Cloud CA certificate here as `tidb-ca.pem`.

## How to get it

1. Go to your TiDB Cloud cluster
2. Click **Connect**
3. Download the CA certificate from the dialog (usually a `.pem` file)
4. Rename/save it as `certs/tidb-ca.pem`

## Important notes

- This file is a **public certificate** — not a credential. It is safe to commit to the repository.
- Both your local machine and GitHub Actions use the same relative path `certs/tidb-ca.pem`.
- **Update this file if TiDB changes the recommended CA certificate.**
- The `DB_SSL_CA=certs/tidb-ca.pem` env var in `.env` and the GitHub Actions workflow points here.
