import { defineConfig } from 'vite';
import {readFileSync} from 'node:fs';
const {version} = JSON.parse(readFileSync(new URL('./package.json', import.meta.url), 'utf8'));

// Electron's production renderer uses file: URLs, so absolute /assets paths
// would resolve at the filesystem root and leave an empty window.
export default defineConfig({ base: './', define:{__APP_VERSION__:JSON.stringify(version)} });
