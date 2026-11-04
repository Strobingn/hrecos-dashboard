const fs = require('node:fs');
const path = require('node:path');
const { Parser } = require('acorn');
const jsx = require('acorn-jsx');
const parser = Parser.extend(jsx());
const root = path.resolve(__dirname, '..');
const modules = new Map();
function collect(directory) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    if (['node_modules', 'android', 'ios', '.expo'].includes(entry.name)) continue;
    const file = path.join(directory, entry.name);
    if (entry.isDirectory()) collect(file);
    else if (entry.name.endsWith('.js')) {
      const source = fs.readFileSync(file, 'utf8');
      modules.set(file, parser.parse(source, { sourceType: 'module', ecmaVersion: 'latest' }));
    }
  }
}
collect(root);
const errors = [];
for (const [file, ast] of modules) {
  for (const statement of ast.body) {
    if (statement.type !== 'ImportDeclaration' || !statement.source.value.startsWith('.')) continue;
    const base = path.resolve(path.dirname(file), statement.source.value);
    const target = [base, base + '.js', base + '.json', path.join(base, 'index.js')].find((p) => fs.existsSync(p) && fs.statSync(p).isFile());
    if (!target) { errors.push(`${path.relative(root, file)}: missing ${statement.source.value}`); continue; }
    if (target.endsWith('.json')) { JSON.parse(fs.readFileSync(target, 'utf8')); continue; }
    const targetAst = modules.get(target);
    if (!targetAst) continue;
    const names = new Set();
    for (const node of targetAst.body) {
      if (node.type === 'ExportDefaultDeclaration') names.add('default');
      if (node.type === 'ExportNamedDeclaration') {
        if (node.declaration?.id) names.add(node.declaration.id.name);
        for (const declaration of node.declaration?.declarations || []) if (declaration.id.name) names.add(declaration.id.name);
        for (const specifier of node.specifiers || []) names.add(specifier.exported.name);
      }
    }
    for (const specifier of statement.specifiers) {
      if (specifier.type === 'ImportNamespaceSpecifier') continue;
      const name = specifier.type === 'ImportDefaultSpecifier' ? 'default' : specifier.imported.name;
      if (!names.has(name)) errors.push(`${path.relative(root, file)}: ${statement.source.value} has no export ${name}`);
    }
  }
}
if (errors.length) { console.error(errors.join('\n')); process.exitCode = 1; }
else console.log(`Parsed ${modules.size} JavaScript modules; local imports and JSON resolve.`);
