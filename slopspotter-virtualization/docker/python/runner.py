import json
import os
import shutil
import subprocess
import sys
import tempfile


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "package name required"}))
        return

    pkg = sys.argv[1]
    work = tempfile.mkdtemp(prefix="scan-")
    report = {
        "package": pkg,
        "install_rc": None,
        "import_rc": None,
        "install_error": None,
        "import_error": None,
        "install_out": "",
        "install_err": "",
        "import_out": "",
        "import_err": "",
        "network": [],
        "processes": [],
        "timeout": False,
    }

    try:
        install = subprocess.run(
            [
                "strace",
                "-ff",
                "-e",
                "trace=network,file,process",
                "-o",
                os.path.join(work, "trace_install"),
                "pip",
                "install",
                "--no-input",
                "--no-cache-dir",
                pkg,
            ],
            capture_output=True,
            text=True,
            timeout=40,
        )
        report["install_rc"] = install.returncode
        report["install_out"] = (install.stdout or "")[-4000:]
        report["install_err"] = (install.stderr or "")[-4000:]
        if install.returncode != 0:
            report["install_error"] = "install_failed"

        mod_name = pkg.replace("-", "_").split(".")[0]
        imp = subprocess.run(
            [
                "strace",
                "-ff",
                "-e",
                "trace=network,file,process",
                "-o",
                os.path.join(work, "trace_import"),
                "python",
                "-c",
                f"import {mod_name}",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        report["import_rc"] = imp.returncode
        report["import_out"] = (imp.stdout or "")[-2000:]
        report["import_err"] = (imp.stderr or "")[-2000:]
        if imp.returncode != 0:
            report["import_error"] = "import_failed"

        for fname in os.listdir(work):
            if not fname.startswith("trace"):
                continue
            path = os.path.join(work, fname)
            if not os.path.isfile(path):
                continue
            with open(path, "r", errors="ignore") as fh:
                for line in fh:
                    if "connect(" in line:
                        report["network"].append(line.strip())
                    if "execve(" in line:
                        report["processes"].append(line.strip())
    except subprocess.TimeoutExpired:
        report["timeout"] = True
    finally:
        shutil.rmtree(work, ignore_errors=True)

    print(json.dumps(report))


if __name__ == "__main__":
    main()
