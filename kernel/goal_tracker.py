"""GoalTracker — task completion detection for Agent Runtime (v1.2)

Detects whether a user's task requirements have been fulfilled,
enabling the Agent Runtime to exit early instead of burning iterations.

Strategy: parse user goal for explicit numbered requirements,
track tool outputs against them, signal completion.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class GoalItem:
    """A single sub-goal extracted from the user's request."""
    index: int
    text: str                      # e.g. "创建项目目录"
    fulfilled: bool = False
    evidence: str = ""              # How it was fulfilled (tool + output)

    def to_dict(self) -> dict:
        return {"index": self.index, "text": self.text, "fulfilled": self.fulfilled, "evidence": self.evidence}


@dataclass
class GoalTracker:
    """Tracks completion progress toward a multi-step goal.

    Usage in Agent Runtime:
        tracker = GoalTracker(user_goal)
        # After each tool call:
        tracker.observe(tool_name, success, output)
        if tracker.all_fulfilled():
            break  # early exit
    """

    goal_text: str = ""
    items: list[GoalItem] = field(default_factory=list)
    tool_log: list[dict] = field(default_factory=list)

    def __post_init__(self):
        if self.goal_text and not self.items:
            self.items = self._extract_goals(self.goal_text)

    @staticmethod
    def _extract_goals(text: str) -> list[GoalItem]:
        """Parse numbered requirements from the user's goal text.

        Matches patterns like:
          "1. 创建项目目录" / "1) 创建项目目录"
          "要求：1. 创建..." / "要求: 1. 创建..."
          "Step 1: create project"
        """
        import re
        items = []

        # Match numbered items: 1. / 1) / 1、
        pattern = re.compile(r'(?:^|\n)\s*(\d+)[.、\)）]\s*(.+?)(?=\n\s*\d+[.、\)）]|\n\n|\Z)', re.MULTILINE | re.DOTALL)
        matches = pattern.findall(text)

        # Also try to find list after "要求" / "需求" / "tasks" markers
        if not matches:
            marker_pattern = re.compile(r'(?:要求|需求|任务|goals?|tasks?)[：:]\s*\n?(.+)', re.IGNORECASE | re.DOTALL)
            marker_match = marker_pattern.search(text)
            if marker_match:
                content = marker_match.group(1)
                matches = pattern.findall(content)

        for idx_str, item_text in matches:
            try:
                idx = int(idx_str)
                items.append(GoalItem(index=idx, text=item_text.strip()[:120]))
            except ValueError:
                pass

        if items:
            logger.info("GoalTracker: extracted %d sub-goals from user request", len(items))

        return items

    def observe(self, tool_name: str, success: bool, output: str) -> None:
        """Feed a tool execution result into the tracker. Checks for fulfillment."""
        self.tool_log.append({"tool": tool_name, "success": success, "output": output[:200]})

        if not self.items:
            return

        combined = (tool_name + " " + output).lower()

        for item in self.items:
            if item.fulfilled:
                continue

            # Check file write targets
            if tool_name == "write_file":
                # Look for keyword overlap with the goal item
                item_keywords = item.text.lower()
                for word in item_keywords.split():
                    if len(word) >= 3 and word in combined:
                        item.fulfilled = True
                        item.evidence = f"write_file: {output[:100]}"
                        break

            # Shell execution
            if tool_name == "shell" and success:
                item_keywords = item.text.lower()
                if any(w in combined for w in ["test", "测试", "运行", "pytest"]) and \
                   any(w in item_keywords for w in ["test", "测试", "运行", "验证", "执行"]):
                    item.fulfilled = True
                    item.evidence = f"shell: {output[:100]}"

            # save_to_memory / search_memory
            if tool_name in ("save_to_memory", "search_memory"):
                if any(w in item.text for w in ["记忆", "保存", "record", "save"]):
                    item.fulfilled = True
                    item.evidence = f"{tool_name}: {output[:100]}"

    def all_fulfilled(self) -> bool:
        """Returns True if all extracted goals are fulfilled."""
        if not self.items:
            return False  # No explicit goals — let max_iter handle it
        return all(item.fulfilled for item in self.items)

    def progress(self) -> dict:
        """Return completion progress."""
        if not self.items:
            return {"items": 0, "fulfilled": 0, "pct": 0, "detail": []}
        fulfilled = sum(1 for i in self.items if i.fulfilled)
        return {
            "items": len(self.items),
            "fulfilled": fulfilled,
            "pct": round(fulfilled / len(self.items) * 100),
            "detail": [i.to_dict() for i in self.items],
        }

    def remaining(self) -> list[GoalItem]:
        return [i for i in self.items if not i.fulfilled]


# Error classifier for tool failures
class ErrorClassifier:
    """Categorize tool errors to decide recovery strategy."""

    FATAL_PATTERNS = ["api key", "authentication", "permission denied", "access denied"]
    NEED_HUMAN_PATTERNS = ["approval", "批准", "blocked by", "requires human"]
    RETRYABLE_PATTERNS = ["timeout", "connection", "temporary", "retry", "busy"]

    @staticmethod
    def classify(tool_name: str, error: str, consecutive_failures: int) -> str:
        """Returns: 'retry' | 'need_human' | 'fatal' | 'skip'"""
        el = error.lower()

        if consecutive_failures >= 3:
            return "fatal"  # 3 consecutive failures → stop

        for p in ErrorClassifier.FATAL_PATTERNS:
            if p in el:
                return "fatal"

        for p in ErrorClassifier.NEED_HUMAN_PATTERNS:
            if p in el:
                return "need_human"

        for p in ErrorClassifier.RETRYABLE_PATTERNS:
            if p in el:
                return "retry"

        return "skip"  # Don't retry automatically
