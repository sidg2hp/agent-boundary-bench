/** Build a daily utilization statement from a replay without changing its journal. */
import {readFileSync} from "node:fs";
import {pathToFileURL} from "node:url";
import {apply, planner} from "./replay.mjs";
import {readCatalog} from "./common/limits.mjs";

export function groupEntries(occupied) {
  const tenants = new Map();
  for (const row of occupied) {
    if (!tenants.has(row.tenant)) tenants.set(row.tenant, new Map());
    const dates = tenants.get(row.tenant);
    if (!dates.has(row.day)) dates.set(row.day, []);
    dates.get(row.day).push({id: row.id, units: row.units});
  }
  return tenants;
}

export function daily(occupied, capFor) {
  const tenants = groupEntries(occupied);
  const lines = [];
  for (const tenant of [...tenants.keys()].sort()) {
    const dates = tenants.get(tenant);
    const cap = capFor(tenant);
    for (const day of [...dates.keys()].sort()) {
      const entries = dates.get(day);
      const used = entries.reduce((n, row) => n + row.units, 0);
      lines.push({
        tenant,
        day,
        cap,
        used,
        available: Math.max(0, cap - used),
        ids: entries.map(row => row.id).sort()
      });
    }
  }
  return lines;
}

export function statement(operations, catalog) {
  const dispatch = planner(catalog);
  const outcomes = {};
  for (const op of operations) {
    const answer = apply(dispatch, op);
    if (answer && typeof answer.status === "string") {
      outcomes[answer.status] = (outcomes[answer.status] ?? 0) + 1;
    }
  }
  const studio = dispatch({service: "studio", action: "summary"});
  const archive = dispatch({service: "archive", action: "summary"});
  return {
    outcomes,
    studio: daily(studio.occupied, tenant => catalog.studios.get(tenant) ?? catalog.default),
    archive: daily(archive.occupied, () => catalog.default)
  };
}

export function csv(lines, service) {
  const rows = ["service,tenant,day,cap,used,available,bookings"];
  for (const line of lines) {
    rows.push([service, line.tenant, line.day, line.cap, line.used, line.available,
               line.ids.join(" ")].join(","));
  }
  return rows.join("\n");
}

function main(argv) {
  const [path, format = "json", service] = argv;
  if (!path || !["json", "csv"].includes(format)) {
    throw new Error("usage: node utilization.mjs <batch> [json|csv] [studio|archive]");
  }
  const operations = JSON.parse(readFileSync(path, "utf8"));
  if (!Array.isArray(operations)) throw new Error("expected an array of operations");
  const result = statement(operations, readCatalog());
  if (format === "csv") {
    if (!["studio", "archive"].includes(service)) {
      throw new Error("CSV requires a service");
    }
    console.log(csv(result[service], service));
  } else {
    console.log(JSON.stringify(result, null, 2));
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    main(process.argv.slice(2));
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
