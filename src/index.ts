#!/usr/bin/env node
import { McpServer } from "@modelcontextprotocol/server";
import { serveStdio } from "@modelcontextprotocol/server/stdio";
import * as z from "zod/v4";
import { getTasksClient, googleError, normalizeDueDate } from "./google.js";

const readOnly = { readOnlyHint: true, destructiveHint: false, idempotentHint: true } as const;
const write = { readOnlyHint: false, destructiveHint: false, idempotentHint: false } as const;
const destructive = { readOnlyHint: false, destructiveHint: true, idempotentHint: false } as const;

function success(data: unknown) {
  return { content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }] };
}

async function call<T>(operation: () => Promise<T>) {
  try {
    return success(await operation());
  } catch (error) {
    return {
      isError: true,
      content: [{ type: "text" as const, text: googleError(error) || "Unknown Google Tasks API error" }],
    };
  }
}

const taskListId = z.string().min(1).describe("Google task list ID; obtain it from list_task_lists");
const taskId = z.string().min(1).describe("Google task ID; obtain it from list_tasks");
const due = z
  .string()
  .describe("Due date as YYYY-MM-DD or RFC 3339. Google Tasks stores only the date and discards the time.");

function createServer(): McpServer {
  const server = new McpServer(
    { name: "google-tasks-mcp", version: "0.1.0" },
    {
      instructions:
        "Manage the authenticated user's Google Tasks. Resolve human names to IDs with list_task_lists/list_tasks before writes. Google Tasks due values are dates only; times are discarded. Ask the user before calling tools marked destructive.",
    },
  );

  server.registerTool(
    "list_task_lists",
    {
      description: "List the authenticated user's Google task lists.",
      inputSchema: z.object({
        max_results: z.number().int().min(1).max(100).default(100),
        page_token: z.string().optional(),
      }),
      annotations: readOnly,
    },
    ({ max_results, page_token }) =>
      call(async () => {
        const api = await getTasksClient();
        const { data } = await api.tasklists.list({ maxResults: max_results, pageToken: page_token });
        return { task_lists: data.items ?? [], next_page_token: data.nextPageToken ?? null };
      }),
  );

  server.registerTool(
    "get_task_list",
    {
      description: "Get one Google task list by ID.",
      inputSchema: z.object({ task_list_id: taskListId }),
      annotations: readOnly,
    },
    ({ task_list_id }) =>
      call(async () => (await (await getTasksClient()).tasklists.get({ tasklist: task_list_id })).data),
  );

  server.registerTool(
    "create_task_list",
    {
      description: "Create a Google task list.",
      inputSchema: z.object({ title: z.string().trim().min(1).max(1024) }),
      annotations: write,
    },
    ({ title }) =>
      call(async () => (await (await getTasksClient()).tasklists.insert({ requestBody: { title } })).data),
  );

  server.registerTool(
    "update_task_list",
    {
      description: "Rename a Google task list.",
      inputSchema: z.object({ task_list_id: taskListId, title: z.string().trim().min(1).max(1024) }),
      annotations: { ...write, idempotentHint: true },
    },
    ({ task_list_id, title }) =>
      call(async () =>
        (await (await getTasksClient()).tasklists.patch({ tasklist: task_list_id, requestBody: { title } })).data,
      ),
  );

  server.registerTool(
    "delete_task_list",
    {
      description: "Permanently delete a Google task list. Requires explicit confirmation.",
      inputSchema: z.object({
        task_list_id: taskListId,
        confirm: z.literal(true).describe("Must be true after the user explicitly confirms deletion"),
      }),
      annotations: destructive,
    },
    ({ task_list_id }) =>
      call(async () => {
        await (await getTasksClient()).tasklists.delete({ tasklist: task_list_id });
        return { deleted: true, task_list_id };
      }),
  );

  server.registerTool(
    "list_tasks",
    {
      description: "List tasks in a Google task list with filters and pagination.",
      inputSchema: z.object({
        task_list_id: taskListId,
        max_results: z.number().int().min(1).max(100).default(100),
        page_token: z.string().optional(),
        show_completed: z.boolean().default(true),
        show_deleted: z.boolean().default(false),
        show_hidden: z.boolean().default(false),
        due_min: z.string().datetime({ offset: true }).optional(),
        due_max: z.string().datetime({ offset: true }).optional(),
        completed_min: z.string().datetime({ offset: true }).optional(),
        completed_max: z.string().datetime({ offset: true }).optional(),
        updated_min: z.string().datetime({ offset: true }).optional(),
      }),
      annotations: readOnly,
    },
    (args) =>
      call(async () => {
        const { data } = await (await getTasksClient()).tasks.list({
          tasklist: args.task_list_id,
          maxResults: args.max_results,
          pageToken: args.page_token,
          showCompleted: args.show_completed,
          showDeleted: args.show_deleted,
          showHidden: args.show_hidden,
          dueMin: args.due_min,
          dueMax: args.due_max,
          completedMin: args.completed_min,
          completedMax: args.completed_max,
          updatedMin: args.updated_min,
        });
        return { tasks: data.items ?? [], next_page_token: data.nextPageToken ?? null };
      }),
  );

  server.registerTool(
    "get_task",
    {
      description: "Get one task by task-list ID and task ID.",
      inputSchema: z.object({ task_list_id: taskListId, task_id: taskId }),
      annotations: readOnly,
    },
    ({ task_list_id, task_id }) =>
      call(async () =>
        (await (await getTasksClient()).tasks.get({ tasklist: task_list_id, task: task_id })).data,
      ),
  );

  server.registerTool(
    "create_task",
    {
      description: "Create a task, optionally as a subtask or after a sibling.",
      inputSchema: z.object({
        task_list_id: taskListId,
        title: z.string().trim().min(1).max(1024),
        notes: z.string().max(8192).optional(),
        due: due.optional(),
        parent_task_id: z.string().min(1).optional(),
        previous_task_id: z.string().min(1).optional(),
      }),
      annotations: write,
    },
    (args) =>
      call(async () =>
        (
          await (await getTasksClient()).tasks.insert({
            tasklist: args.task_list_id,
            parent: args.parent_task_id,
            previous: args.previous_task_id,
            requestBody: { title: args.title, notes: args.notes, due: normalizeDueDate(args.due) },
          })
        ).data,
      ),
  );

  server.registerTool(
    "update_task",
    {
      description: "Patch a task's title, notes, due date, or status. Use null to clear notes or due.",
      inputSchema: z
        .object({
          task_list_id: taskListId,
          task_id: taskId,
          title: z.string().trim().min(1).max(1024).optional(),
          notes: z.string().max(8192).nullable().optional(),
          due: due.nullable().optional(),
          status: z.enum(["needsAction", "completed"]).optional(),
        })
        .refine((value) => value.title !== undefined || value.notes !== undefined || value.due !== undefined || value.status !== undefined, {
          message: "Provide at least one field to update",
        }),
      annotations: { ...write, idempotentHint: true },
    },
    (args) =>
      call(async () => {
        const { task_list_id, task_id, ...fields } = args;
        const requestBody = {
          ...fields,
          ...(fields.due !== undefined ? { due: normalizeDueDate(fields.due) } : {}),
        };
        return (
          await (await getTasksClient()).tasks.patch({
            tasklist: task_list_id,
            task: task_id,
            requestBody,
          })
        ).data;
      }),
  );

  server.registerTool(
    "complete_task",
    {
      description: "Mark a task completed.",
      inputSchema: z.object({ task_list_id: taskListId, task_id: taskId }),
      annotations: { ...write, idempotentHint: true },
    },
    ({ task_list_id, task_id }) =>
      call(async () =>
        (
          await (await getTasksClient()).tasks.patch({
            tasklist: task_list_id,
            task: task_id,
            requestBody: { status: "completed" },
          })
        ).data,
      ),
  );

  server.registerTool(
    "reopen_task",
    {
      description: "Mark a completed task as needing action again.",
      inputSchema: z.object({ task_list_id: taskListId, task_id: taskId }),
      annotations: { ...write, idempotentHint: true },
    },
    ({ task_list_id, task_id }) =>
      call(async () =>
        (
          await (await getTasksClient()).tasks.patch({
            tasklist: task_list_id,
            task: task_id,
            requestBody: { status: "needsAction" },
          })
        ).data,
      ),
  );

  server.registerTool(
    "move_task",
    {
      description: "Reorder a task, change its parent, or move it to another task list.",
      inputSchema: z.object({
        task_list_id: taskListId.describe("Current task list ID"),
        task_id: taskId,
        destination_task_list_id: z.string().min(1).optional(),
        parent_task_id: z.string().min(1).optional(),
        previous_task_id: z.string().min(1).optional(),
      }),
      annotations: write,
    },
    (args) =>
      call(async () =>
        (
          await (await getTasksClient()).tasks.move({
            tasklist: args.task_list_id,
            task: args.task_id,
            destinationTasklist: args.destination_task_list_id,
            parent: args.parent_task_id,
            previous: args.previous_task_id,
          })
        ).data,
      ),
  );

  server.registerTool(
    "delete_task",
    {
      description: "Permanently delete a task. Requires explicit confirmation.",
      inputSchema: z.object({
        task_list_id: taskListId,
        task_id: taskId,
        confirm: z.literal(true).describe("Must be true after the user explicitly confirms deletion"),
      }),
      annotations: destructive,
    },
    ({ task_list_id, task_id }) =>
      call(async () => {
        await (await getTasksClient()).tasks.delete({ tasklist: task_list_id, task: task_id });
        return { deleted: true, task_list_id, task_id };
      }),
  );

  server.registerTool(
    "clear_completed_tasks",
    {
      description: "Hide all completed tasks in a list. Requires explicit confirmation.",
      inputSchema: z.object({
        task_list_id: taskListId,
        confirm: z.literal(true).describe("Must be true after the user explicitly confirms clearing completed tasks"),
      }),
      annotations: destructive,
    },
    ({ task_list_id }) =>
      call(async () => {
        await (await getTasksClient()).tasks.clear({ tasklist: task_list_id });
        return { cleared: true, task_list_id };
      }),
  );

  return server;
}

serveStdio(createServer);
console.error("google-tasks-mcp running on stdio");
