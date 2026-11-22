# all-projects

Unified monorepo of all projects by **Juan-Louw Greyling** (juanlouw.greyling@gmail.com).
Full history of every original repo is preserved.

| Area | What lives here |
|---|---|
| `apps/web` | React/TS web apps: Vantage-ARS, OmniGPT, Quantum Flow OS, Neural Sovereign, Project Genesis, CodeEvolveAI, Site Mirror Studio, SA Threads, SAT portal |
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
