const path = require('node:path');

/** Resolve the sidecar without relying on POSIX paths in a packaged app. */
function engineCommand({isPackaged, resourcesPath, dirname, platform = process.platform}) {
  const paths = platform === 'win32' ? path.win32 : path;
  if (isPackaged) {
    return {
      executable: paths.join(resourcesPath, 'engine', `pixelmend-engine${platform === 'win32' ? '.exe' : ''}`),
      args: [],
    };
  }
  return {
    executable: paths.join(dirname, '../../../engine/.venv', platform === 'win32' ? 'Scripts/python.exe' : 'bin/python'),
    args: ['-m', 'pixelmend_engine'],
  };
}

module.exports = {engineCommand};
