"""Kernel Tool Contract v1.0 — Unified tool execution protocol.

Every tool MUST:
  1. Return a ToolResult — never None, never a raw dict.
  2. Separate stdout from stderr — never mix them.
  3. Use structured error codes — never bare strings.

Runtime enforces this contract before accepting any tool result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


# ═══════════════════════════════════════════════════════════
# ERROR CODE REGISTRY
# ═══════════════════════════════════════════════════════════

class ToolErrorCode(StrEnum):
    """Structured error codes – one per known failure mode.

    Format: E{c}{nnn}{s}
      c = category digit (1=env, 2=code, 3=perm, 4=net, 5=fs, 9=unknown)
    """

    # Environment errors (E1xxx)
    PYTHON_NOT_FOUND   = "E1001"
    MODULE_NOT_FOUND   = "E1002"
    ENCODING_ERROR     = "E1003"
    SHELL_NOT_FOUND    = "E1004"

    # Code errors (E2xxx)
    IMPORT_FAILED       = "E2001"
    SYNTAX_ERROR        = "E2002"
    RUNTIME_ERROR       = "E2003"
    TEST_FAILURE        = "E2004"

    # Permission errors (E3xxx)
    PERMISSION_DENIED   = "E3001"
    APPROVAL_REQUIRED   = "E3002"
    BLOCKED_OPERATION   = "E3003"

    # Network errors (E4xxx)
    CONNECTION_REFUSED  = "E4001"
    TIMEOUT             = "E4002"
    API_ERROR           = "E4003"

    # File system errors (E5xxx)
    FILE_NOT_FOUND      = "E5001"
    DIRECTORY_NOT_FOUND = "E5002"
    WRITE_FAILED        = "E5003"
    DISK_FULL           = "E5004"

    # Unknown (E9xxx)
    UNKNOWN_ERROR       = "E9001"
    INTERNAL_ERROR      = "E9002"

    @classmethod
    def from_category(cls, cat: str) -> "ToolErrorCode":
        """Return the best-matching error code for a category."""
        return {
            "environment": cls.MODULE_NOT_FOUND,
            "code": cls.RUNTIME_ERROR,
            "permission": cls.PERMISSION_DENIED,
            "network": cls.CONNECTION_REFUSED,
            "filesystem": cls.WRITE_FAILED,
        }.get(cat, cls.UNKNOWN_ERROR)

    @property
    def category(self) -> str:
        """Extract the error category from the code."""
        prefix = self.value[1:2]  # first digit after 'E'
        return {
            "1": "environment", "2": "code", "3": "permission",
            "4": "network", "5": "filesystem", "9": "unknown",
        }.get(prefix, "unknown")


# ═══════════════════════════════════════════════════════════
# UNIFIED TOOL RESULT
# ═══════════════════════════════════════════════════════════

@dataclass
class ToolResult:
    """Unified tool execution result — the only allowed return type.

    Rules enforced by Runtime:
      - success: bool (required)
      - stdout: str  — main output (required, never None)
      - stderr: str  — error output (required, never None, "" if no errors)
      - error_code: ToolErrorCode — structured error (required on failure)
      - error_message: str — human-readable (required on failure)

    Migration from old ToolResult:
      Old: ToolResult(success=False, output="some error", error="")
      New: ToolResult(success=False, stdout="", stderr="some error",
                      error_code=ToolErrorCode.UNKNOWN_ERROR,
                      error_message="some error")
    """
    success: bool

    # Main output — always populated
    stdout: str = ""

    # Error output — always present, empty if success
    stderr: str = ""

    # Structured error (REQUIRED when success=False)
    error_code: str = ""

    # Human-readable error description (REQUIRED when success=False)
    error_message: str = ""

    # Optional structured data payload
    data: dict[str, Any] = field(default_factory=dict)

    # Timing (always present)
    duration_ms: float = 0.0

    def __post_init__(self):
        """Validate the contract."""
        if not isinstance(self.success, bool):
            raise ValueError(f"ToolResult.success must be bool, got {type(self.success)}")
        if self.stdout is None:
            self.stdout = ""
        if self.stderr is None:
            self.stderr = ""
        if not self.success and not self.error_code:
            self.error_code = ToolErrorCode.UNKNOWN_ERROR.value
        if not self.success and not self.error_message:
            self.error_message = self.stderr or self.stdout or "Tool execution failed"

    def validate(self) -> None:
        """Runtime calls this before accepting the result. Raises on violation."""
        if not isinstance(self.success, bool):
            raise ContractViolation(f"ToolResult.success must be bool, got {type(self.success).__name__}")
        if self.stdout is None:
            raise ContractViolation("ToolResult.stdout is None — must be str")
        if self.stderr is None:
            raise ContractViolation("ToolResult.stderr is None — must be str")
        if not self.success:
            if not self.error_code:
                raise ContractViolation("ToolResult.error_code is empty but success=False")
            if not self.error_message:
                raise ContractViolation("ToolResult.error_message is empty but success=False")

    def to_dict(self) -> dict:
        """Serialize for API/SSE/audit."""
        return {
            "success": self.success,
            "stdout": self.stdout[:500],
            "stderr": self.stderr[:500],
            "error_code": self.error_code,
            "error_message": self.error_message[:200],
            "duration_ms": self.duration_ms,
            "data_keys": list(self.data.keys()) if self.data else [],
        }

    # ── Backward-compatible accessors (v1.3 → v1.4 migration) ──

    @property
    def output(self) -> str:
        """Legacy: combined output. Use stdout/stderr for new code."""
        if self.success:
            return self.stdout
        # On failure, combine error info for LLM readability
        parts = []
        if self.stdout:
            parts.append(self.stdout)
        if self.error_message:
            parts.append(f"[{self.error_code}] {self.error_message}")
        if self.stderr:
            parts.append(f"Details: {self.stderr[:200]}")
        return "\n".join(parts) if parts else self.error_message

    @property
    def error(self) -> str:
        """Legacy: error text. Use error_code/error_message for new code."""
        return self.stderr or self.error_message or ""

    def to_legacy_dict(self) -> dict:
        """Return old-style dict for backward compat with tool_calls_log."""
        return {
            "tool": "",  # filled by caller
            "args": {},  # filled by caller
            "success": self.success,
            "output": self.output[:500],
        }

    def to_llm_message(self) -> str:
        """Format for injection into LLM message history."""
        if self.success:
            return self.stdout or "OK"
        parts = [f"[{self.error_code}] {self.error_message}"]
        if self.stdout:
            parts.append(f"Output: {self.stdout[:200]}")
        if self.stderr:
            parts.append(f"Details: {self.stderr[:200]}")
        return "\n".join(parts)

    # ── Factory methods ───────────────────────────────────

    @classmethod
    def ok(cls, stdout: str = "OK", stderr: str = "", data: dict | None = None,
           duration_ms: float = 0.0) -> "ToolResult":
        """Successful execution. stderr for warnings (non-fatal)."""
        return cls(success=True, stdout=stdout, stderr=stderr,
                   data=data or {}, duration_ms=duration_ms)

    @classmethod
    def fail(cls, error_code: ToolErrorCode | str, error_message: str,
             stdout: str = "", stderr: str = "", data: dict | None = None,
             duration_ms: float = 0.0) -> "ToolResult":
        """Failed execution with structured error."""
        code = error_code.value if isinstance(error_code, ToolErrorCode) else error_code
        return cls(success=False, stdout=stdout, stderr=stderr,
                   error_code=code, error_message=error_message,
                   data=data or {}, duration_ms=duration_ms)


class ContractViolation(Exception):
    """Raised when a tool returns an invalid ToolResult."""
    pass


# ═══════════════════════════════════════════════════════════
# CONTRACT-COMPATIBLE TOOL RESULT WRAPPER
# ═══════════════════════════════════════════════════════════

class ToolResultAdapter:
    """Wraps old-style tool results into the new contract format.

    Allows gradual migration — old tools that haven't been refactored
    yet can still produce compliant results through this adapter.
    """

    @staticmethod
    def from_legacy(success: bool, output: str = "", error: str = "",
                    tool_name: str = "unknown", duration_ms: float = 0.0,
                    data: Any = None) -> ToolResult:
        """Convert old-style (success, output, error) to new ToolResult.

        The old format mixed stdout and stderr into 'output' and had
        a separate 'error' field that was often empty even on failure.
        """
        if success:
            return ToolResult.ok(stdout=output or "", data=_unwrap_data(data),
                                duration_ms=duration_ms)

        # Failure — parse the best we can from mixed old format
        error_msg = error or output or f"{tool_name} failed"
        code = ToolContract.classify_error(error_msg)
        return ToolResult.fail(
            error_code=code,
            error_message=error_msg[:500],
            stdout=output if error else "",
            stderr=error or "",
            data=_unwrap_data(data),
            duration_ms=duration_ms,
        )


def _unwrap_data(data: Any) -> dict:
    """Safely convert legacy data to dict."""
    if data is None:
        return {}
    if isinstance(data, dict):
        return data
    return {"value": str(data)[:500]}


# ═══════════════════════════════════════════════════════════
# TOOL CONTRACT — maintains the error classification rules
# ═══════════════════════════════════════════════════════════

class ToolContract:
    """Central contract enforcement and error classification.

    Maps error patterns to structured error codes.
    This is the single source of truth — ErrorRecoveryManager
    reads from here instead of maintaining its own keyword list.
    """

    ERROR_MAP: list[tuple[list[str], ToolErrorCode]] = [
        (["python3", "python not found", "python 不是", "python is not"], ToolErrorCode.PYTHON_NOT_FOUND),
        (["modulenotfounderror", "no module named", "importerror: no module"], ToolErrorCode.MODULE_NOT_FOUND),
        (["encoding", "gbk", "utf-8", "decode error", "encode error"], ToolErrorCode.ENCODING_ERROR),
        (["syntaxerror", "indentationerror"], ToolErrorCode.SYNTAX_ERROR),
        (["importerror", "cannot import"], ToolErrorCode.IMPORT_FAILED),
        (["typeerror", "nameerror", "attributeerror", "valueerror", "keyerror",
          "indexerror", "runtimeerror", "traceback", "zerodivisionerror"], ToolErrorCode.RUNTIME_ERROR),
        (["test", "pytest", "assertion"], ToolErrorCode.TEST_FAILURE),
        (["permission denied", "access denied", "forbidden", "not permitted"], ToolErrorCode.PERMISSION_DENIED),
        (["approval", "批准", "blocked by"], ToolErrorCode.APPROVAL_REQUIRED),
        (["timeout", "timed out"], ToolErrorCode.TIMEOUT),
        (["connection refused", "connection error", "cannot connect"], ToolErrorCode.CONNECTION_REFUSED),
        (["api error", "401", "403", "500", "invalid api key"], ToolErrorCode.API_ERROR),
        (["file not found", "no such file", "not found"], ToolErrorCode.FILE_NOT_FOUND),
        (["directory not found", "no such directory"], ToolErrorCode.DIRECTORY_NOT_FOUND),
        (["write failed", "disk full", "cannot write"], ToolErrorCode.WRITE_FAILED),
    ]

    @classmethod
    def classify_error(cls, text: str) -> ToolErrorCode:
        """Classify an error string into a structured error code.

        Uses ordered pattern matching. First match wins.
        """
        if not text:
            return ToolErrorCode.UNKNOWN_ERROR
        tl = text.lower()
        for patterns, code in cls.ERROR_MAP:
            for p in patterns:
                if p in tl:
                    return code
        return ToolErrorCode.UNKNOWN_ERROR
