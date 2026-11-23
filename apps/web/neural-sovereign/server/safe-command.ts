export type SafeSystemCommand = {
  executable: string;
  args: string[];
};

const ALLOWED_COMMANDS: Readonly<Record<string, SafeSystemCommand>> = Object.freeze({
  uptime: { executable: "uptime", args: [] },
  date: { executable: "date", args: [] },
  whoami: { executable: "whoami", args: [] },
  "uname -a": { executable: "uname", args: ["-a"] },
  "free -m": { executable: "free", args: ["-m"] },
  "ps aux": { executable: "ps", args: ["aux"] },
});

/** Resolve an exact command allow-list entry without parsing shell syntax. */
export function resolveSafeSystemCommand(input: unknown): SafeSystemCommand | null {
  if (typeof input !== "string") return null;
  const command = input.trim().toLowerCase();
  const selected = ALLOWED_COMMANDS[command];
  return selected ? { executable: selected.executable, args: [...selected.args] } : null;
}
