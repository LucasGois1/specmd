#!/usr/bin/env node
import { spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';
import { tmpdir } from 'node:os';
import { mkdirSync, readFileSync, writeFileSync, existsSync, copyFileSync, rmSync } from 'node:fs';

const root = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
if (args.includes('--help')) {
  console.log('Usage: node run.mjs --version X.Y.Z [--install] [--cache-dir PATH] [--output-dir PATH]');
  console.log('No network is attempted without --install. Each subprocess has a finite timeout.');
  process.exit(0);
}
function option(name, fallback) {
  const index = args.indexOf(name);
  return index < 0 ? fallback : args[index + 1];
}
const version = option('--version');
if (!version || !/^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/.test(version)) {
  console.error('Supply an exact package version with --version X.Y.Z. No version has been resolved by this fixture.');
  process.exit(2);
}
const cache = resolve(option('--cache-dir', join(tmpdir(), 'specmd-mdg-cache')));
const installation = join(cache, version);
const output = resolve(option('--output-dir', join(root, 'evidence', version)));
mkdirSync(output, { recursive: true });
mkdirSync(installation, { recursive: true });
const summary = {
  startedAt: new Date().toISOString(), node: process.version,
  requestedCucumberVersion: version, status: 'not_executed', cases: [],
};
function persist() {
  writeFileSync(join(output, 'summary.json'), JSON.stringify(summary, null, 2) + '\n');
}
function execute(command, commandArgs, cwd, timeout = 60_000) {
  const result = spawnSync(command, commandArgs, {
    cwd, encoding: 'utf8', timeout, maxBuffer: 5 * 1024 * 1024,
    env: { ...process.env, FORCE_COLOR: '0', CUCUMBER_PUBLISH_ENABLED: 'false' },
  });
  return {
    command: [command, ...commandArgs], exitCode: result.status,
    signal: result.signal, error: result.error?.message ?? null,
    stdout: result.stdout ?? '', stderr: result.stderr ?? '',
  };
}
const manifestPath = join(installation, 'package.json');
if (!existsSync(manifestPath)) {
  writeFileSync(manifestPath, JSON.stringify({ private: true, name: 'specmd-mdg-baseline' }, null, 2) + '\n');
}
if (args.includes('--install')) {
  const installationResult = execute('npm', [
    'install', '--save-exact', '--no-audit', '--no-fund',
    '--fetch-retries=0', '--fetch-timeout=30000', `@cucumber/cucumber@${version}`,
  ], installation, 120_000);
  writeFileSync(join(output, 'installation.json'), JSON.stringify(installationResult, null, 2) + '\n');
  if (installationResult.exitCode !== 0) {
    summary.status = 'dependency_installation_failed'; persist();
    console.error(`Installation did not complete. See ${output}/installation.json`);
    process.exit(2);
  }
}
const packagePath = join(installation, 'node_modules', '@cucumber', 'cucumber', 'package.json');
if (!existsSync(packagePath)) {
  summary.status = 'not_executed_dependency_missing'; persist();
  console.error('Dependency is absent. No network attempted; use --install only after network authorization.');
  process.exit(2);
}
const packageInfo = JSON.parse(readFileSync(packagePath, 'utf8'));
summary.installedCucumberVersion = packageInfo.version;
summary.packageEngines = packageInfo.engines ?? null;
if (packageInfo.version !== version) {
  summary.status = 'installed_version_mismatch'; persist(); process.exit(2);
}
copyFileSync(manifestPath, join(output, 'package.json'));
const lockPath = join(installation, 'package-lock.json');
if (existsSync(lockPath)) copyFileSync(lockPath, join(output, 'package-lock.json'));
const requireFromInstallation = createRequire(manifestPath);
const cucumberEntry = requireFromInstallation.resolve('@cucumber/cucumber');
const cli = join(installation, 'node_modules', '@cucumber', 'cucumber', 'bin', 'cucumber.js');
summary.cliVersion = execute(process.execPath, [cli, '--version'], installation);
const probes = [
  { id: 'mdg-explicit-positive', fixture: 'addition.feature.md', target: 'addition.feature.md', explicit: true },
  { id: 'mdg-explicit-negative', fixture: 'negative.feature.md', target: 'negative.feature.md', explicit: true },
  { id: 'mdg-default-discovery', fixture: 'addition.feature.md', target: 'addition.feature.md', explicit: false },
  { id: 'mdg-ordinary-md-explicit', fixture: 'addition.feature.md', target: 'addition.md', explicit: true },
  { id: 'fenced-ordinary-md-explicit', fixture: 'fenced.md', target: 'fenced.md', explicit: true },
];
for (const probe of probes) {
  const work = join(output, probe.id);
  rmSync(work, { recursive: true, force: true });
  for (const directory of ['features', 'support', 'src']) mkdirSync(join(work, directory), { recursive: true });
  copyFileSync(join(root, 'fixtures', probe.fixture), join(work, 'features', probe.target));
  copyFileSync(join(root, 'src', 'math.cjs'), join(work, 'src', 'math.cjs'));
  const stepSource = readFileSync(join(root, 'support', 'steps.cjs'), 'utf8')
    .replace("require('@cucumber/cucumber')", `require(${JSON.stringify(cucumberEntry)})`);
  writeFileSync(join(work, 'support', 'steps.cjs'), stepSource);
  const invocation = [cli];
  if (probe.explicit) invocation.push(join('features', probe.target));
  invocation.push('--require', 'support/steps.cjs', '--format', 'json:results.json', '--format', 'progress');
  const result = execute(process.execPath, invocation, work);
  const record = { ...probe, ...result, scenarioCount: null, stepStatuses: {}, failedStepMessages: [] };
  const report = join(work, 'results.json');
  if (existsSync(report)) {
    try {
      const features = JSON.parse(readFileSync(report, 'utf8'));
      const scenarios = features.flatMap(feature => feature.elements ?? []).filter(element => element.type === 'scenario');
      record.scenarioCount = scenarios.length;
      for (const scenario of scenarios) for (const step of scenario.steps ?? []) {
        const status = step.result?.status ?? 'unknown';
        record.stepStatuses[status] = (record.stepStatuses[status] ?? 0) + 1;
        if (step.result?.error_message) record.failedStepMessages.push(step.result.error_message);
      }
    } catch (error) { record.reportError = error.message; }
  }
  writeFileSync(join(work, 'execution.json'), JSON.stringify(record, null, 2) + '\n');
  summary.cases.push(record);
}
const positive = summary.cases.find(item => item.id === 'mdg-explicit-positive');
const negative = summary.cases.find(item => item.id === 'mdg-explicit-negative');
summary.baselineConfirmed = positive.exitCode === 0 && positive.scenarioCount > 0
  && Number.isInteger(negative.exitCode) && negative.exitCode > 0 && negative.scenarioCount > 0
  && negative.failedStepMessages.some(message => message.includes('AssertionError'));
summary.status = 'executed';
summary.finishedAt = new Date().toISOString();
persist();
console.log(JSON.stringify({ status: summary.status, baselineConfirmed: summary.baselineConfirmed, output,
  cases: summary.cases.map(item => ({ id: item.id, exitCode: item.exitCode, scenarioCount: item.scenarioCount, stepStatuses: item.stepStatuses })) }, null, 2));
process.exit(summary.baselineConfirmed ? 0 : 1);
