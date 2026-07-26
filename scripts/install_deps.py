#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""ActionCoach Dependency Installer - clones required skills from GitHub.

This script is called when ActionCoach SKILL.md is installed.
It checks for and installs:
  - llm-wiki-skill (hard dependency): persistent memory/knowledge base
  - nuwa-skill (optional dependency): character perspective overlay

Usage:
  python scripts/install_deps.py [--check-only] [--skip-nuwa]
  python scripts/install_deps.py                    # install both
  python scripts/install_deps.py --check-only       # only check status
  python scripts/install_deps.py --skip-nuwa        # skip nuwa-skill

Output: JSON with status for each dependency.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

# Fix stdout encoding for GBK terminals
if hasattr(sys.stdout, "buffer"):
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)

# ── Dependency definitions ──
DEPENDENCIES = [
    {
        "name": "llm-wiki-skill",
        "repo": "https://github.com/sdyckjq-lab/llm-wiki-skill.git",
        "required": True,
        "description": "持久记忆/知识库（硬依赖）",
    },
    {
        "name": "nuwa-skill",
        "repo": "https://github.com/alchaincyf/nuwa-skill.git",
        "required": False,
        "description": "角色视角叠加（可选依赖）",
    },
]

# ══════════════════════ HELPERS ══════════════════════


def _codex_home():
    """Get CODEX_HOME or default to ~/.codex."""
    return os.environ.get("CODEX_HOME", os.path.join(os.path.expanduser("~"), ".codex"))


def _skills_dir():
    """Return the standard skills installation directory."""
    return os.path.join(_codex_home(), "skills")


def _is_installed(name):
    """Check if a skill is already installed by looking for its SKILL.md."""
    skill_path = os.path.join(_skills_dir(), name)
    if not os.path.isdir(skill_path):
        return False
    skill_md = os.path.join(skill_path, "SKILL.md")
    return os.path.isfile(skill_md)


def _run_git(args, timeout=120):
    """Run a git command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Git operation timed out"
    except FileNotFoundError:
        return -2, "", "Git not found in PATH"


def _git_version():
    """Check if git is available and return version string."""
    rc, out, _ = _run_git(["git", "--version"])
    if rc == 0:
        return out
    return None


def _clone_dependency(dep, dest_dir):
    """Clone a single dependency into the skills directory.

    Returns a status dict with: name, ok, message, action (installed/skipped/failed).
    """
    name = dep["name"]
    repo_url = dep["repo"]
    is_required = dep["required"]

    # Already installed
    if _is_installed(name):
        return {
            "name": name,
            "ok": True,
            "action": "already_installed",
            "message": f"✅ {name} 已安装",
        }

    # Check git availability
    git_ver = _git_version()
    if git_ver is None:
        msg = f"❌ {name} 安装失败：Git 不可用（PATH 中未找到 git）"
        if is_required:
            return {"name": name, "ok": False, "action": "failed", "message": msg}
        else:
            return {"name": name, "ok": True, "action": "skipped", "message": msg + "（非必需，已跳过）"}

    # Clone
    target = os.path.join(dest_dir, name)
    rc, out, err = _run_git([
        "git", "clone",
        "--depth", "1",
        "--single-branch",
        repo_url,
        target,
    ])

    if rc == 0:
        return {
            "name": name,
            "ok": True,
            "action": "installed",
            "message": f"✅ {name} 安装成功 → {target}",
        }
    else:
        msg = f"❌ {name} 安装失败：{err or out}"
        if is_required:
            return {"name": name, "ok": False, "action": "failed", "message": msg}
        else:
            return {"name": name, "ok": True, "action": "skipped", "message": msg + "（非必需，已跳过）"}


def _check_dependency(name):
    """Check if a dependency is installed without installing it."""
    installed = _is_installed(name)
    path = os.path.join(_skills_dir(), name)
    return {
        "name": name,
        "ok": installed,
        "installed": installed,
        "path": path if installed else None,
        "message": f"{'✅' if installed else '❌'} {name} {'已安装' if installed else '未安装'}",
    }


# ══════════════════════ MAIN ══════════════════════


def main(argv):
    check_only = "--check-only" in argv
    skip_nuwa = "--skip-nuwa" in argv

    if check_only:
        results = [_check_dependency(d["name"]) for d in DEPENDENCIES]
        all_ok = all(r["ok"] for r in results)
        output = {"ok": all_ok, "deps": results}
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0 if all_ok else 1

    # ── Install dependencies ──
    dest_dir = _skills_dir()
    os.makedirs(dest_dir, exist_ok=True)

    results = []
    for dep in DEPENDENCIES:
        if skip_nuwa and dep["name"] == "nuwa-skill":
            results.append({
                "name": dep["name"],
                "ok": True,
                "action": "skipped",
                "message": f"⏭️ {dep['name']} 已跳过（--skip-nuwa）",
            })
            continue
        result = _clone_dependency(dep, dest_dir)
        results.append(result)

    all_ok = all(r["ok"] for r in results)
    output = {"ok": all_ok, "deps": results}
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
