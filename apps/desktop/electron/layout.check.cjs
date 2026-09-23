const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

test('right inspector and its control groups can shrink within the viewport', () => {
  const css = fs.readFileSync(path.join(__dirname, '../src/style.css'), 'utf8');
  const shrinkableSelectors = [...css.matchAll(/([^{}]+)\{[^{}]*min-width:0[^{}]*\}/g)]
    .map((match) => match[1]);

  assert.ok(shrinkableSelectors.some((selectors) => selectors.includes('.inspector')));
  assert.ok(shrinkableSelectors.some((selectors) => selectors.includes('.tool-group')));
  assert.match(css, /\.tool-group\{[^}]*grid-template-columns:minmax\(0,1fr\)/);
  assert.match(css, /\.tool-group select\{[^}]*width:100%[^}]*min-width:0/);
});
