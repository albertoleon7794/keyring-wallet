#!/usr/bin/env node

// This script will upload to a Google Play release track. See
// the Google Developer API documentation reference here:
// https://developers.google.com/android-publisher/api-ref/rest

const { google } = require('googleapis');
const fs = require('fs');
const pjson = require('./package.json');

if (typeof process.env.GOOGLE_API_CREDENTIALS === 'undefined') {
  console.log(`
  Google Publish v${pjson.version}

  GOOGLE_API_CREDENTIALS cannot be empty

  Set the env var GOOGLE_API_CREDENTIALS to the full path of the
  JSON credentials (keys) downloaded from the GCP console.
  eg: /path/to/some/credentials.json
  `);
  process.exit(1);
}

if (typeof process.env.ANDROID_PACKAGE_NAME === 'undefined') {
  console.log(`
  Google Publish v${pjson.version}

  ANDROID_PACKAGE_NAME cannot be empty

  Set the env var ANDROID_PACKAGE_NAME to the full package name
  used in the Android project.
  eg: ca.fullboar.BifoldWallet
  `);
  process.exit(1);
}

if (typeof process.env.ANDROID_BUNDLE_PATH === 'undefined') {
  console.log(`
  Google Publish v${pjson.version}

  ANDROID_BUNDLE_PATH cannot be empty

  Set the env var ANDROID_BUNDLE_PATH to the full path to the
  bundle (aab) file produced by the build.
  eg: /path/to/some/bundle.aab
  `);
  process.exit(1);
}

if (typeof process.env.VERSION_NAME === 'undefined') {
  console.log(`
  Google Publish v${pjson.version}

  VERSION_NAME cannot be empty

  Set the env var VERSION_NAME to the full version name
  eg: 1.0.2
  `);
  process.exit(1);
}

const expiryTimeSeconds = 600 // 10 min
const scopes = [
  'https://www.googleapis.com/auth/androidpublisher',
];

const main = async () => {

  const keyFile = process.env.GOOGLE_API_CREDENTIALS;
  const packageName = process.env.ANDROID_PACKAGE_NAME;
  const bundlePath = process.env.ANDROID_BUNDLE_PATH;

  console.log(`Google Publish v${pjson.version}`);

  try {
    console.log('Creating Google API client.');
    const client = await google.auth.getClient({
      keyFile,
      scopes,
    });

    console.log('Preparing Android publisher.');
    const play = await google.androidpublisher({
      version: 'v3',
      auth: client,
      params: {
        packageName,
      }
    });

    console.log('Creating an Edit.');
    const edit = await play.edits.insert({
      resource: {
        id: `${new Date().getTime()}`,
        expiryTimeSeconds,
      }
    });

    console.log('Loading bundle data.');
    const bundle = fs.readFileSync(bundlePath);

    console.log('Uploading bundle data to Edit.');
    await play.edits.bundles.upload({
      editId: edit.data.id,
      packageName,
      media: {
        mimeType: 'application/octet-stream',
        body: bundle
      }
    });

    const track = process.env.ANDROID_TRACK || 'internal';
    console.log(`Updating ${track} track.`);
    await play.edits.tracks.update({
      editId: edit.data.id,
      packageName,
      track: track,
      requestBody: {
        releases: [{
          name: `v${process.env.VERSION_NAME}-${process.env.VERSION_CODE || process.env.GITHUB_RUN_NUMBER || 0}`,
          status: 'completed', // draft, inProgress, completed
          // userFraction: 0.99,
          versionCodes: [
            `${process.env.VERSION_CODE || process.env.GITHUB_RUN_NUMBER || 0}`
          ],
          releaseNotes: [
            {
              language: 'en-CA',
              text: (() => {
                // Priority 1: Use commit message from GitHub (includes PR description from merge commits)
                let releaseNotes = process.env.GITHUB_COMMIT_MESSAGE;
                
                // Priority 2: Fallback to version-based message
                if (!releaseNotes || releaseNotes.trim().length < 5) {
                  releaseNotes = `Release ${process.env.VERSION_NAME} (Build ${process.env.GITHUB_RUN_NUMBER || '0'})`;
                }
                
                // Clean up: remove any remaining merge prefixes and normalize
                releaseNotes = releaseNotes
                  .replace(/^Merge (pull request #[0-9]+|branch [^\s]+ into [^\s]+)\s*/i, '')
                  .replace(/^Merge pull request #[0-9]+ from [^\s]+\s*/i, '')
                  .trim();
                
                // Limit length (Google Play has a 500 character limit)
                if (releaseNotes.length > 500) {
                  releaseNotes = releaseNotes.substring(0, 497) + '...';
                }
                
                return releaseNotes || `Release ${process.env.VERSION_NAME} (Build ${process.env.GITHUB_RUN_NUMBER || '0'})`;
              })()
            }
          ],
        }],
      },
    });

    console.log('Committing Edit.');
    await play.edits.commit({
      editId: edit.data.id
    });

    process.exit(0);
  } catch (e) {
    console.log('error = ', e)
    process.exit(1);
  }
}

main();
