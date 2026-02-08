#!/usr/bin/env node

/**
 * Version Bump Script for ImageTools
 * 
 * Similar to npm version, but updates all project components:
 * - version.json (central version file)
 * - frontend/package.json
 * - backend/app/main.py
 * - browser-addons/firefox/manifest.json
 * - browser-addons/chrome/manifest.json
 * - android-app/app/build.gradle
 * 
 * Usage:
 *   node bump-version.js <major|minor|patch|prerelease> [preid]
 * 
 * Examples:
 *   node bump-version.js patch        # 1.2.0 -> 1.2.1
 *   node bump-version.js minor        # 1.2.0 -> 1.3.0
 *   node bump-version.js major        # 1.2.0 -> 2.0.0
 *   node bump-version.js prerelease   # 1.2.0 -> 1.2.1-0
 *   node bump-version.js prerelease alpha  # 1.2.0 -> 1.2.1-alpha.0
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// File paths
const ROOT_DIR = path.join(__dirname);
const VERSION_FILE = path.join(ROOT_DIR, 'version.json');
const FRONTEND_PACKAGE = path.join(ROOT_DIR, 'frontend', 'package.json');
const BACKEND_MAIN = path.join(ROOT_DIR, 'backend', 'app', 'main.py');
const FIREFOX_MANIFEST = path.join(ROOT_DIR, 'browser-addons', 'firefox', 'manifest.json');
const CHROME_MANIFEST = path.join(ROOT_DIR, 'browser-addons', 'chrome', 'manifest.json');
const ANDROID_GRADLE = path.join(ROOT_DIR, 'android-app', 'app', 'build.gradle');

/**
 * Parse semantic version string
 */
function parseVersion(version) {
  const match = version.match(/^(\d+)\.(\d+)\.(\d+)(?:-([a-z]+)\.(\d+))?$/);
  if (!match) {
    throw new Error(`Invalid version format: ${version}`);
  }
  
  return {
    major: parseInt(match[1], 10),
    minor: parseInt(match[2], 10),
    patch: parseInt(match[3], 10),
    prerelease: match[4] || null,
    prereleaseVersion: match[5] ? parseInt(match[5], 10) : null
  };
}

/**
 * Format version object to string
 */
function formatVersion(ver) {
  let version = `${ver.major}.${ver.minor}.${ver.patch}`;
  if (ver.prerelease) {
    version += `-${ver.prerelease}.${ver.prereleaseVersion}`;
  }
  return version;
}

/**
 * Bump version based on type
 */
function bumpVersion(currentVersion, bumpType, preid = 'alpha') {
  const ver = parseVersion(currentVersion);
  
  switch (bumpType) {
    case 'major':
      ver.major++;
      ver.minor = 0;
      ver.patch = 0;
      ver.prerelease = null;
      ver.prereleaseVersion = null;
      break;
      
    case 'minor':
      ver.minor++;
      ver.patch = 0;
      ver.prerelease = null;
      ver.prereleaseVersion = null;
      break;
      
    case 'patch':
      ver.patch++;
      ver.prerelease = null;
      ver.prereleaseVersion = null;
      break;
      
    case 'prerelease':
      if (ver.prerelease) {
        // Already a prerelease, increment prerelease version
        ver.prereleaseVersion++;
      } else {
        // Convert to prerelease
        ver.patch++;
        ver.prerelease = preid;
        ver.prereleaseVersion = 0;
      }
      break;
      
    default:
      throw new Error(`Invalid bump type: ${bumpType}. Use major, minor, patch, or prerelease.`);
  }
  
  return formatVersion(ver);
}

/**
 * Calculate Android versionCode from semantic version
 * Format: XXYYZZ where XX=major, YY=minor, ZZ=patch
 */
function calculateVersionCode(version) {
  const ver = parseVersion(version);
  return ver.major * 10000 + ver.minor * 100 + ver.patch;
}

/**
 * Update version.json
 */
