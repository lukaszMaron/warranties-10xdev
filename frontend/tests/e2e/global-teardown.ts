import { rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, dirname, resolve } from 'node:path';
import type { FullConfig } from '@playwright/test';

export default function globalTeardown(config: FullConfig) {
  const profileDirectory = config.metadata.e2eProfileDirectory;
  if (typeof profileDirectory !== 'string') {
    throw new Error('The isolated E2E profile path is missing from Playwright config metadata.');
  }

  const resolvedDirectory = resolve(profileDirectory);
  if (
    dirname(resolvedDirectory) !== resolve(tmpdir())
    || !basename(resolvedDirectory).startsWith('warranties-10xdev-e2e-')
  ) {
    throw new Error('Refusing to remove a test profile outside the isolated E2E temp directory.');
  }

  rmSync(resolvedDirectory, { recursive: true });
}
