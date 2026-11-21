"""Run the published examples on an Ubuntu runner using exact course bytes."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import venv


ROOT = Path(__file__).resolve().parents[1]
IMAGES = re.compile(rb"(?:docker\.io|ghcr\.io)/[a-z0-9_/-]+@sha256:[a-f0-9]{64}")


def main():
    name = sys.argv[1]
    manifest = json.loads((ROOT / "ci/cloud-examples.json").read_bytes())
    directory = ROOT / "cloud-examples" / name
    expected = manifest[name]
    actual = {p.name: p.read_bytes() for p in directory.iterdir()}
    hashes = {filename: hashlib.sha256(raw).hexdigest() for filename, raw in actual.items()}
    if hashes != expected:
        raise ValueError("The exercise members differ from the published course")
    for reference in sorted({m.decode("ascii") for raw in actual.values() for m in IMAGES.findall(raw)}):
        subprocess.run(["docker", "pull", reference], check=True, timeout=150)
    with tempfile.TemporaryDirectory(prefix="workbench-course-") as temp:
        environment = Path(temp) / "python"
        venv.EnvBuilder(with_pip=(name == "dns")).create(environment)
        python = environment / "bin" / "python"
        if name == "dns":
            subprocess.run(
                [python, "-I", "-m", "pip", "install", "--disable-pip-version-check",
                 "--only-binary=:all:", "--require-hashes", "-r", directory / "requirements.txt"],
                check=True, timeout=120,
            )
        for mode in ("guide", "example"):
            result = subprocess.run([python, "-B", directory / "run.py", mode],
                                    cwd=directory, stdout=subprocess.PIPE, check=True, timeout=220)
            proof = json.loads(result.stdout)
            if proof.get("passed") is not True or proof.get("mode") != mode:
                raise ValueError(f"{name}/{mode} did not verify")
            print(json.dumps({
                "scope": "published-cloud-example",
                "topic": name,
                "mode": mode,
                "passed": True,
                "commit": os.environ["GITHUB_SHA"],
                "run": os.environ["GITHUB_RUN_ID"],
                "attempt": os.environ["GITHUB_RUN_ATTEMPT"],
                "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
            }), flush=True)


if __name__ == "__main__":
    main()
