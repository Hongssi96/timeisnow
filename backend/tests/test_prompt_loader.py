"""Document/resource parity and safe loading, without DB or AI access."""
import json
import os
import re
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.ai.prompt_loader import PromptLoadError, load_prompt


class PromptLoaderTests(unittest.TestCase):
    def test_document_blocks_and_versions_match_exactly(self):
        source = Path(__file__).resolve().parents[2].joinpath('ai_prompts.md').read_text(encoding='utf-8')
        for task, version, section in [('walking_estimate', 'walking_estimate.v1', 3),
                                       ('journey_explanation', 'journey_explanation.v2', 6)]:
            bundle = load_prompt(task, expected_version=version)
            self.assertEqual(bundle.prompt_version, version)
            for block, number in [(bundle.system, 2), (bundle.developer, section)]:
                pattern = rf'^## {number}\. [^\n]* — {re.escape(block.version)}\n(.*?)(?=^## |\Z)'
                found = re.search(pattern, source, re.M | re.S)
                self.assertIsNotNone(found)
                text = re.search(r'^```text\n(.*?)\n```', found.group(1), re.M | re.S).group(1)
                self.assertEqual(block.content, text)
            self.assertEqual([item['role'] for item in bundle.messages()], ['system', 'developer'])

    def test_load_independent_of_working_directory(self):
        original = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                self.assertEqual(load_prompt('walking_estimate').prompt_version, 'walking_estimate.v1')
            finally:
                os.chdir(original)

    def test_untrusted_task_cannot_select_files_or_schedule_system(self):
        for task in ['../../secret', 'common', 'schedule_interpretation', '', None, []]:
            with self.subTest(task=task), patch('app.ai.prompt_loader.files') as resources:
                with self.assertRaisesRegex(PromptLoadError, '^PROMPT_TASK_UNSUPPORTED$'):
                    load_prompt(task)
                resources.assert_not_called()

    def test_wrong_version_fails_before_reading(self):
        with patch('app.ai.prompt_loader.files') as resources:
            with self.assertRaisesRegex(PromptLoadError, '^PROMPT_VERSION_MISMATCH$'):
                load_prompt('walking_estimate', expected_version='walking_estimate.v2')
            resources.assert_not_called()

    def test_missing_or_unreadable_resource_has_safe_error(self):
        for error in [FileNotFoundError('private/path'), UnicodeError('private text')]:
            with patch('app.ai.prompt_loader.files') as resources:
                resources.return_value.joinpath.return_value.read_text.side_effect = error
                with self.assertRaisesRegex(PromptLoadError, '^PROMPT_RESOURCE_INVALID$') as caught:
                    load_prompt('walking_estimate')
                self.assertNotIn('private', str(caught.exception))

    def test_malformed_or_mismatched_blocks_are_rejected(self):
        valid = {'version': 'common.v1', 'role': 'system', 'content': 'trusted text'}
        invalid = ['{private', 'null', '[]', json.dumps({**valid, 'content': ' '}),
                   json.dumps({**valid, 'content': 123}), json.dumps({**valid, 'role': 'user'}),
                   json.dumps({**valid, 'version': 'common.v2'}), json.dumps({**valid, 'extra': True})]
        for raw in invalid:
            with self.subTest(raw=raw), patch('app.ai.prompt_loader.files') as resources:
                resources.return_value.joinpath.return_value.read_text.return_value = raw
                with self.assertRaisesRegex(PromptLoadError, '^PROMPT_RESOURCE_INVALID$'):
                    load_prompt('walking_estimate')

    def test_developer_failure_never_returns_partial_bundle(self):
        with patch('app.ai.prompt_loader.files') as resources:
            resources.return_value.joinpath.return_value.read_text.side_effect = [
                json.dumps({'version': 'common.v1', 'role': 'system', 'content': 'trusted'}),
                json.dumps({'version': 'walking_estimate.v1', 'role': 'user', 'content': 'wrong role'})]
            with self.assertRaises(PromptLoadError):
                load_prompt('walking_estimate')

    def test_bundle_is_immutable_and_message_edits_do_not_leak(self):
        bundle = load_prompt('walking_estimate')
        with self.assertRaises(FrozenInstanceError):
            bundle.developer.content = 'changed'
        messages = bundle.messages()
        messages[0]['content'] = 'untrusted input'
        self.assertNotEqual(bundle.messages()[0]['content'], 'untrusted input')
        self.assertNotIn(bundle.developer.content, repr(bundle))


if __name__ == '__main__':
    unittest.main()
