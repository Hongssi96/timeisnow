"""Load trusted packaged instructions without provider calls or user data."""
import json
from dataclasses import dataclass, field
from importlib.resources import files


class PromptLoadError(RuntimeError):
    """Safe configuration error without instruction text or filesystem paths."""


@dataclass(frozen=True)
class PromptBlock:
    version: str
    role: str
    content: str = field(repr=False)


@dataclass(frozen=True)
class PromptBundle:
    system: PromptBlock
    developer: PromptBlock

    @property
    def prompt_version(self):
        return self.developer.version

    def messages(self):
        """Fresh instruction messages; input JSON belongs in a separate message."""
        return [{'role': block.role, 'content': block.content}
                for block in (self.system, self.developer)]


_TASK_VERSIONS = {
    'walking_estimate': 'walking_estimate.v1',
    'journey_explanation': 'journey_explanation.v2',
}


def _read_block(version, role):
    try:
        data = json.loads(files('app.ai.prompts').joinpath(version + '.json').read_text(encoding='utf-8'))
    except (OSError, UnicodeError, ValueError):
        raise PromptLoadError('PROMPT_RESOURCE_INVALID') from None
    if (not isinstance(data, dict) or set(data) != {'version', 'role', 'content'}
            or data['version'] != version or data['role'] != role
            or not isinstance(data['content'], str) or not data['content'].strip()):
        raise PromptLoadError('PROMPT_RESOURCE_INVALID')
    return PromptBlock(version=version, role=role, content=data['content'])


def load_prompt(task, *, expected_version=None):
    """Load an allowlisted task with common.v1; reject unsupported or stale versions.

    No cache: version and text are read together on each load.
    Schedule interpretation has its own SYSTEM and is outside this registry.
    """
    if not isinstance(task, str) or task not in _TASK_VERSIONS:
        raise PromptLoadError('PROMPT_TASK_UNSUPPORTED')
    version = _TASK_VERSIONS[task]
    if expected_version is not None and expected_version != version:
        raise PromptLoadError('PROMPT_VERSION_MISMATCH')
    return PromptBundle(system=_read_block('common.v1', 'system'),
                        developer=_read_block(version, 'developer'))
