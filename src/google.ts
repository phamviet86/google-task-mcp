import { readFile, writeFile, mkdir, chmod } from "node:fs/promises";
import { dirname, join } from "node:path";
import { homedir } from "node:os";
import { google, tasks_v1 } from "googleapis";

export const TASKS_SCOPE = "https://www.googleapis.com/auth/tasks";

export const tokenPath = () =>
  process.env.GOOGLE_TOKEN_FILE ?? join(homedir(), ".config", "google-tasks-mcp", "token.json");

type ClientSecrets = {
  installed?: { client_id: string; client_secret: string };
};

async function readJson(path: string): Promise<unknown> {
  return JSON.parse(await readFile(path, "utf8"));
}

export async function loadClientSecrets(path: string): Promise<{ client_id: string; client_secret: string }> {
  const json = (await readJson(path)) as ClientSecrets;
  const client = json.installed;
  if (!client?.client_id || !client?.client_secret) {
    throw new Error("--client-secret must point to a Google OAuth Desktop client JSON containing 'installed'.");
  }
  return { client_id: client.client_id, client_secret: client.client_secret };
}

export async function saveAuthorizedUserToken(
  auth: { credentials: { refresh_token?: string | null } },
  clientSecretFile: string,
): Promise<void> {
  const { client_id, client_secret } = await loadClientSecrets(clientSecretFile);
  const refresh_token = auth.credentials.refresh_token;
  if (!refresh_token) {
    throw new Error("Google did not return a refresh token. Revoke the app grant and run auth again.");
  }

  const path = tokenPath();
  await mkdir(dirname(path), { recursive: true, mode: 0o700 });
  await writeFile(
    path,
    JSON.stringify({ type: "authorized_user", client_id, client_secret, refresh_token }, null, 2) + "\n",
    { mode: 0o600 },
  );
  await chmod(path, 0o600);
}

export async function getTasksClient(): Promise<tasks_v1.Tasks> {
  let token: unknown;
  try {
    token = await readJson(tokenPath());
  } catch (error) {
    const reason = error instanceof Error ? error.message : String(error);
    throw new Error(
      `Google Tasks is not authenticated. Run 'google-tasks-mcp-auth' first. Token path: ${tokenPath()}. ${reason}`,
    );
  }

  const auth = google.auth.fromJSON(token as Parameters<typeof google.auth.fromJSON>[0]);
  return google.tasks({ version: "v1", auth: auth as never });
}

export function googleError(error: unknown): string {
  if (error && typeof error === "object") {
    const candidate = error as {
      message?: string;
      code?: string | number;
      response?: { data?: { error?: { message?: string; status?: string } } };
    };
    const apiError = candidate.response?.data?.error;
    return [candidate.code ?? apiError?.status, apiError?.message ?? candidate.message]
      .filter(Boolean)
      .join(": ");
  }
  return String(error);
}

export function normalizeDueDate(value: string | null | undefined): string | null | undefined {
  if (value === undefined || value === null) return value;
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return `${value}T00:00:00.000Z`;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.valueOf())) throw new Error("due must be YYYY-MM-DD or a valid RFC 3339 timestamp");
  return parsed.toISOString();
}
