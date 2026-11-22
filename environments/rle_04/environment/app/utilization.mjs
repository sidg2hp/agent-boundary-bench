/** Build a daily utilization statement from a replay without changing its journal. */
import {readFileSync, renameSync, writeFileSync} from "node:fs";
import {pathToFileURL} from "node:url";
import {apply, planner} from "./replay.mjs";
import {readCatalog} from "./common/limits.mjs";
import {day, name} from "./common/request.mjs";

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

function calendarKey(service, tenant, date) {
  return [service, tenant, date].join("/");
}

function calendarSource(path) {
  const source = JSON.parse(readFileSync(path, "utf8"));
  name(source.edition, "edition");
  if (!Array.isArray(source.operations) || !Array.isArray(source.subscriptions)) {
    throw new Error("expected a replay and subscription list");
  }
  const days = [...new Set(source.days.map(day))].sort();
  if (!days.length) throw new Error("empty diary");
  return {...source, days};
}

export function projectCalendar(source, catalog) {
  const result = statement(source.operations, catalog);
  const records = new Map();
  for (const subscription of source.subscriptions) {
    const {service, tenant} = subscription;
    if (!["studio","archive"].includes(service)) throw new Error("unknown desk");
    name(tenant, "tenant");
    const cap = service === "studio" ? (catalog.studios.get(tenant) ?? catalog.default) : catalog.default;
    const usage = new Map(result[service].filter(r => r.tenant === tenant).map(r => [r.day,r.used]));
    for (const date of source.days) {
      const id = calendarKey(service, tenant, date);
      if (records.has(id)) throw new Error("ambiguous subscription: " + id);
      const used = usage.get(date) ?? 0;
      records.set(id, {service, tenant, day:date, edition:source.edition,
                       cap, used, available:Math.max(0,cap - used)});
    }
  }
  return [...records.values()];
}

export function replaceCalendar(path, records) {
  const rows = JSON.parse(readFileSync(path, "utf8"));
  const byKey = new Map();
  for (const row of rows) {
    const key = calendarKey(row.service, row.tenant, row.day);
    if (byKey.has(key)) throw new Error("duplicate existing calendar row " + key);
    byKey.set(key, row);
  }
  for (const row of records) {
    byKey.set(calendarKey(row.service, row.tenant, row.day), row);
  }
  const temp = path + "." + process.pid + ".tmp";
  writeFileSync(temp, JSON.stringify([...byKey.values()], null, 2) + "\n", {flag:"wx"});
  renameSync(temp, path);
}

function calendarCommand(argv) {
  const [operation, sourcePath, destination] = argv;
  if (argv.length !== 3) throw new Error("expected operation, source and calendar path");
  const source = calendarSource(sourcePath);
  const projected = projectCalendar(source, readCatalog());
  if (operation === "preview-calendar") {
    console.log(JSON.stringify(projected));
    return;
  }
  if (operation === "rebuild-calendar") {
    replaceCalendar(destination, projected);
    console.log(JSON.stringify({edition:source.edition, rows:projected.length}));
    return;
  }
  throw new Error("unknown calendar operation " + operation);
}

function main(argv) {
  if (["preview-calendar","rebuild-calendar","publish-calendar"].includes(argv[0])) {
    calendarCommand(argv);
    return;
  }
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
