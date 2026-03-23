/**
 * SharePoint List Extractor
 *
 * Authenticates to Microsoft Graph API via Azure AD client credentials,
 * fetches all items from CATT SharePoint lists, and writes raw JSON to S3.
 *
 * Usage:
 *   node src/sharepoint-extractor.js               # full extraction
 *   DRY_RUN=true node src/sharepoint-extractor.js   # preview without S3 upload
 *
 * Required env vars: see .env.example
 */

import { ConfidentialClientApplication } from "@azure/msal-node";
import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";

// ---------------------------------------------------------------------------
// Configuration (all values from environment — no hardcoded secrets or IDs)
// ---------------------------------------------------------------------------

const TENANT_ID = required("AZURE_TENANT_ID");
const CLIENT_ID = required("AZURE_CLIENT_ID");
const CLIENT_SECRET = required("AZURE_CLIENT_SECRET");
const SHAREPOINT_SITE_URL = required("SHAREPOINT_SITE_URL");
const S3_BUCKET = process.env.S3_BUCKET_NAME || "catt-pipeline-data";
const AWS_REGION = process.env.AWS_REGION || "us-west-2";
const DRY_RUN = process.env.DRY_RUN === "true";

const GRAPH_BASE = "https://graph.microsoft.com/v1.0";

/** SharePoint lists to extract — matched by display name at runtime. */
const LISTS = [
  { fileName: "episodes",    displayName: "Episodes List" },
  { fileName: "catt-times",  displayName: "CATT Time List" },
  { fileName: "narratives",  displayName: "NarrativeList" },
];

function required(name) {
  const val = process.env[name];
  if (!val) {
    console.error(`Missing required env var: ${name}`);
    process.exit(1);
  }
  return val;
}

// ---------------------------------------------------------------------------
// Auth — MSAL client_credentials flow
// ---------------------------------------------------------------------------

const cca = new ConfidentialClientApplication({
  auth: {
    clientId: CLIENT_ID,
    authority: `https://login.microsoftonline.com/${TENANT_ID}`,
    clientSecret: CLIENT_SECRET,
  },
});

async function getToken() {
  const result = await cca.acquireTokenByClientCredential({
    scopes: ["https://graph.microsoft.com/.default"],
  });
  if (!result?.accessToken) throw new Error("Failed to acquire Graph API token");
  return result.accessToken;
}

// ---------------------------------------------------------------------------
// Graph API helpers
// ---------------------------------------------------------------------------

async function graphGet(token, url) {
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Graph API ${res.status}: ${body}`);
  }
  return res.json();
}

/** Resolve the SharePoint site ID from the site URL. */
async function resolveSiteId(token) {
  const url = new URL(SHAREPOINT_SITE_URL);
  const hostname = url.hostname; // e.g. contoso.sharepoint.com
  const sitePath = url.pathname; // e.g. /sites/CATTV2
  const data = await graphGet(token, `${GRAPH_BASE}/sites/${hostname}:${sitePath}`);
  return data.id;
}

/** Resolve a list ID from its display name. */
async function resolveListId(token, siteId, displayName) {
  const data = await graphGet(token, `${GRAPH_BASE}/sites/${siteId}/lists`);
  const match = data.value.find((l) => l.displayName === displayName || l.name === displayName);
  if (!match) {
    const available = data.value.map((l) => l.displayName).join(", ");
    throw new Error(`List "${displayName}" not found. Available: ${available}`);
  }
  return match.id;
}

/** Fetch all items from a list, handling pagination ($skiptoken). */
async function fetchListItems(token, siteId, listId) {
  const items = [];
  let url = `${GRAPH_BASE}/sites/${siteId}/lists/${listId}/items?$expand=fields&$top=200`;

  while (url) {
    const data = await graphGet(token, url);
    for (const item of data.value || []) {
      items.push(item.fields);
    }
    url = data["@odata.nextLink"] || null;
  }

  return items;
}

// ---------------------------------------------------------------------------
// S3 upload
// ---------------------------------------------------------------------------

const s3 = new S3Client({ region: AWS_REGION });

async function uploadToS3(key, jsonData) {
  const body = JSON.stringify(jsonData, null, 2);

  if (DRY_RUN) {
    console.log(`  [DRY RUN] Would upload ${key} (${body.length} bytes, ${jsonData.length} records)`);
    return;
  }

  await s3.send(
    new PutObjectCommand({
      Bucket: S3_BUCKET,
      Key: key,
      Body: body,
      ContentType: "application/json",
    })
  );
  console.log(`  Uploaded s3://${S3_BUCKET}/${key} (${jsonData.length} records)`);
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const datePrefix = new Date().toISOString().slice(0, 10);
  console.log(`CATT SharePoint Extractor — ${datePrefix}`);
  console.log(`Mode: ${DRY_RUN ? "DRY RUN" : "LIVE"}\n`);

  const token = await getToken();
  console.log("Graph API token acquired");

  // Resolve site ID from URL
  const siteId = await resolveSiteId(token);
  console.log(`Site resolved: ${SHAREPOINT_SITE_URL}\n`);

  for (const list of LISTS) {
    console.log(`Extracting: ${list.displayName}`);

    const listId = await resolveListId(token, siteId, list.displayName);
    const items = await fetchListItems(token, siteId, listId);
    console.log(`  Fetched ${items.length} items`);

    const s3Key = `catt-pipeline/raw/${datePrefix}/${list.fileName}.json`;
    await uploadToS3(s3Key, items);
    console.log();
  }

  console.log("Extraction complete.");
}

main().catch((err) => {
  console.error("Fatal error:", err.message || err);
  process.exit(1);
});
