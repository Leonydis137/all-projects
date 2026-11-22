# Migration map (old folder → new location)
Author: Juan-Louw Greyling <juanlouw.greyling@gmail.com>

Every original commit is preserved in this repo's history (each import merge commit's second parent is that repo's full history, e.g. `git log "$(git log --grep='Merge Covenant ' --format=%H -1)^2"`). Per-file `git log --follow` does not trace across the folder moves. Original repos are untouched.

| Old folder | New location |
|---|---|
| vantage-ars | apps/web/vantage-ars |
| vantage | apps/web/vantage-workspace |
| omnigpt-web | apps/web/omnigpt-web |
| Quantum-Flow-OS | apps/web/quantum-flow-os |
| vite-react-wmjavfy2 | apps/web/quantum-flow-os-vite |
| neural_sovereign | apps/web/neural-sovereign |
| Project-Genesis | apps/web/project-genesis |
| CodeEvolveAI | apps/web/codeevolve-ai |
| SA-Threads---Premier-Online-Fashion | apps/web/sa-threads |
| hybrid-sat-solver-portal | apps/web/hybrid-sat-solver-portal |
| Site-Mirror-Studio | apps/web/site-mirror-studio |
| juan-louw.greyling.github.io | apps/sites/portfolio |
| jacobsbayaccomodationtemp.io | apps/sites/jacobsbay-site |
| Jacobsbay-Accomodation | apps/sites/jacobsbay-accommodation |
| topsecret | apps/sites/topsecret |
| Synapse-OS | apps/mobile/synapse-os |
| chatgpt-android-os | apps/mobile/chatgpt-android-os |
| omnigpt-mobile | apps/mobile/omnigpt-mobile |
| Covenant | services/covenant |
| autonomous-AI | services/autonomous-ai |
| EAON-AI-Engine | services/aeon-engine |
| Codegenie | services/codegenie |
| Discussion_Bot | services/discussion-bot |
| GCD-PvsNP | research/gcd-pvsnp |
| solution_to_p-np | research/circuit-lower-bounds |
| uuma | research/uuma |
| PlayGround | tools/omgithub |
| self-improving-code-analyzer-v14 | tools/self-improving-code-analyzer |
| Combined | archive/omgithub-combined |
| Covenant-ai | archive/covenant-ai |
| Covenant-Enterprise | archive/covenant-enterprise |
| blank-app | archive/templates/blank-app |
| Nexus, Predictor, combined-repositories | archive/stubs/ |

## Removed
- `Covenant_Enterprise_V5.0`: byte-identical to `Covenant`.
- `self-improving-code-analyzer-v9` to `v13`: differed from v14 only in name/version strings (still in git history and the source repos).
- Committed `venv`/`.venv` folders and `.pyc` files (regenerable).

## Notes
- Per-project `.github/workflows/*` are inert in a monorepo (GitHub only reads the root). The root `ci.yml` replaces them; port individual workflows as needed.
- Kept as-is: zips/tarballs inside projects (e.g. `Vantage-Ars.zip`, `Site-Mirror-completed.zip`).
