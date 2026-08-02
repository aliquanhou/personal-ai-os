"""Tool Contract Protocol Tests — 20 cases verifying v1.4 unified ToolResult.

Covers: factory methods, validation, backward compat, error classification,
         None safety, Shell stdout/stderr separation, legacy adapter.
"""

import pytest
from kernel.tool_contract import (
    ToolResult, ToolErrorCode, ToolContract, ContractViolation,
    ToolResultAdapter,
)


class TestToolResultFactory:
    """Tests 1-5: Factory method correctness."""

    def test_01_ok_factory(self):
        r = ToolResult.ok("hello world", data={"lines": 3}, duration_ms=150.0)
        assert r.success is True
        assert r.stdout == "hello world"
        assert r.stderr == ""
        assert r.error_code == ""
        assert r.duration_ms == 150.0
        assert r.data == {"lines": 3}

    def test_02_fail_factory(self):
        r = ToolResult.fail(ToolErrorCode.FILE_NOT_FOUND, "file missing",
                           stderr="os error 2")
        assert r.success is False
        assert r.error_code == "E5001"
        assert r.error_message == "file missing"
        assert r.stderr == "os error 2"

    def test_03_fail_auto_code(self):
        """failing without error_code should default to UNKNOWN_ERROR."""
        r = ToolResult(success=False, error_message="something broke")
        assert r.success is False
        assert r.error_code == "E9001"  # UNKNOWN_ERROR

    def test_04_fail_default_message(self):
        """failing without error_message should derive from stderr/stdout."""
        r = ToolResult(success=False, stdout="", stderr="disk full")
        assert r.error_message == "disk full"

    def test_05_none_coercion(self):
        """None stdout/stderr must become empty string."""
        r = ToolResult(success=True)
        assert r.stdout == ""
        assert r.stderr == ""


class TestToolResultValidation:
    """Tests 6-9: Contract enforcement."""

    def test_06_validate_ok(self):
        r = ToolResult.ok("a")
        r.validate()  # should not raise

    def test_07_validate_fail_auto_fills_code(self):
        """__post_init__ auto-fills missing error_code to UNKNOWN_ERROR."""
        r = ToolResult(success=False, error_code="", error_message="err")
        r.validate()  # should not raise — auto-filled
        assert r.error_code == ToolErrorCode.UNKNOWN_ERROR.value

    def test_08_validate_fail_auto_fills_message(self):
        """__post_init__ auto-fills missing error_message from stderr."""
        r = ToolResult(success=False, error_code="E5001", error_message="")
        r.validate()  # should not raise — auto-filled
        assert r.error_message != ""

    def test_09_validate_none_stdout(self):
        r = ToolResult.ok("x")
        r.stdout = None  # type: ignore — simulating tool returning None
        with pytest.raises(ContractViolation):
            r.validate()


class TestBackwardCompat:
    """Tests 10-13: Legacy field accessors."""

    def test_10_output_on_success(self):
        r = ToolResult.ok("hello")
        assert r.output == "hello"

    def test_11_output_on_failure(self):
        r = ToolResult.fail(ToolErrorCode.MODULE_NOT_FOUND, "no pandas")
        assert "no pandas" in r.output
        assert "E1002" in r.output

    def test_12_error_property(self):
        r = ToolResult.fail(ToolErrorCode.TIMEOUT, "cmd timeout", stderr="killed")
        assert "killed" in r.error

    def test_13_error_property_empty(self):
        r = ToolResult.ok("ok")
        assert r.error == ""


class TestErrorClassification:
    """Tests 14-17: Structured error code classification."""

    def test_14_python_not_found(self):
        assert ToolContract.classify_error("python3 不是内部或外部命令") == ToolErrorCode.PYTHON_NOT_FOUND

    def test_15_module_not_found(self):
        assert ToolContract.classify_error("ModuleNotFoundError: No module named 'pandas'") == ToolErrorCode.MODULE_NOT_FOUND

    def test_16_import_error(self):
        assert ToolContract.classify_error("ImportError: cannot import name 'foo'") == ToolErrorCode.IMPORT_FAILED

    def test_17_encoding_error(self):
        assert ToolContract.classify_error("UnicodeDecodeError: 'gbk' codec can't decode") == ToolErrorCode.ENCODING_ERROR

    def test_17b_permission_denied(self):
        assert ToolContract.classify_error("Permission denied: /etc/config") == ToolErrorCode.PERMISSION_DENIED


class TestShellSeparation:
    """Tests 18-19: ShellTool stdout/stderr must be separate."""

    def test_18_ok_has_empty_stderr(self):
        r = ToolResult.ok(stdout="Hello from Python", duration_ms=100)
        assert r.stderr == ""
        assert r.success is True

    def test_19_fail_separates_stdout_stderr(self):
        r = ToolResult.fail(ToolErrorCode.RUNTIME_ERROR, "traceback",
                           stdout="partial output",
                           stderr="Traceback (most recent call last):\n  File ...",
                           data={"exit_code": 1})
        assert r.stdout == "partial output"
        assert "Traceback" in r.stderr
        assert r.error_code == "E2003"


class TestLegacyAdapter:
    """Test 20: Old-style (success, output, error) migration."""

    def test_20_legacy_to_contract(self):
        r = ToolResultAdapter.from_legacy(
            success=False,
            output="some mixed output",
            error="",
            tool_name="shell",
            duration_ms=500.0,
        )
        assert r.success is False
        assert r.error_code != ""  # should have been auto-classified
        assert r.stderr == ""  # old format had error="" so stderr is empty
        # output from old format goes to stdout on failure with adapter
        # Actually the adapter puts output into error_message when no error text
        assert "some mixed output" in r.error_message
