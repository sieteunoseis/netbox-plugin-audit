"""Check GitHub repository health and activity."""

import json
import re
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone

from . import CategoryResult, CheckResult, Severity


def _get_github_repo(plugin_path: str) -> str | None:
    """Extract GitHub owner/repo from git remote URL."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            cwd=plugin_path,
            timeout=5,
        )
        if result.returncode != 0:
            return None
        url = result.stdout.strip()
        m = re.search(r"github\.com[/:]([^/]+/[^/.]+?)(?:\.git)?$", url)
        return m.group(1) if m else None
    except Exception:
        return None


def _github_api(url: str) -> dict | list | None:
    """Make a GitHub API request."""
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/vnd.github.v3+json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def check_github(plugin_path: str, pkg_dir: str | None) -> CategoryResult:
    """Check GitHub repository health indicators."""
    cat = CategoryResult(name="GitHub Health", icon="G")
    results = cat.results

    repo = _get_github_repo(plugin_path)
    if not repo:
        results.append(CheckResult("github_repo", Severity.INFO, "Not a GitHub repository (skipped)"))
        return cat

    # Fetch repo metadata
    repo_data = _github_api(f"https://api.github.com/repos/{repo}")
    if not repo_data or isinstance(repo_data, list):
        results.append(CheckResult("github_api", Severity.INFO, "Could not fetch GitHub repo data"))
        return cat

    # --- Archived check ---
    if repo_data.get("archived", False):
        results.append(CheckResult("archived", Severity.ERROR, "Repository is archived (no longer maintained)"))
    else:
        results.append(CheckResult("archived", Severity.PASS, "Repository is not archived"))

    # --- Last activity ---
    pushed_at = repo_data.get("pushed_at", "")
    if pushed_at:
        try:
            pushed_dt = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            days_ago = (now - pushed_dt).days

            if days_ago <= 90:
                results.append(CheckResult("last_push", Severity.PASS, f"Last push: {days_ago} days ago (active)"))
            elif days_ago <= 365:
                results.append(
                    CheckResult("last_push", Severity.WARNING, f"Last push: {days_ago} days ago (may be stale)")
                )
            else:
                results.append(
                    CheckResult("last_push", Severity.ERROR, f"Last push: {days_ago} days ago (likely unmaintained)")
                )
        except Exception:
            pass

    # --- Stars and forks (community health) ---
    stars = repo_data.get("stargazers_count", 0)
    forks = repo_data.get("forks_count", 0)
    results.append(CheckResult("community", Severity.PASS, f"Stars: {stars}, Forks: {forks}"))

    # --- Open issues ---
    has_issues = repo_data.get("has_issues", True)
    open_issues = repo_data.get("open_issues_count", 0)

    if not has_issues:
        results.append(CheckResult("issues_enabled", Severity.INFO, "Issues are disabled on this repository"))
    else:
        results.append(CheckResult("issues_enabled", Severity.PASS, "Issues are enabled"))

        if open_issues == 0:
            results.append(CheckResult("open_issues", Severity.PASS, "No open issues"))
        elif open_issues <= 20:
            results.append(CheckResult("open_issues", Severity.PASS, f"{open_issues} open issues"))
        elif open_issues <= 50:
            results.append(
                CheckResult("open_issues", Severity.WARNING, f"{open_issues} open issues (consider triaging)")
            )
        else:
            results.append(
                CheckResult("open_issues", Severity.WARNING, f"{open_issues} open issues (significant backlog)")
            )

        # Check for stale issues (fetch open issues sorted by updated)
        issues_data = _github_api(
            f"https://api.github.com/repos/{repo}/issues?state=open&sort=updated&direction=asc&per_page=5"
        )
        if issues_data and isinstance(issues_data, list):
            # Filter out pull requests (GitHub API includes PRs in issues endpoint)
            real_issues = [i for i in issues_data if "pull_request" not in i]
            if real_issues:
                oldest = real_issues[0]
                updated_at = oldest.get("updated_at", "")
                try:
                    updated_dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                    now = datetime.now(timezone.utc)
                    stale_days = (now - updated_dt).days
                    if stale_days > 365:
                        results.append(
                            CheckResult(
                                "stale_issues",
                                Severity.WARNING,
                                f"Oldest open issue untouched for {stale_days} days",
                            )
                        )
                    elif stale_days > 180:
                        results.append(
                            CheckResult(
                                "stale_issues",
                                Severity.INFO,
                                f"Oldest open issue untouched for {stale_days} days",
                            )
                        )
                    else:
                        results.append(CheckResult("stale_issues", Severity.PASS, "No significantly stale issues"))
                except Exception:
                    pass

    # --- Open pull requests ---
    prs_data = _github_api(f"https://api.github.com/repos/{repo}/pulls?state=open&per_page=1")
    if prs_data is not None and isinstance(prs_data, list):
        # We only fetched 1 per page, but the Link header would tell us total
        # Use the issues_count minus issues-only count as an estimate
        # Or just report what we know
        if len(prs_data) == 0:
            results.append(CheckResult("open_prs", Severity.PASS, "No open pull requests"))
        else:
            # Fetch count more accurately
            prs_all = _github_api(f"https://api.github.com/repos/{repo}/pulls?state=open&per_page=100")
            if prs_all and isinstance(prs_all, list):
                pr_count = len(prs_all)
                if pr_count <= 5:
                    results.append(CheckResult("open_prs", Severity.PASS, f"{pr_count} open pull request(s)"))
                elif pr_count <= 15:
                    results.append(
                        CheckResult("open_prs", Severity.WARNING, f"{pr_count} open pull requests (review backlog)")
                    )
                else:
                    results.append(
                        CheckResult(
                            "open_prs", Severity.WARNING, f"{pr_count} open pull requests (significant backlog)"
                        )
                    )

    # --- Default branch ---
    default_branch = repo_data.get("default_branch", "")
    if default_branch in ("main", "master", "develop", "dev"):
        results.append(CheckResult("default_branch", Severity.PASS, f"Default branch: {default_branch}"))
    elif default_branch:
        results.append(CheckResult("default_branch", Severity.INFO, f"Default branch: {default_branch} (non-standard)"))

    return cat
