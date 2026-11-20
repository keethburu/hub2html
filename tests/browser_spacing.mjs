// Run against actual Saxon-generated XHTML, using Chrome's rendered innerText.
// Expected strings are authored in browser_spacing.json, not inferred from CSS.
import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

if (process.argv.length !== 3) {
  throw new Error('Usage: node tests/browser_spacing.mjs /absolute/path/to/manifest.json');
}
const fixtures = JSON.parse(readFileSync(process.argv[2], 'utf8'));
if (fixtures.length === 0) throw new Error('No browser fixtures');
const script = `
const fixtures = ${JSON.stringify(fixtures)};
const failures = [];
const results = [];
for (const fixture of fixtures) {
  await page.open(fixture.url);
  const actual = await page.eval(() => {
    const author = document.querySelector('p.author');
    if (!author) throw new Error('Missing converted author');
    return {
      text: author.innerText,
      visible_svg: [...author.querySelectorAll('svg')].filter(
        svg => svg.getClientRects().length > 0
      ).length,
      white_space: getComputedStyle(author).whiteSpace,
    };
  });
  const pass = actual.text === fixture.expected &&
    (fixture.visible_svg === undefined || actual.visible_svg === fixture.visible_svg);
  results.push({name: fixture.name, pass, expected: fixture.expected, actual});
  if (!pass) failures.push(fixture.name);
}
console.log(JSON.stringify({total: fixtures.length, failures, results}));
`;
const result = spawnSync('npx', ['-y', 'chrome-devtools-axi@0.1.46', 'run'], {
  input: script,
  encoding: 'utf8',
  env: { ...process.env, CHROME_DEVTOOLS_AXI_SESSION: process.env.CHROME_DEVTOOLS_AXI_SESSION || 'hub2html-spacing' },
  timeout: 180_000,
  maxBuffer: 4 * 1024 * 1024,
});
process.stdout.write(result.stdout || '');
process.stderr.write(result.stderr || '');
if (result.error) throw result.error;
process.exitCode = result.status ?? 1;
if (result.status === 0) {
  const report = JSON.parse(result.stdout);
  if (report.failures.length) {
    console.error('Browser spacing failures: ' + report.failures.join(', '));
    process.exitCode = 1;
  } else {
    console.log('Browser spacing: ' + report.total + ' passed');
  }
}
