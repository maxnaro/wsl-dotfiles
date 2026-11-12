"""Fixture-only tests for privileged updater decisions; no live API calls."""
import copy
import importlib.util
from pathlib import Path
import sys
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'setup'))
SPEC = importlib.util.spec_from_file_location('update_prs', ROOT / 'setup/update_prs.py')
updater = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(updater)
BOT = 'dotfiles-updater[bot]'
REPO = 'owner/repo'
HEAD = 'a' * 40
BASE = 'b' * 40
BASE_MANIFEST = {'nvim': {'version': 'v0.11.5', 'assets': {}}}
HEAD_MANIFEST = {'nvim': {'version': 'v0.11.6', 'assets': {}}}


class GitHubRequests(unittest.TestCase):
    def test_repository_endpoint_has_no_trailing_slash(self):
        for endpoint, expected in (('', 'repos/owner/repo'), ('git/ref/heads/main', 'repos/owner/repo/git/ref/heads/main')):
            with self.subTest(endpoint=endpoint), patch.object(updater.subprocess, 'run', return_value=
                    subprocess.CompletedProcess([], 0, stdout='{}')) as run:
                updater.GitHub(REPO).api(endpoint)
                self.assertEqual(run.call_args.args[0], ['gh', 'api', '-X', 'GET', expected])


def pull():
    return {'number': 12, 'user': {'login': BOT, 'type': 'Bot'},
            'head': {'sha': HEAD, 'ref': 'deps/nvim', 'repo': {'full_name': REPO}},
            'base': {'ref': 'main'}, 'body': f'<!-- dotfiles-updater head={HEAD} -->', 'draft': False}


def workflow():
    return {'name': 'CI', 'path': '.github/workflows/ci.yml', 'event': 'pull_request',
            'head_sha': HEAD, 'head_repository': {'full_name': REPO}, 'actor': {'login': BOT},
            'status': 'completed', 'conclusion': 'success'}


class FixtureAPI:
    repo = REPO

    def __init__(self):
        self.pr = pull()
        self.run = workflow()
        self.files = [{'filename': updater.MANIFEST, 'status': 'modified'}]
        self.commits = [{'author': {'login': BOT}, 'committer': {'login': BOT}}]
        self.jobs = [{'name': 'ci', 'conclusion': 'success'}]
        self.calls = []
        self.merge_result = {'merged': True}
        self.merge_failure = None

    def api(self, endpoint, method='GET', data=None):
        self.calls.append((endpoint, method, data))
        if endpoint == '':
            return {'default_branch': 'main', 'allow_auto_merge': True}
        if endpoint == 'actions/runs/1':
            return self.run
        if endpoint == 'git/ref/heads/main':
            return {'object': {'sha': BASE}}
        if endpoint.startswith('compare/'):
            return {'merge_base_commit': {'sha': BASE}}
        if endpoint == 'pulls/12/merge' and method == 'PUT':
            if self.merge_failure:
                raise self.merge_failure
            return self.merge_result
        if endpoint == 'pulls/12':
            return self.pr
        raise AssertionError(endpoint)

    def pages(self, endpoint):
        if endpoint.startswith('pulls?'):
            return [self.pr]
        if '/files?' in endpoint:
            return self.files
        if '/commits?' in endpoint:
            return self.commits
        if endpoint.startswith('actions/runs/1/jobs?'):
            return self.jobs
        raise AssertionError(endpoint)

    def manifest(self, sha):
        return copy.deepcopy(BASE_MANIFEST if sha == BASE else HEAD_MANIFEST)


