Weekly Membrain lint (catalog routine weekly-brain-lint, installed {{DATE}} for @{{OWNER}}).

Open {{REPO_OR_WORKSPACE}}. Read AGENTS.md there fresh (in a single shared brain: CLAUDE.md), then follow guides/weekly-lint.md for every brain listed in brains/personal/brains.yaml (in a single shared brain: this brain only).

Send {{APPROVER}} one message with every proposed fix (file, line, problem, exact change). If there is nothing to fix, send nothing.
Change nothing until {{APPROVER}} says yes. Then apply exactly what was approved using the {{APPLY_PATH}} path (direct = append, read back, lint, log, sync; pull-request = open a pull request for the owner), and stop.
