# all-projects

Unified monorepo of all projects by **Juan-Louw Greyling** (juanlouw.greyling@gmail.com).
Full history of every original repo is preserved.

**New: [`merged/`](./merged)** holds a verbatim copy of everything (`merged/sources`) plus **OMNIS** (`merged/platform`), one platform that combines the projects' features behind a single API and console.

| Area | What lives here |
|---|---|
| `apps/web` | React/TS web apps: Vantage-ARS, OmniGPT, Quantum Flow OS, Neural Sovereign, Project Genesis, CodeEvolveAI, Site Mirror Studio, SA Threads, SAT portal |
| `apps/edge` | Vantage Sentinel: live Cloudflare Worker control plane observing the deployed office, GitHub pipeline and bound D1 database, with grounded AI briefings |
| `apps/sites` | Static sites: portfolio, Jacobs Bay |
| `apps/mobile` | Android (Kotlin) and React Native/Expo apps |
| `services` | Python services: COVENANT (3 repos merged into one tested package), AEON engine, autonomous agent, Codegenie, Streamlit apps |
| `research` | P vs NP / circuit lower bounds / UUMA proof-of-work research |
| `tools` | OMGithub automation, self-improving code analyzer |
| `archive` | Empty/stub repos kept for reference |

## Use
```bash
make list                        # all projects + type
make install P=services/covenant # install one project
make test                        # test everything (slow)
```
`projects.json` is the machine-readable catalog; `docs/MIGRATION.md` maps old repo names to new paths.

See [ROADMAP.md](./ROADMAP.md) for the staged engineering plan and current CI limitations.
