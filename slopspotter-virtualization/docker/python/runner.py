import json
import os
import shutil
import subprocess
import sys
import tempfile
import importlib
import importlib.util


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
        "installed_version": None,
        "download_bytes": None,
        "install_out": "",
        "install_err": "",
        "import_out": "",
        "import_err": "",
        "network": [],
        "processes": [],
        "file_ops": [],
        "file_writes": [],
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
        # best-effort parse for version/size from pip output
        for line in (install.stdout or "").splitlines():
            if "Downloading" in line and "(" in line and " kB" in line:
                try:
                    size_part = line.split("(")[-1].split(" ")[0]
                    report["download_bytes"] = int(float(size_part) * 1024)
                except Exception:
                    pass
            if "Installing collected packages" in line:
                parts = line.split()
                if len(parts) >= 3:
                    report["installed_version"] = parts[-1]
        # Try to read installed version and approximate size from site-packages
        try:
            import importlib.metadata as metadata

            if not report["installed_version"]:
                report["installed_version"] = metadata.version(pkg)
            dist = metadata.distribution(pkg)
            if dist and dist.locate_file(""):
                base_path = dist.locate_file("").parent
                total = 0
                for root, _, files in os.walk(base_path):
                    for f in files:
                        fp = os.path.join(root, f)
                        try:
                            total += os.path.getsize(fp)
                        except OSError:
                            continue
                if total:
                    report["download_bytes"] = total
        except Exception:
            pass

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
                    if any(tok in line for tok in ("open(", "openat(", "stat(", "access(")):
                        # Capture file paths inside quotes, if present
                        parts = line.split("\"")
                        if len(parts) >= 2:
                            path_val = parts[1]
                            if path_val:
                                report["file_ops"].append(path_val)
                                # Heuristic: consider write if flags include O_WRONLY/O_RDWR/O_CREAT/O_TRUNC/O_APPEND
                                if any(flag in line for flag in ("O_WRONLY", "O_RDWR", "O_CREAT", "O_TRUNC", "O_APPEND")):
                                    report["file_writes"].append(path_val)
    except subprocess.TimeoutExpired:
        report["timeout"] = True
    finally:
        shutil.rmtree(work, ignore_errors=True)

    print(json.dumps(report))


if __name__ == "__main__":
    main()