function updateVersionJson(newVersion, versionCode) {
  console.log('📝 Updating version.json...');
  const versionData = {
    version: newVersion,
    buildDate: new Date().toISOString(),
    versionCode: versionCode
  };
  fs.writeFileSync(VERSION_FILE, JSON.stringify(versionData, null, 2) + '\n');
  console.log(`   ✓ Updated to ${newVersion} (code: ${versionCode})`);
}

/**
 * Update frontend package.json
 */
function updateFrontendPackage(newVersion) {
  console.log('📝 Updating frontend/package.json...');
  const pkg = JSON.parse(fs.readFileSync(FRONTEND_PACKAGE, 'utf8'));
  pkg.version = newVersion;
  fs.writeFileSync(FRONTEND_PACKAGE, JSON.stringify(pkg, null, 2) + '\n');
  console.log(`   ✓ Updated to ${newVersion}`);
}

/**
 * Update backend main.py
 */
function updateBackendMain(newVersion) {
  console.log('📝 Updating backend/app/main.py...');
  let content = fs.readFileSync(BACKEND_MAIN, 'utf8');
  
  // Update the version in FastAPI app initialization
  content = content.replace(
    /version="[^"]+"/,
    `version="${newVersion}"`
  );
  
  fs.writeFileSync(BACKEND_MAIN, content);
  console.log(`   ✓ Updated to ${newVersion}`);
}

/**
 * Update browser addon manifest.json
 */
function updateManifest(manifestPath, addonName, newVersion) {
  console.log(`📝 Updating ${addonName} manifest.json...`);
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  
  // Browser extensions don't support prerelease versions in manifest
  // Strip prerelease suffix for manifest
  const cleanVersion = newVersion.split('-')[0];
  manifest.version = cleanVersion;
  
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
  console.log(`   ✓ Updated to ${cleanVersion}`);
}

/**
 * Update Android build.gradle
 */
function updateAndroidGradle(newVersion, versionCode) {
  console.log('📝 Updating android-app/app/build.gradle...');
  let content = fs.readFileSync(ANDROID_GRADLE, 'utf8');
  
  // Update versionCode
  content = content.replace(
    /versionCode\s+\d+/,
    `versionCode ${versionCode}`
  );
  
  // Update versionName
  content = content.replace(
    /versionName\s+"[^"]+"/,
    `versionName "${newVersion}"`
  );
  
  fs.writeFileSync(ANDROID_GRADLE, content);
  console.log(`   ✓ Updated to ${newVersion} (code: ${versionCode})`);
}

/**
 * Run git command and return output
 */
function runGitCommand(command, description) {
  try {
    const output = execSync(command, { encoding: 'utf8', stdio: 'pipe' });
    return output.trim();
  } catch (error) {
    throw new Error(`${description} failed: ${error.message}`);
  }
}

/**
 * Check if git working directory is clean
 */
function checkGitStatus() {
  try {
    const status = execSync('git status --porcelain', { encoding: 'utf8' });
    return status.trim();
  } catch (error) {
    throw new Error('Failed to check git status. Are you in a git repository?');
  }
}

/**
 * Commit version changes and create git tag
 */
function commitAndTag(newVersion) {
  console.log('\n📦 Committing version changes...');
  
  // Add all version-related files
  const filesToCommit = [
    'version.json',
    'frontend/package.json',
    'backend/app/main.py',
    'browser-addons/firefox/manifest.json',
    'browser-addons/chrome/manifest.json',
    'android-app/app/build.gradle'
  ];
  
  try {
    // Stage the files
    filesToCommit.forEach(file => {
      runGitCommand(`git add ${file}`, `Staging ${file}`);
    });
    
    // Commit
    const commitMessage = `chore: bump version to ${newVersion}`;
    runGitCommand(`git commit -m "${commitMessage}"`, 'Creating commit');
    console.log(`   ✓ Committed: ${commitMessage}`);
    
    // Create tag
    const tagName = `v${newVersion}`;
    const tagMessage = `Release version ${newVersion}`;
    runGitCommand(`git tag -a ${tagName} -m "${tagMessage}"`, 'Creating tag');
    console.log(`   ✓ Tagged: ${tagName}`);
    
    return tagName;
  } catch (error) {
    throw new Error(`Git operations failed: ${error.message}`);
  }
}

