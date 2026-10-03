// Shared read-only Git environment for discovery and enumeration.
export function gitEnvironment(): NodeJS.ProcessEnv {
  const locationOverrides = new Set([
    'GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR', 'GIT_INDEX_FILE',
    'GIT_CEILING_DIRECTORIES', 'GIT_DISCOVERY_ACROSS_FILESYSTEM',
    'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES',
  ]);
  const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !locationOverrides.has(key.toUpperCase())));
  env.GIT_TERMINAL_PROMPT = '0';
  env.LC_ALL = 'C';
  return env;
}
