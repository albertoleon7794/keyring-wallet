#!/usr/bin/env node

/**
 * Fixes portal: symlinks that Yarn sometimes creates as directories instead.
 * This runs as part of the postinstall lifecycle hook.
 */

const fs = require('fs');
const path = require('path');

const APP_DIR = path.join(__dirname, '..', 'app');
const BIFOLD_PACKAGES = [
  { name: '@bifold/core', path: '../../../bifold/packages/core' },
  { name: '@bifold/oca', path: '../../../bifold/packages/oca' },
  { name: '@bifold/verifier', path: '../../../bifold/packages/verifier' },
  { name: '@bifold/react-native-attestation', path: '../../../bifold/packages/react-native-attestation' },
  { name: '@bifold/remote-logs', path: '../../../bifold/packages/remote-logs' },
];

function log(message) {
  console.log(`[fix-portal-symlinks] ${message}`);
}

function main() {
  const appNodeModules = path.join(APP_DIR, 'node_modules', '@bifold');

  if (!fs.existsSync(appNodeModules)) {
    log('@bifold packages not found, skipping symlink fix');
    return;
  }

  let fixed = 0;
  let alreadyLinked = 0;

  for (const pkg of BIFOLD_PACKAGES) {
    const pkgPath = path.join(appNodeModules, pkg.name.replace('@bifold/', ''));
    
    if (!fs.existsSync(pkgPath)) {
      log(`⚠️  ${pkg.name} not found in node_modules`);
      continue;
    }

    const stats = fs.lstatSync(pkgPath);
    
    if (stats.isSymbolicLink()) {
      alreadyLinked++;
      continue;
    }

    if (stats.isDirectory()) {
      log(`Converting ${pkg.name} from directory to symlink...`);
      try {
        // Remove the directory
        fs.rmSync(pkgPath, { recursive: true, force: true });
        // Create symlink (relative path from app/node_modules/@bifold/pkgName)
        fs.symlinkSync(pkg.path, pkgPath, 'dir');
        log(`✅ Fixed ${pkg.name} -> ${pkg.path}`);
        fixed++;
      } catch (error) {
        console.error(`❌ Failed to fix ${pkg.name}: ${error.message}`);
        process.exit(1);
      }
    }
  }

  if (fixed > 0) {
    log(`Fixed ${fixed} package(s), ${alreadyLinked} already linked`);
  } else if (alreadyLinked === BIFOLD_PACKAGES.length) {
    log('All packages already linked correctly');
  }
}

main();