class UpdatePRPolicy(unittest.TestCase):
    def test_only_same_repository_app_bot_branch_is_owned(self):
        self.assertTrue(updater.bot_owned(pull(), BOT, REPO))
        for field, value in [('user', {'login': 'human', 'type': 'User'}),
                             ('head', {'sha': HEAD, 'ref': 'deps/nvim', 'repo': {'full_name': 'fork/repo'}})]:
            candidate = pull()
            candidate[field] = value
            self.assertFalse(updater.bot_owned(candidate, BOT, REPO))

    def test_marker_rejects_human_modified_head(self):
        self.assertTrue(updater.unchanged(pull()))
        candidate = pull()
        candidate['head']['sha'] = BASE
        self.assertFalse(updater.unchanged(candidate))

    def test_diff_must_only_modify_manifest(self):
        updater.verify_files([{'filename': updater.MANIFEST, 'status': 'modified'}])
        for files in ([], [{'filename': updater.MANIFEST, 'status': 'added'}],
                      [{'filename': '.github/workflows/ci.yml', 'status': 'modified'}],
                      [{'filename': updater.MANIFEST, 'status': 'modified'}, {'filename': 'setup/update_prs.py'}]):
            with self.assertRaises(ValueError):
                updater.verify_files(files)

    def test_commits_need_bot_author_and_committer(self):
        updater.verify_commits([{'author': {'login': BOT}, 'committer': {'login': BOT}}], BOT)
        for commits in ([], [{'author': None, 'committer': {'login': BOT}}],
                        [{'author': {'login': BOT}, 'committer': {'login': 'human'}}]):
            with self.assertRaises(ValueError):
                updater.verify_commits(commits, BOT)

    def test_ci_requires_exact_head_workflow_source_and_conclusion(self):
        self.assertTrue(updater.ci_success(workflow(), pull(), REPO))
        for field, value in [('head_sha', BASE), ('event', 'push'), ('conclusion', 'skipped'),
                             ('path', '.github/workflows/fake.yml'), ('head_repository', {'full_name': 'fork/repo'})]:
            run = workflow()
            run[field] = value
            self.assertFalse(updater.ci_success(run, pull(), REPO))

    def test_candidate_must_match_fresh_official_hashes(self):
        with patch.object(updater.update_tools, 'verify_manifest_change'), \
             patch.object(updater.update_tools, 'prepare_update', return_value={'forged': 'hash'}), \
             patch.object(updater.update_tools, 'classify_update', return_value='patch'):
            with self.assertRaisesRegex(ValueError, 'freshly verified'):
                updater.verify_candidate(BASE_MANIFEST, HEAD_MANIFEST, 'nvim')

    def test_nonpatch_never_auto_merges(self):
        for classification in ('minor', 'major', 'non-semver', 'unknown'):
            with patch.object(updater.update_tools, 'verify_manifest_change'), \
                 patch.object(updater.update_tools, 'prepare_update', return_value=HEAD_MANIFEST), \
                 patch.object(updater.update_tools, 'classify_update', return_value=classification):
                with self.assertRaisesRegex(ValueError, 'strict'):
                    updater.verify_candidate(BASE_MANIFEST, HEAD_MANIFEST, 'nvim')

    def test_merge_uses_immediate_api_with_immutable_expected_head(self):
        api = FixtureAPI()
        with patch.object(updater, 'verify_candidate') as verify, patch.object(updater, 'publish') as publish:
            updater.merge(api, BOT, 1)
        verify.assert_called_once_with(BASE_MANIFEST, HEAD_MANIFEST, 'nvim')
        mutations = [call for call in api.calls if call[1] != 'GET']
        self.assertEqual(mutations, [('pulls/12/merge', 'PUT', {'sha': HEAD, 'merge_method': 'squash'})])
        publish.assert_called_once_with(api, BOT)

    def test_repository_auto_merge_opt_out_stops_immediate_bot_merges(self):
        api = FixtureAPI()
        original = api.api

        def request(endpoint, method='GET', data=None):
            if endpoint == '':
                return {'default_branch': 'main', 'allow_auto_merge': False}
            return original(endpoint, method, data)

        api.api = request
        with patch.object(updater.subprocess, 'run') as run:
            updater.merge(api, BOT, 1)
            run.assert_not_called()

    def test_pending_remote_gate_fails_without_arming_auto_merge(self):
        for failure in (None, updater.subprocess.CalledProcessError(1, ['gh', 'api'])):
            api = FixtureAPI()
            api.merge_result = {'merged': False, 'message': 'Required gate is pending'}
            api.merge_failure = failure
            with patch.object(updater, 'verify_candidate'), patch.object(updater, 'publish') as publish:
                expected_error = updater.subprocess.CalledProcessError if failure else ValueError
                with self.assertRaises(expected_error):
                    updater.merge(api, BOT, 1)
                mutations = [call for call in api.calls if call[1] != 'GET']
                self.assertEqual(mutations, [('pulls/12/merge', 'PUT', {'sha': HEAD, 'merge_method': 'squash'})])
                publish.assert_not_called()

    def test_merge_rejects_nonbot_run_actor_or_failed_aggregate(self):
        for mutate in (lambda api: api.run.update(actor={'login': 'human'}),
                       lambda api: api.jobs[0].update(conclusion='skipped'),
                       lambda api: api.files.append({'filename': 'setup/update_prs.py', 'status': 'modified'})):
            api = FixtureAPI()
            mutate(api)
            with patch.object(updater.subprocess, 'run') as run:
                with self.assertRaises(ValueError):
                    updater.merge(api, BOT, 1)
                run.assert_not_called()
                self.assertTrue(all(method == 'GET' for _, method, _ in api.calls))

    def test_outdated_ci_or_modified_branch_never_attempts_merge(self):
        for mutate in (lambda api: api.run.update(head_sha=BASE),
                       lambda api: api.pr.update(body='human edited branch')):
            api = FixtureAPI()
            mutate(api)
            with patch.object(updater.subprocess, 'run') as run:
                updater.merge(api, BOT, 1)
                run.assert_not_called()
                self.assertTrue(all(method == 'GET' for _, method, _ in api.calls))

    def test_stale_main_refreshes_without_merging_old_ci(self):
        api = FixtureAPI()
        original = api.api

        def request(endpoint, method='GET', data=None):
            if endpoint.startswith('compare/'):
                return {'merge_base_commit': {'sha': 'c' * 40}}
            return original(endpoint, method, data)

        api.api = request
        with patch.object(updater, 'verify_candidate'), patch.object(updater, 'publish') as publish, \
             patch.object(updater.subprocess, 'run') as run:
            updater.merge(api, BOT, 1)
            publish.assert_called_once_with(api, BOT)
            run.assert_not_called()

    def test_publish_preserves_human_owned_branch(self):
        api = FixtureAPI()
        api.pr['user'] = {'login': 'human', 'type': 'User'}
        updates = {'updates': [{'tool': 'nvim', 'latest': 'v0.11.6', 'classification': 'patch', 'available': True}]}
        with patch.object(updater.update_tools, 'check_updates', return_value=updates), \
             patch.object(updater.update_tools, 'prepare_update') as prepare:
            updater.publish(api, BOT)
            prepare.assert_not_called()
        self.assertTrue(all(method == 'GET' for _, method, _ in api.calls))

    def test_publish_preserves_bot_branch_after_human_push(self):
        api = FixtureAPI()
        api.pr['head']['sha'] = 'c' * 40
        updates = {'updates': [{'tool': 'nvim', 'latest': 'v0.11.6', 'classification': 'patch', 'available': True}]}
        with patch.object(updater.update_tools, 'check_updates', return_value=updates), \
             patch.object(updater.update_tools, 'prepare_update') as prepare:
            updater.publish(api, BOT)
            prepare.assert_not_called()
        self.assertTrue(all(method == 'GET' for _, method, _ in api.calls))


if __name__ == '__main__':
    unittest.main()