/**
 * Display usage information
 */
function showUsage() {
  console.log(`
ImageTools Version Bump Tool

Usage: node bump-version.js <bump-type> [preid] [--no-commit]

Bump Types:
  major       Increment major version (1.2.3 -> 2.0.0)
  minor       Increment minor version (1.2.3 -> 1.3.0)
  patch       Increment patch version (1.2.3 -> 1.2.4)
  prerelease  Create or increment prerelease (1.2.3 -> 1.2.4-alpha.0)

Options:
  preid       Prerelease identifier (default: alpha)
              Examples: alpha, beta, rc
  --no-commit Skip automatic git commit and tag creation

Examples:
  node bump-version.js patch
  node bump-version.js minor
  node bump-version.js major
  node bump-version.js prerelease
  node bump-version.js prerelease beta
  node bump-version.js patch --no-commit
`);
}

/**
 * Main function
 */
function main() {
  const args = process.argv.slice(2);
  
  if (args.length === 0 || args[0] === '--help' || args[0] === '-h') {
    showUsage();
    process.exit(0);
  }
  
  // Parse arguments
  const noCommit = args.includes('--no-commit');
  const bumpType = args[0];
  const preid = args[1] && !args[1].startsWith('--') ? args[1] : 'alpha';
  
  try {
    // Check git status before proceeding (unless --no-commit is specified)
    if (!noCommit) {
      const gitStatus = checkGitStatus();
      if (gitStatus) {
        console.error('\n❌ Error: Working directory has uncommitted changes.');
        console.error('   Please commit or stash your changes before bumping version.\n');
        console.error('   Or use --no-commit flag to skip automatic commit.\n');
        process.exit(1);
      }
    }
    
    // Read current version
    const versionData = JSON.parse(fs.readFileSync(VERSION_FILE, 'utf8'));
    const currentVersion = versionData.version;
    
    console.log(`\n🔧 Current version: ${currentVersion}`);
    
    // Calculate new version
    const newVersion = bumpVersion(currentVersion, bumpType, preid);
    const versionCode = calculateVersionCode(newVersion);
    
    console.log(`🚀 New version: ${newVersion} (code: ${versionCode})\n`);
    
    // Update all files
    updateVersionJson(newVersion, versionCode);
    updateFrontendPackage(newVersion);
    updateBackendMain(newVersion);
    updateManifest(FIREFOX_MANIFEST, 'Firefox', newVersion);
    updateManifest(CHROME_MANIFEST, 'Chrome', newVersion);
    updateAndroidGradle(newVersion, versionCode);
    
    console.log('\n✅ Version bump complete!\n');
    console.log('Updated files:');
    console.log('  • version.json');
    console.log('  • frontend/package.json');
    console.log('  • backend/app/main.py');
    console.log('  • browser-addons/firefox/manifest.json');
    console.log('  • browser-addons/chrome/manifest.json');
    console.log('  • android-app/app/build.gradle');
    
    // Commit and tag
    if (!noCommit) {
      const tagName = commitAndTag(newVersion);
      console.log('\n✅ Changes committed and tagged!\n');
      console.log('💡 Next steps:');
      console.log(`  1. Review the changes with: git show`);
      console.log(`  2. Push changes: git push`);
      console.log(`  3. Push tags: git push --tags`);
      console.log(`  4. Or push both: git push && git push --tags\n`);
    } else {
      console.log('\n💡 Next steps:');
      console.log('  1. Review the changes with: git diff');
      console.log('  2. Commit: git add . && git commit -m "chore: bump version to ' + newVersion + '"');
      console.log('  3. Tag: git tag v' + newVersion);
      console.log('  4. Push: git push && git push --tags\n');
    }
    
  } catch (error) {
    console.error(`\n❌ Error: ${error.message}\n`);
    process.exit(1);
  }
}

// Run main function
main();
