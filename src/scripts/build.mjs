import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { stripTypeScriptTypes } from 'node:module';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const tsPath = path.join(__dirname, 'privacy_shield.ts');
const outPath = path.join(__dirname, 'privacy_shield.bundle.js');

console.log(`[TypeScript Builder] Reading: ${tsPath}`);
const tsSource = fs.readFileSync(tsPath, 'utf8');

console.log('[TypeScript Builder] Transpiling TypeScript types via Node module engine...');
const jsCode = stripTypeScriptTypes(tsSource);

fs.writeFileSync(outPath, jsCode, 'utf8');
console.log(`[TypeScript Builder] Generated production bundle: ${outPath} (${jsCode.length} bytes)`);
