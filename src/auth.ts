#!/usr/bin/env node
import { authenticate } from "@google-cloud/local-auth";
import { TASKS_SCOPE, loadClientSecrets, saveAuthorizedUserToken, tokenPath } from "./google.js";

const usage = "Usage: google-tasks-mcp-auth --client-secret /path/to/client_secret.json";

function clientSecretArgument(args: string[]): string {
  if (args.length === 1 && (args[0] === "--help" || args[0] === "-h")) {
    console.log(usage);
    process.exit(0);
  }
  if (args.length !== 2 || args[0] !== "--client-secret" || !args[1]) {
    throw new Error(usage);
  }
  return args[1];
}

async function main(): Promise<void> {
  const clientSecretFile = clientSecretArgument(process.argv.slice(2));
  await loadClientSecrets(clientSecretFile);
  const auth = await authenticate({
    scopes: [TASKS_SCOPE],
    keyfilePath: clientSecretFile,
  });
  await saveAuthorizedUserToken(auth, clientSecretFile);
  console.error(`Google Tasks authorization saved to ${tokenPath()}`);
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
});
