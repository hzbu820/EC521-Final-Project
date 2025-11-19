# Slopspotter CLI & Native Host

This subproject is managed with [UV](https://docs.astral.sh/uv/). While it's not required for building this project, it makes setting up easier.

## Local Installation Instructions (With UV)

1. Make `slopspotter-cli` your current directory (if not already done).

2. Set up / activate your Python environment.

   ```bash
   uv sync
   ```

   You can also install additional packages for development:

   ```bash
   uv sync --dev
   ```

## Local Installation Instructions (Without UV)

1. Make `slopspotter-cli` your current directory (if not already done).

2. Set up isolated Python virtual environment using `venv`

   ```bash
   python -m venv .venv --prompt='slopspotter-cli'
   ```

3. Activate your Python environment.

   ```bash
   # For MacOS / Linux:
   source .venv/bin/activate
   ```

   ```powershell
   # For Windows:
   .venv\Scripts\Activate
   ```

4. Install the `slopspotter` Python package.

   ```bash
   pip install .
   ```

   You can also install additional packages for development:

   ```bash
   pip install --editable . --group=dev
   ```

5. If your GPU is too old to support the most recent of PyTorch, you can install an older version that relies on older CUDA toolkit versions.[^1]

   ```bash
   pip install torch==2.7.1 torchvision==0.22.1 torchaudio==2.7.1 --index-url https://download.pytorch.org/whl/cu118
   ```

6. Install manifests for enabling native messaging.

   ```bash
   slopspotter --install-manifests=firefox
   ```

[^1]: https://pytorch.org/get-started/previous-versions/
