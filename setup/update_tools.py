#!/usr/bin/env python3
"""Review and atomically update pinned tools from their official GitHub releases."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import urllib.parse
import urllib.request


# This trusted map is code, never metadata supplied by a release or pull request.
UPSTREAM = {
    'fzf': ('junegunn/fzf', 'v', 'fzf-{version}-linux_amd64.tar.gz', 'fzf-{version}-linux_arm64.tar.gz'),
    'bat': ('sharkdp/bat', 'v', 'bat-{tag}-x86_64-unknown-linux-musl.tar.gz', 'bat-{tag}-aarch64-unknown-linux-musl.tar.gz'),
    'eza': ('eza-community/eza', 'v', 'eza_x86_64-unknown-linux-musl.tar.gz', 'eza_aarch64-unknown-linux-gnu.tar.gz'),
    'fastfetch': ('fastfetch-cli/fastfetch', '', 'fastfetch-linux-amd64.tar.gz', 'fastfetch-linux-aarch64.tar.gz'),
    'nvim': ('neovim/neovim', 'v', 'nvim-linux-x86_64.tar.gz', 'nvim-linux-arm64.tar.gz'),
    'fish': ('fish-shell/fish-shell', '', 'fish-{version}-linux-x86_64.tar.xz', 'fish-{version}-linux-aarch64.tar.xz'),
    'lazygit': ('jesseduffield/lazygit', 'v', 'lazygit_{version}_linux_x86_64.tar.gz', 'lazygit_{version}_linux_arm64.tar.gz'),
    'rg': ('BurntSushi/ripgrep', '', 'ripgrep-{version}-x86_64-unknown-linux-musl.tar.gz', 'ripgrep-{version}-aarch64-unknown-linux-musl.tar.gz'),
    'zoxide': ('ajeetdsouza/zoxide', 'v', 'zoxide-{version}-x86_64-unknown-linux-musl.tar.gz', 'zoxide-{version}-aarch64-unknown-linux-musl.tar.gz'),
    'sesh': ('joshmedeski/sesh', 'v', 'sesh_Linux_x86_64.tar.gz', 'sesh_Linux_arm64.tar.gz'),
    'atuin': ('atuinsh/atuin', 'v', 'atuin-x86_64-unknown-linux-musl.tar.gz', 'atuin-aarch64-unknown-linux-musl.tar.gz'),
    'tmux': ('tmux/tmux', '', 'tmux-{version}.tar.gz', 'tmux-{version}.tar.gz'),
}
REGISTRY = {tool: {'repo': spec[0]} for tool, spec in UPSTREAM.items()}
ARCHES = ('x86_64', 'aarch64')
FZF_FILES = {'fzf-completion': 'completion.bash', 'fzf-key-bindings': 'key-bindings.bash'}
SHA256 = re.compile(r'[0-9a-f]{64}\Z')
SEMVER = re.compile(r'v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z')
MAX_PAGES = 5
PAGE_SIZE = 100


def parse_version(value):
    """Accept only three numeric components and an optional leading v."""
    match = SEMVER.fullmatch(value) if isinstance(value, str) else None
    return tuple(map(int, match.groups())) if match else None


parse = parse_version


def classify_update(old, new):
    if old == new:
        return 'none'
    before, after = parse_version(old), parse_version(new)
    if before is None or after is None:
        return 'manual'
    if after < before:
        return 'downgrade'
    if after == before:
        return 'none'
    return 'major' if after[0] != before[0] else 'minor' if after[1] != before[1] else 'patch'


def canonical_tag(tool, tag):
    if not isinstance(tag, str) or tool not in UPSTREAM:
        return False
    if tool == 'tmux':
        return re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)[a-z]?', tag) is not None
    version = parse_version(tag)
    return version is not None and tag == UPSTREAM[tool][1] + '.'.join(map(str, version))


def tag_key(tool, tag):
    if tool == 'tmux':
        match = re.fullmatch(r'(\d+)\.(\d+)([a-z]?)', tag)
        return (int(match[1]), int(match[2]), match[3])
    return parse_version(tag)


def asset_names(tool, tag):
    if not canonical_tag(tool, tag):
        raise ValueError(f'Noncanonical tag for {tool}: {tag}')
    return dict(zip(ARCHES, [template.format(tag=tag, version=tag.removeprefix('v'))
                            for template in UPSTREAM[tool][2:]]))


def release_url(tool, tag, name):
    return f'https://github.com/{UPSTREAM[tool][0]}/releases/download/{tag}/{name}'


def script_url(tag, filename):
    return f'https://raw.githubusercontent.com/junegunn/fzf/{tag}/shell/{filename}'


class GitHubClient:
    """Token goes only to api.github.com; release downloads never receive it."""
    def read(self, url):
        headers = {'User-Agent': 'dotfiles-release-updater', 'Accept': 'application/vnd.github+json'}
        if urllib.parse.urlparse(url).netloc == 'api.github.com':
            token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
            if token:
                headers['Authorization'] = f'Bearer {token}'
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
            return response.read()

    def json(self, url):
        return json.loads(self.read(url))


def releases(tool, client):
    result = []
    repo = UPSTREAM[tool][0]
    for page in range(1, MAX_PAGES + 1):
        batch = client.json(f'https://api.github.com/repos/{repo}/releases?per_page={PAGE_SIZE}&page={page}')
        if not isinstance(batch, list):
            raise ValueError('Invalid GitHub release list')
        result.extend(item for item in batch if not item.get('draft') and not item.get('prerelease')
                      and canonical_tag(tool, item.get('tag_name')))
        if len(batch) < PAGE_SIZE:
            break
    return sorted(result, key=lambda item: tag_key(tool, item['tag_name']), reverse=True)


def release_assets(release):
    assets = release.get('assets', [])
    names = [asset.get('name') for asset in assets]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate release asset names')
    return {asset['name']: asset for asset in assets}


def checksum_names(tool, tag, name):
    version = tag.removeprefix('v')
    return (name + '.sha256', name + '.sha256sum', 'checksums.txt',
            f'fzf_{version}_checksums.txt', f'lazygit_{version}_checksums.txt',
            'sha256.sum', 'sha256sum.txt', 'sha256sums.txt', 'SHA256SUMS', 'shasum.txt', 'SHASUMS256.txt')


def official_digest(tool, tag, name, assets, client):
    asset = assets.get(name)
    if asset is None or asset.get('browser_download_url') != release_url(tool, tag, name):
        raise ValueError(f'Missing official asset: {tool} {tag} {name}')
    digest = asset.get('digest')
    if digest is not None:
        if not isinstance(digest, str) or not digest.startswith('sha256:') or not SHA256.fullmatch(digest[7:]):
            raise ValueError(f'Invalid official SHA-256 digest: {name}')
        return digest[7:]
    for checksum_name in checksum_names(tool, tag, name):
        checksum = assets.get(checksum_name)
        if checksum is None:
            continue
        url = release_url(tool, tag, checksum_name)
        if checksum.get('browser_download_url') != url:
            raise ValueError('Unofficial checksum URL')
        content = client.read(url)
        checksum_digest = checksum.get('digest')
        if checksum_digest is not None and checksum_digest != 'sha256:' + hashlib.sha256(content).hexdigest():
            raise ValueError('Checksum document digest mismatch')
        for line in content.decode('utf-8').splitlines():
            # Standard sha256sum form, or a single digest in an asset-specific file.
            match = re.fullmatch(r'([0-9a-fA-F]{64})(?:\s+\*?(.+))?', line.strip())
            if match and (match[2] == name or (match[2] is None and checksum_name == name + '.sha256')):
                return match[1].lower()
            match = re.fullmatch(r'SHA256 \((.+)\) = ([0-9a-fA-F]{64})', line.strip())
            if match and match[1] == name:
                return match[2].lower()
    raise ValueError(f'No official SHA-256 for {name}')


def validate_release(tool, tag, release):
    if release.get('tag_name') != tag or release.get('draft') or release.get('prerelease'):
        raise ValueError('Expected a stable release at the requested tag')
    if not canonical_tag(tool, tag):
        raise ValueError('Noncanonical release tag')


def package_assets(tool, tag, release, client, download=False):
    validate_release(tool, tag, release)
    assets, result = release_assets(release), {}
    for arch, name in asset_names(tool, tag).items():
        digest = official_digest(tool, tag, name, assets, client)
        url = release_url(tool, tag, name)
        if download and hashlib.sha256(client.read(url)).hexdigest() != digest:
            raise ValueError(f'Checksum mismatch: {url}')
        result[arch] = {'url': url, 'sha256': digest}
    return result


def check_updates(manifest, tools=None, client=None):
    client = client or GitHubClient()
    selected = list(tools) if tools else [tool for tool, spec in manifest.items()
                                        if 'version' in spec and 'file' not in spec]
    if len(selected) != len(set(selected)):
        selected = list(dict.fromkeys(selected))
    results = []
    for tool in selected:
        if tool not in UPSTREAM or tool not in manifest or 'file' in manifest[tool]:
            raise ValueError(f'Unsupported binary tool: {tool}')
        current = manifest[tool]['version']
        row = {'tool': tool, 'current': current, 'latest': current, 'classification': 'none'}
        candidates = releases(tool, client)
        if candidates and tag_key(tool, candidates[0]['tag_name']) > tag_key(tool, current):
            release = candidates[0]
            tag = release['tag_name']
            row.update(latest=tag, classification=classify_update(current, tag))
            try:
                package_assets(tool, tag, release, client)
                row['available'] = True
            except ValueError as error:
                row.update(available=False, error=str(error))
        results.append(row)
    return {'updates': results}


def prepare_update(manifest, tool, tag, client=None):
    client = client or GitHubClient()
    if tool not in UPSTREAM or tool not in manifest or not canonical_tag(tool, tag):
        raise ValueError(f'Unsupported tool or noncanonical tag: {tool} {tag}')
    old = manifest[tool]['version']
    if not canonical_tag(tool, old) or tag_key(tool, tag) <= tag_key(tool, old):
        raise ValueError('Update must advance the pinned version')
    release = client.json(f'https://api.github.com/repos/{UPSTREAM[tool][0]}/releases/tags/{tag}')
    assets = package_assets(tool, tag, release, client, download=True)
    updated = copy.deepcopy(manifest)
    updated[tool]['version'] = tag
    if tool == 'tmux':
        updated[tool]['source'] = assets['x86_64']
    else:
        updated[tool]['assets'] = assets
    if tool == 'fzf':
        for companion, filename in FZF_FILES.items():
            if companion not in updated or updated[companion].get('file') != filename:
                raise ValueError('Missing expected fzf companion')
            url = script_url(tag, filename)
            updated[companion]['version'] = tag
            updated[companion]['assets'] = {'all': {'url': url, 'sha256': hashlib.sha256(client.read(url)).hexdigest()}}
    verify_manifest_change(manifest, updated, tool)
    return updated


def verify_manifest_change(base, head, tool):
    """Validate a single package diff against trusted templates; no network or execution.

    This checks structure, URLs, version direction and hashes, not upstream hash
    authenticity. Trusted CI can compare prepare_update(base, tool, tag) to head.
    """
    if not isinstance(base, dict) or not isinstance(head, dict):
        raise ValueError('Manifest must be an object')
    if tool not in UPSTREAM or tool not in base or set(base) != set(head):
        raise ValueError('Unknown tool or changed manifest packages')
    group = {tool} | (set(FZF_FILES) if tool == 'fzf' else set())
    if any(base[key] != head[key] for key in base if key not in group):
        raise ValueError('Changes outside the selected package group')
    before, after = base[tool], head[tool]
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise ValueError('Package must be an object')
    old, tag = before.get('version'), after.get('version')
    if not canonical_tag(tool, old) or not canonical_tag(tool, tag) or tag_key(tool, tag) <= tag_key(tool, old):
        raise ValueError('Expected canonical forward version change')
    for key in group:
        if key not in head:
            raise ValueError('Missing package companion')
        previous, current = base[key], head[key]
        if not isinstance(previous, dict) or not isinstance(current, dict):
            raise ValueError('Package must be an object')
        mutable = {'version', 'source' if key == 'tmux' else 'assets'}
        if set(previous) != set(current) or any(previous[field] != current[field] for field in previous if field not in mutable):
            raise ValueError('Unexpected package metadata change')
        if current.get('version') != tag:
            raise ValueError('Package versions must advance together')
        if key == 'tmux':
            expected = {'source': release_url(tool, tag, asset_names(tool, tag)['x86_64'])}
            actual = {'source': current.get('source')}
        elif key in FZF_FILES:
            if current.get('file') != FZF_FILES[key]:
                raise ValueError('Invalid companion filename')
            expected = {'all': script_url(tag, FZF_FILES[key])}
            actual = current.get('assets', {})
        else:
            expected = {arch: release_url(tool, tag, name) for arch, name in asset_names(tool, tag).items()}
            actual = current.get('assets', {})
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError('Unexpected architecture set')
        for arch, url in expected.items():
            asset = actual[arch]
            if not isinstance(asset, dict) or set(asset) != {'url', 'sha256'} or asset.get('url') != url or not isinstance(asset.get('sha256'), str) or not SHA256.fullmatch(asset['sha256']):
                raise ValueError('Invalid official asset URL or SHA-256')
    return classify_update(old, tag)


def apply_update(path, tool, tag, client=None):
    path = Path(path)
    original = path.read_bytes()
    updated = prepare_update(json.loads(original), tool, tag, client)
    staged = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, prefix='.' + path.name + '-', delete=False) as stream:
            staged = Path(stream.name)
            stream.write(json.dumps(updated, indent=2) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        staged.chmod(path.stat().st_mode & 0o777)
        if path.read_bytes() != original:
            raise ValueError('Manifest changed during update')
        os.replace(staged, path)
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)
    return updated


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--check', action='store_true')
    action.add_argument('--apply', metavar='TOOL')
    parser.add_argument('--tool', action='append', help='Limit --check to this binary tool (repeatable)')
    parser.add_argument('--tag')
    parser.add_argument('--manifest', type=Path, default=Path(__file__).with_name('tools.json'))
    args = parser.parse_args(argv)
    if args.check and args.tag or args.apply and (not args.tag or args.tool):
        parser.error('--apply requires --tag; --tool is only valid with --check')
    try:
        if args.check:
            result = check_updates(json.loads(args.manifest.read_text()), args.tool)
        else:
            apply_update(args.manifest, args.apply, args.tag)
            result = {'tool': args.apply, 'version': args.tag}
        print(json.dumps(result, sort_keys=True))
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
