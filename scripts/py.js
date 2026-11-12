import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';

// Run Python from the project virtualenv when it exists, so git hooks work
// even if the venv is not activated (e.g. when pushing from VS Code).
const candidates = [
    '.venv/Scripts/python.exe',
    '.venv/bin/python',
    'venv/Scripts/python.exe',
    'venv/bin/python',
];
const python = candidates.find((p) => existsSync(p)) ?? 'python';

const result = spawnSync(python, process.argv.slice(2), { stdio: 'inherit' });
process.exit(result.status ?? 1);
