        # Additional checks for shell commands
        if name == "shell":
            command = args.get("command", "")
            command_lower = command.lower()
            for pattern in CRITICAL_COMMANDS:
                if pattern.lower() in command_lower:
                    return ApprovalResult(
                        blocked=True, needs_approval=False,
                        reason=f"禁止：命令包含危险操作 '{pattern}'"
                    )
            for pattern in DANGEROUS_PATTERNS:
                # Case-insensitive match to prevent bypass via case variation
                if pattern.lower() in command_lower:
                    risk = "dangerous"
                    break

        # Additional checks for file operations
        if name == "write_file":
            path = args.get("path", "")
            path_lower = path.lower()
            for pattern in DANGEROUS_PATTERNS:
                # Case-insensitive match to prevent bypass via case variation
                if pattern.lower() in path_lower:
                    return ApprovalResult(
                        blocked=False, needs_approval=True,
                        reason=f"需要批准：写入敏感路径 '{path}'"
                    )
