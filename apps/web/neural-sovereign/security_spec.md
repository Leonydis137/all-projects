# Security Specification for NEURAL_OS

## Data Invariants
- A `Log` must have a valid `timestamp`, `level` and `source`.
- A `Mission` progress must be between 0 and 100.
- `SystemNode` load must be between 0 and 100.
- Only authenticated users can read/write.
- Admin status is granted to `juanlouw.greyling@gmail.com`.

## The Dirty Dozen Payloads (Rejections)
1. Anonymous user attempting to read logs.
2. User attempting to create a node with `load > 100`.
3. User attempting to create a mission with negative progress.
4. User attempting to update a mission they didn't create (if we had ownership, but for now it's collaborative).
5. User attempting to inject a 1MB string into a `Log` message.
6. User attempting to delete the `kernel` node.
7. User attempting to update a node's `id`.
8. User attempting to set a tool status to something other than `READY`, `EXECUTING`, or `LOCKED`.
9. User attempting to create a log with a future timestamp.
10. User attempting to modify the `type` of a CORE tool.
11. User attempting to write a field not defined in the schema (Ghost field test).
12. Non-admin user attempting to delete a critical system node.

## Test Runner (Logic Check)
- `permission_denied` expected for all "Dirty Dozen".
- Access granted for valid authenticated requests.
