"""Reads and writes the bot's YAML configuration (data/config.yaml)."""
import copy
import os
import tempfile
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.error import CommentMark
from ruamel.yaml.tokens import CommentToken

# Resolve paths from the project root so the bot works no matter which
# directory it is started from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / 'data' / 'config.yaml'

# Round-trip mode keeps comments, key order and quoting when saving
_yaml = YAML()
_yaml.preserve_quotes = True
_yaml.width = 4096  # don't re-wrap long TOS text
_yaml.indent(mapping=2, sequence=4, offset=2)  # match the example file's list indentation

ID_LIST_KEYS = ("forums", "admin_ids", "admin_role_ids")
DEFAULTS = {
    "auto_close_enabled": True,
    "auto_close_hours": 24,
    "admin_close_confirmation": True,
    "tos_timeout_seconds": 30,
    "tos_message": "Please accept the marketplace terms. This post closes {timeout} if you don't respond.",
    "tos_decline_response": "Marketplace terms not accepted. Thread will now be closed.",
}
BOT_STATUS_DEFAULTS = {
    "enabled": True,
    "activity_type": "watching",
    "message": "marketplace reviews",
    "status_type": "online",
}

_cache: CommentedMap | None = None
_cache_mtime: float | None = None


def _to_int(value) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


_TRUE_WORDS = ("true", "yes", "y", "on")
_FALSE_WORDS = ("false", "no", "n", "off")


