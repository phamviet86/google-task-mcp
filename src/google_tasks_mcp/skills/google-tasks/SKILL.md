---
name: google-tasks
description: Read and manage a user's Google Tasks through the local Google Tasks MCP server with safe confirmation and patch semantics.
---

# Google Tasks MCP usage

Use the configured local `google-tasks-mcp` server to work with the user's Google Tasks. It exposes
exactly 14 tools: `list_task_lists`, `get_task_list`, `create_task_list`, `update_task_list`,
`delete_task_list`, `list_tasks`, `get_task`, `create_task`, `update_task`, `complete_task`,
`reopen_task`, `move_task`, `delete_task`, and `clear_completed_tasks`.

## Work safely

Resolve a human-readable task-list name with `list_task_lists`, then read the list or task before
changing an existing resource when current state matters. Use the returned IDs. After an uncertain
write result or API error, re-read the affected resource before retrying; do not blindly repeat a
write.

Creating a list or task is additive and has a non-destructive annotation, but still needs the
user's request. Renaming, updating, moving, completing, and reopening affect existing user data;
treat their conservative destructive-risk annotations as a prompt to confirm the intended target
and outcome. The user's exact authorization for that named action is sufficient to perform it.
For `delete_task_list`, `delete_task`, or `clear_completed_tasks`, require explicit authorization
for the named target and then provide `confirm: true`; reuse exact existing authorization in the
current request, otherwise ask. Clearing completed tasks hides completed tasks through Google's
clear operation; it is not a substitute for a general deletion preview.

## Preserve patch intent

For `update_task`, omit every field the user wants left unchanged. Send explicit `null` only to
clear `notes` or `due`; `null` for `title` or `status` is invalid. A due value may be `YYYY-MM-DD`
or RFC 3339, but Google Tasks retains only the date. Use `complete_task` and `reopen_task` for
clear status intent rather than combining unrelated updates.

Use `list_tasks` pagination and filters deliberately. To inspect completed tasks as shown in
Google's first-party clients, request both `show_completed: true` and `show_hidden: true`. Keep
task titles and notes within the server's validation limits, and never request or expose OAuth
credentials while handling task work.
