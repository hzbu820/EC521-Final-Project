const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFileSync, spawnSync } = require("child_process");
const fs = require("fs");

function main() {
  const pkg = process.argv[2];
  if (!pkg) {
    console.log(JSON.stringify({ error: "package name required" }));
    return;
  }

  const work = fs.mkdtempSync(path.join(os.tmpdir(), "scan-"));
const report = {
    package: pkg,
    install_rc: null,
    require_rc: null,
    install_error: null,
    require_error: null,
    installed_version: null,
    download_bytes: null,
    install_out: "",
    install_err: "",
    require_out: "",
    require_err: "",
    network: [],
    processes: [],
    file_ops: [],
    timeout: false,
  };

  try {
    const install = spawnSync(
      "strace",
      [
        "-ff",
        "-e",
        "trace=network,file,process",
        "-o",
        path.join(work, "trace_install"),
        "npm",
        "install",
        pkg,
      ],
      { encoding: "utf8", timeout: 40000 }
    );
    report.install_rc = install.status;
    report.install_out = (install.stdout || "").slice(-4000);
    report.install_err = (install.stderr || "").slice(-4000);
    if (install.status !== 0) {
      report.install_error = "install_failed";
    }
    // Try to read installed version from node_modules/<pkg>/package.json
    try {
      const pkgJsonPath = path.join(process.cwd(), "node_modules", pkg, "package.json");
      if (fs.existsSync(pkgJsonPath)) {
        const pkgJson = JSON.parse(fs.readFileSync(pkgJsonPath, "utf8"));
        if (pkgJson && pkgJson.version) {
          report.installed_version = pkgJson.version;
        }
        // compute dir size
        const dirSize = (dir) => {
          let total = 0;
          const entries = fs.readdirSync(dir, { withFileTypes: true });
          for (const entry of entries) {
            const full = path.join(dir, entry.name);
            if (entry.isDirectory()) total += dirSize(full);
            else total += fs.statSync(full).size;
          }
          return total;
        };
        report.download_bytes = dirSize(path.join(process.cwd(), "node_modules", pkg));
      }
    } catch (e) {
      // ignore
    }

    const req = spawnSync(
      "strace",
      [
        "-ff",
        "-e",
        "trace=network,file,process",
        "-o",
        path.join(work, "trace_require"),
        "node",
        "-e",
        `require("${pkg.replace(/"/g, "")}")`,
      ],
      { encoding: "utf8", timeout: 15000 }
    );
    report.require_rc = req.status;
    report.require_out = (req.stdout || "").slice(-2000);
    report.require_err = (req.stderr || "").slice(-2000);
    if (req.status !== 0) {
      report.require_error = "require_failed";
    }

    fs.readdirSync(work).forEach((fname) => {
      if (!fname.startsWith("trace")) return;
      const file = path.join(work, fname);
      if (!fs.statSync(file).isFile()) return;
      const lines = fs.readFileSync(file, "utf8").split("\n");
      for (const line of lines) {
        if (line.includes("connect(")) report.network.push(line.trim());
        if (line.includes("execve(")) report.processes.push(line.trim());
        if (line.includes("open(") || line.includes("openat(") || line.includes("stat(") || line.includes("access(")) {
          const firstQuote = line.indexOf('"');
          const secondQuote = firstQuote >= 0 ? line.indexOf('"', firstQuote + 1) : -1;
          if (firstQuote >= 0 && secondQuote > firstQuote) {
            const pathVal = line.slice(firstQuote + 1, secondQuote);
            if (pathVal) report.file_ops.push(pathVal);
          }
        }
      }
    });
  } catch (err) {
    if (err.killed) {
      report.timeout = true;
    } else {
      report.install_error = String(err);
    }
  } finally {
    fs.rmSync(work, { recursive: true, force: true });
  }

  console.log(JSON.stringify(report));
}

main();
