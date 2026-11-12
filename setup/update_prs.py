"""Publish and merge manifest-only release PRs from trusted default-branch code.

Never check out a candidate branch or execute candidate code. The App token belongs
only in this process's environment, after trusted checkout and setup have finished.
"""
import argparse
import base64
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import update_tools

MANIFEST = 'setup/tools.json'
BRANCH_PREFIX = 'deps/'
MARKER = re.compile(r'<!-- dotfiles-updater head=([0-9a-f]{40}) -->')


class GitHub:
    def __init__(self, repo):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
            raise ValueError('Invalid repository')
        self.repo = repo

    def api(self, endpoint, method='GET', data=None):
        command = ['gh', 'api', '-X', method, f'repos/{self.repo}/{endpoint}']
        if data is not None:
            command += ['--input', '-']
        result = subprocess.run(command, input=json.dumps(data) if data is not None else None,
                                text=True, capture_output=True, check=True)
        return json.loads(result.stdout) if result.stdout else None

    def pages(self, endpoint):
        result = subprocess.run(['gh', 'api', '--paginate', '--slurp', f'repos/{self.repo}/{endpoint}'],
                                text=True, capture_output=True, check=True)
        return [item for page in json.loads(result.stdout) for item in page]

    def manifest(self, sha):
        if not re.fullmatch(r'[0-9a-f]{40}', sha):
            raise ValueError('Expected immutable commit SHA')
        content = self.api(f'contents/{MANIFEST}?ref={sha}')
        if content.get('encoding') != 'base64':
            raise ValueError('Manifest must be a regular base64 GitHub contents response')
        return json.loads(base64.b64decode(content['content']))


def bot_owned(pr, bot_login, repo):
    return (pr['user']['login'] == bot_login and pr['user']['type'] == 'Bot'
            and pr['head']['repo']['full_name'] == repo
            and pr['head']['ref'].startswith(BRANCH_PREFIX)
            and re.fullmatch(r'deps/[a-z0-9][a-z0-9-]*', pr['head']['ref']) is not None)


def unchanged(pr):
    marker = MARKER.search(pr.get('body') or '')
    return bool(marker and marker.group(1) == pr['head']['sha'])


def verify_candidate(base, head, tool):
    """Re-fetch official assets and hashes; PR-provided checksums are never trusted."""
    update_tools.verify_manifest_change(base, head, tool)
    tag = head[tool]['version']
    expected = update_tools.prepare_update(copy.deepcopy(base), tool, tag)
    if expected != head:
        raise ValueError('Candidate differs from freshly verified official release')
    if update_tools.classify_update(base[tool]['version'], tag) != 'patch':
        raise ValueError('Only strict same-major/minor three-component patches may auto-merge')
    return tag


def verify_files(files):
    if len(files) != 1 or files[0]['filename'] != MANIFEST or files[0]['status'] != 'modified':
        raise ValueError('Expected only a modified setup/tools.json')


def verify_commits(commits, bot_login):
    if not commits or any((commit.get('author') or {}).get('login') != bot_login
                          or (commit.get('committer') or {}).get('login') != bot_login for commit in commits):
        raise ValueError('Candidate contains a commit not authored and committed by the updater bot')


def ci_success(run, pr, repo):
    return (run['name'] == 'CI' and run['path'] == '.github/workflows/ci.yml'
            and run['event'] == 'pull_request' and run['head_sha'] == pr['head']['sha']
            and run['head_repository']['full_name'] == repo
            and run['status'] == 'completed' and run['conclusion'] == 'success')


def body(tool, old, new, classification, sha):
    eligible = classification == 'patch'
    return (f'Updates **{tool}** from `{old}` to `{new}`.\n\n'
            f'Release notes: {release_url(tool, new)}\n\n'
            'Verified release assets: Linux x86_64 and aarch64'
            ' (fzf shell integration moves with fzf).\n\n'
            f'Auto-merge eligibility: {"strict patch; requires candidate CI" if eligible else "manual review required"}.\n\n'
            f'<!-- dotfiles-updater head={sha} -->')


def release_url(tool, tag):
    # Repository source is the trusted updater registry, not release response text.
    repository = update_tools.REGISTRY[tool]['repo']
    return f'https://github.com/{repository}/releases/tag/{tag}'


