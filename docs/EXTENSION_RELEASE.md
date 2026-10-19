# Browser extension releases

`.github/workflows/extension-release.yml` packages and submits the Chrome and
Firefox extensions whenever their source changes on `master`.

## What happens on a push

1. **prepare** works out which add-on folder changed.
2. It asks each store what versions it already knows about:
   - Chrome: `fetchStatus` (published and submitted revisions)
   - Firefox: the AMO `/versions/` endpoint, authenticated with the AMO API key
3. It chooses a version:
   - manifest already ahead of the store → publish that version
   - otherwise → bump the patch version
4. If it bumped, it commits `chore(extensions): bump ... [skip ci]` and pushes
   to `master` with `GITHUB_TOKEN`. Token-pushed commits do not trigger
   workflows, so this cannot loop.
5. **chrome** packages the ZIP, uploads it and calls `publish` (submits for
   review).
6. **firefox** packages the XPI and submits a listed version to AMO with
   `web-ext sign --channel=listed`.

Both publish jobs attach their package to the workflow run.

Extension versions are independent of `version.json` and of each other.
`bump-version.js` now only ever *raises* an extension version, so an app release
can never lower a version that a store already has.

## Manual runs

```bash
# Release whatever the latest commit changed
gh workflow run extension-release.yml -f browser=auto

# Force a store submission for one add-on
gh workflow run extension-release.yml -f browser=firefox
gh workflow run extension-release.yml -f browser=both

gh run watch
```

`browser=chrome|firefox|both` fails immediately if that store's credentials are
missing, rather than silently doing nothing.

## Repository secrets

| Secret | Used for |
| --- | --- |
| `CHROME_CLIENT_ID` | Chrome Web Store OAuth client |
| `CHROME_CLIENT_SECRET` | Chrome Web Store OAuth client |
| `CHROME_REFRESH_TOKEN` | Long-lived Chrome Web Store token |
| `CHROME_EXTENSION_ID` | The item's extension ID |
| `CHROME_PUBLISHER_ID` | The dashboard publisher ID |
| `WEB_EXT_API_KEY` | AMO JWT issuer |
| `WEB_EXT_API_SECRET` | AMO JWT secret |

### Chrome Web Store

1. Open the [Google Cloud Console](https://console.cloud.google.com/) and
   create (or select) a project.
2. **APIs & Services → Library →** enable **Chrome Web Store API**.
3. **Configure the consent screen.** The old "OAuth consent screen" page is now
   called **Google Auth Platform**:
   - Open <https://console.cloud.google.com/auth/overview?project=PROJECT_ID>
     or search the console for **Google Auth Platform**.
   - If prompted, click **Get started** and choose **External** as the audience.
   - **Branding** is the consent screen (app name, support email).
   - **Audience → Test users** is where you add your own Google account.
   - Once everything works, use **Audience → Publish app** to move the app to
     production — refresh tokens from an app left in *Testing* expire after
     7 days.
4. **Create a Web application OAuth client** under **Google Auth Platform →
   Clients** (or **APIs & Services → Credentials**):
   - Application type: **Web application**
   - Authorised redirect URI: `https://developers.google.com/oauthplayground`
   - Do **not** use a **Desktop app** client: it has no redirect-URI field and
     the Playground fails with `redirect_uri_mismatch`. If your client
     downloaded a JSON file containing an `"installed"` key, it is a Desktop
     client — create a new Web application client instead.
   - The client ID and secret are shown in the console; the downloadable JSON
     is only a copy. Use its `client_id` and `client_secret` values, and do not
     commit the file.
5. Open the [OAuth 2.0 Playground](https://developers.google.com/oauthplayground/):
   - Click the gear icon, tick **Use your own OAuth credentials**, and paste
     the client ID and secret.
   - In *Step 1*, enter the scope
     `https://www.googleapis.com/auth/chromewebstore`, click **Authorise APIs**,
     and approve with the Google account that owns the extension.
   - In *Step 2*, click **Exchange authorisation code for tokens**.
   - Copy the **Refresh token**.
6. Get the two IDs from the item's dashboard URL:

   ```text
   https://chrome.google.com/webstore/devconsole/<PUBLISHER_ID>/<EXTENSION_ID>/edit
   ```

   The first UUID is the publisher ID and the second string is the extension ID.
   They are also under **Publisher → Settings** and on the item page.

> The Chrome Web Store item must already exist. The API can update existing
> items but cannot create one, and the Store listing and Privacy tabs must be
> complete before the first publish.

### Mozilla Add-ons (AMO)

1. Open <https://addons.mozilla.org/en-US/developers/addon/api/key/>.
2. Click **Generate new credentials**.
3. Use the **JWT issuer** as `WEB_EXT_API_KEY` and the **JWT secret** as
   `WEB_EXT_API_SECRET`. These are account-wide, not per add-on.

### Adding the secrets

Run these from the repository. `gh secret set` with no value prompts for the
value without echoing it, so it does not land in your shell history:

```bash
gh secret set CHROME_CLIENT_ID      --repo githuba42r/ImageTools
gh secret set CHROME_CLIENT_SECRET  --repo githuba42r/ImageTools
gh secret set CHROME_REFRESH_TOKEN  --repo githuba42r/ImageTools
gh secret set CHROME_EXTENSION_ID   --repo githuba42r/ImageTools
gh secret set CHROME_PUBLISHER_ID   --repo githuba42r/ImageTools

gh secret set WEB_EXT_API_KEY       --repo githuba42r/ImageTools
gh secret set WEB_EXT_API_SECRET    --repo githuba42r/ImageTools
```

Verify the names (values are never shown):

```bash
gh secret list --repo githuba42r/ImageTools
```

You can also add them in **Settings → Secrets and variables → Actions** in the
GitHub UI.

Rotate a credential with `gh secret set <NAME> --repo ...` and revoke the old
one at the provider:
- Chrome: delete the OAuth client or revoke the app's access to the account.
- AMO: revoke the API key on the API key page.

## Caveats

- **First Chrome review.** While the item has never been published and a
  revision is awaiting its first review, the workflow skips Chrome with a
  message. Re-run after approval.
- **Release notes are manual.** Neither the Chrome Web Store API nor
  `web-ext sign` accepts release notes, so add them in each dashboard when the
  submission is reviewed.
- **AMO review.** `--approval-timeout 0` returns as soon as the submission is
  accepted; human review happens afterwards.
- **Duplicate versions.** AMO versions that are still awaiting review are
  visible to the API credentials, so a second change bumps past them. If the
  AMO API ever hides an in-review version, the submission fails with AMO's
  duplicate-version error and can be re-run after review.

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| `Chrome Web Store item not found` | Wrong `CHROME_EXTENSION_ID`/`CHROME_PUBLISHER_ID`, or the item was never created |
| `invalid_grant` from Google | Refresh token expired (consent screen still in *Testing*) or was revoked |
| `HTTP 401` from AMO | Wrong JWT issuer/secret, or the system clock is badly skewed |
| Chrome `publish` fails during review | The item is still in review; re-run later |
| `Could not push the version bump` | `master` moved during the run or branch protection was added |
