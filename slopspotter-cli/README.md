# Slopspotter CLI & Native Host

## Local Installation Instructions

1. Set up isolated Python virtual environment using `venv`

   ```bash
   python -m venv .venv --prompt='slopspotter-cli'
   ```

2. Activate Python environment

   ```bash
   # For MacOS / Linux:
   source .venv/bin/activate
   ```

   ```powershell
   # For Windows:
   .venv\Scripts\Activate
   ```

3. Install the `slopspotter` Python package

   ```bash
   pip install --editable .
   ```

4. Install manifests for enabling native messaging

   ```bash
   slopspotter --install-manifests=firefox
   ```
