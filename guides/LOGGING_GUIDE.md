# Logging System Usage Guide

The logging system has been separated into its own modular cog (`cogs/logging.py`) that provides versatile logging capabilities for all other cogs.

## Key Features

- **Thread-based logging**: Track activities in Discord threads with persistent embed logs
- **Custom logging**: Create and update custom log entries with unique identifiers  
- **Simple messaging**: Send one-off log messages with optional embeds
- **Plug-and-play**: Easy to integrate into any new cog

## How to Use in Your Cogs

### 1. Get the Logging Cog Instance
```python
logging_cog = self.bot.get_cog("LoggingSystem")
if not logging_cog:
    return  # Logging system not available
```

### 2. Thread-Based Logging
```python
# Create a thread log with custom fields
await logging_cog.create_thread_log(
    thread,
    title="Custom Thread Title",
    description="Description here",
    color=discord.Color.blue(),
    fields={
        "Status": "Active",
        "Events": "*No events yet*",
        "Custom Field": "Custom Value"
    }
)

# Update thread log fields
await logging_cog.update_thread_log(
    thread,
    field_updates={"Status": "Completed"},
    event_additions={"Events": "New event occurred"}
)
```

### 3. Custom Logging with Identifiers
```python
# Create a custom log
await logging_cog.create_custom_log(
    identifier="my_unique_id",
    title="My Activity Log",
    description="Description",
    color=discord.Color.green(),
    fields={"Status": "In Progress"}
)

# Update the custom log later
await logging_cog.update_custom_log(
    identifier="my_unique_id",
    field_updates={"Status": "Completed"},
    event_additions={"Events": "Task finished"}
)
```

### 4. Simple Message Logging
```python
# Log a simple message
await logging_cog.log_simple_message("Something happened!")

# Log with an embed
embed = discord.Embed(title="Event", description="Details")
await logging_cog.log_simple_message("", embed=embed)
```

## Configuration

The logging system uses the `log_channel` setting from `data/config.yaml`:

```yaml
log_channel: 123456789012345678  # Your log channel ID
```

## Example Implementation

See `cogs/example_cog.py` for a complete example of how to integrate the logging system into a new cog.

## Migration from Old System

The Rep cog has been updated to use the new logging system. Key changes:
- `_update_thread_log()` calls replaced with `logging_cog.update_thread_log()`
- `_ensure_thread_log()` replaced with `logging_cog.create_thread_log()`
- Parameters restructured to use dictionaries for better organization

## Loading Order

Make sure to load the logging cog before other cogs that depend on it in `bot.py`:

```python
await bot.load_extension("cogs.logging")
await bot.load_extension("cogs.rep")  # Depends on logging
```