def _to_bool(value, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        # YAML 1.2 (ruamel) reads yes/no/on/off as text; older configs used them as booleans
        word = value.strip().lower()
        if word in _TRUE_WORDS:
            return True
        if word in _FALSE_WORDS:
            return False
    return default


# ─── Comment-preserving list edits ──────────────────────────────────────────
# ruamel attaches the blank lines and comments that follow a list (which
# belong to the next key) to the list's last item. Plain append/remove would
# leave them in the middle of the list or delete them, so these helpers move
# that trailing text along with the end of the list.

def _split_trailing(token) -> tuple[str, str]:
    """Split a list item's comment into (its own end-of-line part, text that follows the list)."""
    value = token.value
    end_of_line = value[:value.index("\n") + 1] if "\n" in value else value
    return end_of_line, value[len(end_of_line):]


def _take_trailing(seq: CommentedSeq) -> str:
    """Detach the text following the list from its last item and return it."""
    if not seq:
        return ""
    last = len(seq) - 1
    entry = seq.ca.items.get(last)
    if not entry or entry[0] is None:
        return ""
    end_of_line, rest = _split_trailing(entry[0])
    if end_of_line.strip():
        entry[0].value = end_of_line
    else:
        del seq.ca.items[last]
    return rest


def _give_trailing(parent: CommentedMap, key: str, seq: CommentedSeq, text: str) -> None:
    """Re-attach text that follows the list to its (new) last item, or to the key if it is empty."""
    if not text:
        return
    if seq:
        last = len(seq) - 1
        entry = seq.ca.items.get(last)
        if entry and entry[0] is not None:
            entry[0].value += text
        else:
            seq.yaml_add_eol_comment("x", last)
            seq.ca.items[last][0].value = "\n" + text
    else:
        # An empty list is written as `key: []`, which can't carry a comment
        # after it, so the text goes before the next key instead
        keys = list(parent)
        position = keys.index(key)
        if position + 1 >= len(keys):
            return
        token = CommentToken(text, CommentMark(0), None)
        slot = parent.ca.items.setdefault(keys[position + 1], [None, None, None, None])
        slot[1] = [token] + (slot[1] or [])


def list_append(config: CommentedMap, key: str, value) -> None:
    """Append to a top-level list in the config without displacing comments."""
    seq = config[key]
    trailing = _take_trailing(seq)
    seq.append(value)
    _give_trailing(config, key, seq, trailing)


def list_remove(config: CommentedMap, key: str, value) -> None:
    """Remove from a top-level list in the config without losing comments."""
    seq = config[key]
    trailing = _take_trailing(seq)
    del seq[seq.index(value)]  # ruamel shifts the remaining items' comments
    _give_trailing(config, key, seq, trailing)


def _clamp_int(value, default: int, low: int, high: int) -> int:
    number = _to_int(value)
    return default if number is None else max(low, min(high, number))


def normalize(config) -> CommentedMap:
    """
    Coerce hand-edited values into the types the bot expects, in place.

    YAML turns an empty key into None and quoted IDs into strings; without
    this, `admin_ids:` left empty or `log_channel: "123"` would crash
    commands or silently never match.
    """
    if not isinstance(config, dict):
        config = CommentedMap()
    _normalize_id_lists(config)
    _normalize_scalars(config)
    _normalize_bot_status(config)
    return config


def _normalize_id_lists(config) -> None:
    for key in ID_LIST_KEYS:
        values = config.get(key)
        if not isinstance(values, list):
            config[key] = CommentedSeq()
            continue
        # Convert in place so per-item comments survive saving
        for i in reversed(range(len(values))):
            number = _to_int(values[i])
            if number is None:
                del values[i]
            elif values[i] != number or not isinstance(values[i], int):
                values[i] = number


def _normalize_scalars(config) -> None:
    for key in ("guild_id", "log_channel"):
        config[key] = _to_int(config.get(key)) if config.get(key) is not None else None

    for key in ("auto_close_enabled", "admin_close_confirmation"):
        config[key] = _to_bool(config.get(key), DEFAULTS[key])
    config["auto_close_hours"] = _clamp_int(config.get("auto_close_hours"), DEFAULTS["auto_close_hours"], 1, 168)
    config["tos_timeout_seconds"] = _clamp_int(config.get("tos_timeout_seconds"), DEFAULTS["tos_timeout_seconds"], 5, 900)

    for key in ("tos_message", "tos_decline_response"):
        if not isinstance(config.get(key), str) or not config[key].strip():
            config[key] = DEFAULTS[key]

    if not isinstance(config.get("no_rep_messages"), list):
        config["no_rep_messages"] = CommentedSeq()


def _normalize_bot_status(config) -> None:
    bot_status = config.get("bot_status")
    if not isinstance(bot_status, dict):
        bot_status = config["bot_status"] = CommentedMap()
    for key, default in BOT_STATUS_DEFAULTS.items():
        if key == "enabled":
            bot_status[key] = _to_bool(bot_status.get(key), default)
        elif not isinstance(bot_status.get(key), str) or not bot_status[key].strip():
            bot_status[key] = default


def load_config() -> CommentedMap:
    """
    Return the current configuration, normalized.

    The file is re-read only when it changes on disk, so manual edits still
    take effect without a restart. Callers get their own copy and may modify
    it freely before passing it to save_config().
    """
    global _cache, _cache_mtime
    mtime = os.path.getmtime(CONFIG_PATH)
    if _cache is None or mtime != _cache_mtime:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            _cache = normalize(_yaml.load(f))
        _cache_mtime = mtime
    return copy.deepcopy(_cache)


def save_config(config) -> None:
    """Write the configuration atomically, keeping comments, key order and emoji."""
    global _cache, _cache_mtime
    config = normalize(config)
    _cache = copy.deepcopy(config)
    _strip_unchanged_defaults(config)
    fd, tmp_path = tempfile.mkstemp(dir=CONFIG_PATH.parent, prefix='.config-', suffix='.yaml')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            _yaml.dump(config, f)
        os.replace(tmp_path, CONFIG_PATH)
    except BaseException:
        os.unlink(tmp_path)
        raise
    _cache_mtime = os.path.getmtime(CONFIG_PATH)


def _strip_unchanged_defaults(config) -> None:
    """
    Don't write keys that normalize() filled in with defaults and nobody
    changed, so saving doesn't add clutter like `guild_id: null` to the file.
    """
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            on_disk = _yaml.load(f) or {}
    except FileNotFoundError:
        on_disk = {}
    defaults = {**DEFAULTS, "guild_id": None, "log_channel": None, "no_rep_messages": [],
                **{key: [] for key in ID_LIST_KEYS}}
    for key, default in defaults.items():
        if key not in on_disk and key in config and config[key] == default:
            del config[key]


def get_forum_ids(config) -> list[int]:
    """Tracked forum channel IDs as ints."""
    return list(normalize(config)["forums"])
