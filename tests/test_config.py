from claude_agent_sdk._cli_version import __cli_version__

from autofx.config import DEFAULT_MODEL, MIN_CLAUDE_CODE_VERSION


def _version_tuple(version: str) -> tuple:
    return tuple(int(part) for part in version.split("."))


def test_bundled_claude_code_supports_default_model():
    assert _version_tuple(__cli_version__) >= _version_tuple(MIN_CLAUDE_CODE_VERSION), (
        f"claude-agent-sdk bundles Claude Code {__cli_version__}, but {DEFAULT_MODEL} "
        f"needs {MIN_CLAUDE_CODE_VERSION} or newer"
    )
