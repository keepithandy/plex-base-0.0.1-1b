"""Shared output spelling checks for Windows filesystem aliases."""

from pathlib import PureWindowsPath


def require_unambiguous_windows_destination(path: PureWindowsPath) -> None:
    # Validate before and after resolve(): Win32 aliases nonexistent names too.
    if str(path).startswith(("\\\\?\\", "\\\\.\\")) or (path.drive and not path.root):
        raise ValueError("Output destinations must use ordinary Windows paths")
    reserved = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"} | {
        prefix + suffix for prefix in ("COM", "LPT")
        for suffix in "123456789\u00b9\u00b2\u00b3"
    }
    for part in path.parts[1:] if path.anchor else path.parts:
        if part in {".", ".."}:
            continue
        if (part != part.rstrip(" .")
                or part.split(".")[0].rstrip(" ").upper() in reserved
                or any(char in '<>:"|?*' or ord(char) < 32 for char in part)):
            raise ValueError("Output destinations must not use ambiguous Windows names")
