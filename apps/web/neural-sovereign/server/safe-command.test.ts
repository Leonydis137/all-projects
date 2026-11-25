import assert from "node:assert/strict";
import test from "node:test";
import { resolveSafeSystemCommand } from "./safe-command";

test("resolves only exact read-only system command entries", () => {
  assert.deepEqual(resolveSafeSystemCommand("date"), { executable: "date", args: [] });
  assert.deepEqual(resolveSafeSystemCommand(" uname -a "), { executable: "uname", args: ["-a"] });
  assert.deepEqual(resolveSafeSystemCommand("free -m"), { executable: "free", args: ["-m"] });
  assert.deepEqual(resolveSafeSystemCommand("ps aux"), { executable: "ps", args: ["aux"] });
});

test("rejects shell operators, substitutions, redirects, and appended commands", () => {
  for (const input of [
    "date; id",
    "date && id",
    "date | cat",
    "date $(id)",
    "whoami > /tmp/out",
    "ps aux; curl attacker.invalid",
    "uname -a -r",
    "constructor",
    "toString",
    "__proto__",
  ]) {
    assert.equal(resolveSafeSystemCommand(input), null, input);
  }
});

test("rejects non-string and empty inputs", () => {
  assert.equal(resolveSafeSystemCommand(null), null);
  assert.equal(resolveSafeSystemCommand({ command: "date" }), null);
  assert.equal(resolveSafeSystemCommand("   "), null);
});
