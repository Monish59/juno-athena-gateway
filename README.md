# JUNO-Athena Research Gateway

A modular, privacy-aware, AI/ML-driven Streamlit research environment for literature synthesis, academic writing, and collaborative lab work.

## Features

- Email+Passkey authentication (Athena-issued)
- License management + renewal
- Modular abilities (unlock with mentor approval)
- Scientific onboarding and daily brief
- Lab library (read-only)
- Secure groups, projects, findings, and chat (commands supported)
- Supervisor comments, Athena AI assistant, audit logging (ARGOS webhooks)
- Codespaces/devcontainer + CI

## Quickstart

1. **Clone the repo**

2. **Install requirements**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure secrets**

   - Copy `.streamlit/secrets.example.toml` to `.streamlit/secrets.toml`
   - Fill in your passkeys, ARGOS URLs, and tokens

4. **(Optional) Seed demo data**
   ```bash
   python seeds/load_demo.py
   ```

5. **Run the app**
   ```bash
   streamlit run app.py
   ```

6. **[Optional] Use Codespaces**
   - Open in GitHub Codespaces for instant dev environment

7. **[Optional] Enable CI**
   - CI will lint and check app boot on every push/PR

## Documentation

- [Abilities](docs/abilities.md)
- [License Renewal Runbook](docs/renewal.md)
- [Webhooks](docs/webhooks.md)
- [Privacy Policy](COPY_PRIVACY.md)

---

**Contact Supervisor for access or questions.**