def publish(api, bot_login, selected=None):
    repo = api.api('')
    branch = repo['default_branch']
    base_sha = api.api(f'git/ref/heads/{branch}')['object']['sha']
    base = api.manifest(base_sha)
    updates = update_tools.check_updates(base, tools=[selected] if selected else None)
    if isinstance(updates, dict):
        updates = updates['updates']
    pulls = api.pages('pulls?state=open&per_page=100')
    for update in updates:
        if not update.get('available', False):
            print(f'Skipping {update["tool"]}: candidate assets unavailable')
            continue
        tool, tag = update['tool'], update['latest']
        branch_name = BRANCH_PREFIX + tool
        matches = [pr for pr in pulls if pr['head']['ref'] == branch_name]
        if len(matches) > 1:
            raise ValueError(f'Multiple PRs for {branch_name}')
        existing = matches[0] if matches else None
        parent = base_sha
        if existing:
            if not bot_owned(existing, bot_login, api.repo) or not unchanged(existing):
                print(f'Skipping {branch_name}: branch ownership or published head changed')
                continue
            verify_files(api.pages(f'pulls/{existing["number"]}/files?per_page=100'))
            verify_commits(api.pages(f'pulls/{existing["number"]}/commits?per_page=100'), bot_login)
            parent = existing['head']['sha']
        else:
            # A branch without the bot's PR is human-owned; never reuse or replace it.
            refs = api.pages('git/matching-refs/heads/deps/')
            if any(ref['ref'] == 'refs/heads/' + branch_name for ref in refs):
                print(f'Skipping {branch_name}: branch exists without an updater PR')
                continue
        candidate = update_tools.prepare_update(copy.deepcopy(base), tool, tag)
        if existing and api.manifest(parent) == candidate:
            comparison = api.api(f'compare/{base_sha}...{parent}')
            if comparison['merge_base_commit']['sha'] == base_sha:
                print(f'{branch_name}: already current')
                continue
        base_commit = api.api(f'git/commits/{base_sha}')
        blob = api.api('git/blobs', 'POST', {'content': json.dumps(candidate, indent=2) + '\n', 'encoding': 'utf-8'})
        tree = api.api('git/trees', 'POST', {'base_tree': base_commit['tree']['sha'], 'tree': [
            {'path': MANIFEST, 'mode': '100644', 'type': 'blob', 'sha': blob['sha']}]})
        # The API attributes the commit to the authenticated App installation bot.
        parents = [parent] if parent == base_sha else [parent, base_sha]
        commit = api.api('git/commits', 'POST', {'message': f'chore(deps): update {tool} to {tag}',
                                               'tree': tree['sha'], 'parents': parents})
        sha = commit['sha']
        if existing:
            current = api.api(f'git/ref/heads/{branch_name}')['object']['sha']
            if current != parent:
                raise ValueError(f'{branch_name} changed during publishing')
            # A concurrent human push is rejected by GitHub's fast-forward check.
            api.api(f'git/refs/heads/{branch_name}', 'PATCH', {'sha': sha, 'force': False})
        else:
            api.api('git/refs', 'POST', {'ref': 'refs/heads/' + branch_name, 'sha': sha})
        fields = {'title': f'chore(deps): update {tool} to {tag}',
                  'body': body(tool, base[tool]['version'], tag, update['classification'], sha)}
        if existing:
            api.api(f'pulls/{existing["number"]}', 'PATCH', fields)
        else:
            api.api('pulls', 'POST', dict(fields, head=branch_name, base=branch))


def merge(api, bot_login, run_id):
    run = api.api(f'actions/runs/{run_id}')
    if run['event'] != 'pull_request' or run['name'] != 'CI' or run['path'] != '.github/workflows/ci.yml':
        raise ValueError('Unexpected source workflow')
    repo = api.api('')
    default = repo['default_branch']
    # Honor repository opt-out even though merges use no persistent auto-merge queue.
    if not repo['allow_auto_merge']:
        print('Automatic updater merges remain disabled at repository level')
        return
    for pr in api.pages('pulls?state=open&per_page=100'):
        if not bot_owned(pr, bot_login, api.repo) or not unchanged(pr) or not ci_success(run, pr, api.repo):
            continue
        number, sha = pr['number'], pr['head']['sha']
        if pr['base']['ref'] != default or pr.get('draft'):
            continue
        if run.get('actor', {}).get('login') != bot_login:
            raise ValueError('CI was not triggered by the updater App bot')
        jobs = api.pages(f'actions/runs/{run_id}/jobs?filter=latest&per_page=100')
        checks = [job for job in jobs if job['name'] == 'ci']
        if len(checks) != 1 or checks[0]['conclusion'] != 'success':
            raise ValueError('Required aggregate ci check did not succeed')
        verify_files(api.pages(f'pulls/{number}/files?per_page=100'))
        verify_commits(api.pages(f'pulls/{number}/commits?per_page=100'), bot_login)
        tool = pr['head']['ref'].removeprefix(BRANCH_PREFIX)
        latest_base = api.api(f'git/ref/heads/{default}')['object']['sha']
        comparison = api.api(f'compare/{latest_base}...{sha}')
        merge_base = comparison['merge_base_commit']['sha']
        verify_candidate(api.manifest(merge_base), api.manifest(sha), tool)
        if merge_base != latest_base:
            print(f'PR #{number}: main advanced; refreshing bot PRs for fresh candidate CI')
            publish(api, bot_login)
            return
        current = api.api(f'pulls/{number}')
        if (current['head']['sha'] != sha or current['head']['ref'] != pr['head']['ref']
                or current['base']['ref'] != default
                or not bot_owned(current, bot_login, api.repo) or not unchanged(current)):
            raise ValueError('PR changed during verification')
        if api.api(f'git/ref/heads/{default}')['object']['sha'] != latest_base:
            print(f'PR #{number}: main advanced during verification; refreshing candidate CI')
            publish(api, bot_login)
            return
        # Merge immediately or fail; never arm a persistent queue for future heads.
        subprocess.run(['gh', 'pr', 'merge', str(number), '--repo', api.repo, '--squash',
                        '--match-head-commit', sha], check=True)
        if api.api(f'pulls/{number}').get('merged'):
            publish(api, bot_login)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('publish', 'merge'))
    parser.add_argument('--repo', required=True)
    parser.add_argument('--bot-login', required=True)
    parser.add_argument('--tool')
    parser.add_argument('--run-id', type=int)
    args = parser.parse_args()
    api = GitHub(args.repo)
    if not args.bot_login.endswith('[bot]'):
        parser.error('--bot-login must identify a GitHub App bot')
    if args.command == 'publish':
        publish(api, args.bot_login, args.tool)
    else:
        if args.run_id is None:
            parser.error('merge requires --run-id')
        merge(api, args.bot_login, args.run_id)


if __name__ == '__main__':
    main()
