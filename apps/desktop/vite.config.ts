import { defineConfig } from 'vite';

// Electron's production renderer uses file: URLs, so absolute /assets paths
// would resolve at the filesystem root and leave an empty window.
export default defineConfig({ base: './' });
