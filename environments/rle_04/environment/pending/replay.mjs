import {readFileSync, renameSync, writeFileSync} from "node:fs";
import {createInterface} from "node:readline";
import {pathToFileURL} from "node:url";
import {Ledger} from "./common/ledger.mjs";
import {readCatalog} from "./common/limits.mjs";
import {renew} from "./common/renewals.mjs";
import {InputError, booking, day, name} from "./common/request.mjs";
import {bookStudio} from "./services/studio.mjs";
import {bookArchive} from "./services/archive.mjs";

export function planner(catalog) {
  const ledgers = {studio: new Ledger(catalog), archive: new Ledger(catalog)};
  return function dispatch(op) {
    if (!op || !Object.hasOwn(ledgers, op.service)) {
      throw new InputError("service", "must be studio or archive");
    }
    const ledger = ledgers[op.service];
    switch (op.action) {
      case "renew":
        return renew(ledger, op);
      case "book":
        return op.service === "studio"
          ? bookStudio(ledger, op, catalog)
          : bookArchive(ledger, op);
      case "import":
        return ledger.post(booking(op));
      case "cancel":
        return ledger.cancel(name(op.id, "id"));
      case "lookup":
        return ledger.inspect(name(op.id, "id"));
      case "usage":
        return {units: ledger.usage(name(op.tenant, "tenant"), day(op.day))};
      case "summary":
        return ledger.summary();
      default:
        throw new InputError("action", "is unknown");
    }
  };
}

export function apply(dispatch, operation) {
  try {
    return dispatch(operation);
  } catch (error) {
    if (error instanceof InputError) {
      return {status: "invalid", field: error.field};
    }
    throw error;
  }
}

async function main(argv) {
  const [command, ...args] = argv;
  const catalog = readCatalog();
  if (command === "stage" && args.length === 1) {
    // Quarterly coordinated releases normally carry both distribution records.
    const release = name(args[0], "release");
    const file = "fixtures/release-queue.json";
    const queue = JSON.parse(readFileSync(file, "utf8"));
    for (const service of ["studio", "archive"]) {
      if (queue.some(row => row.release === release && row.service === service)) continue;
      const allocations = service === "studio" ? Object.fromEntries(catalog.studios) : {};
      const record = {release, service, default:catalog.default, allocations};
      if (service === "archive") record.retention = 30;
      queue.push(record);
    }
    writeFileSync(file + ".tmp", JSON.stringify(queue, null, 2) + "\n");
    renameSync(file + ".tmp", file);
    console.log(JSON.stringify(queue));
    return;
  }
  if (command === "catalog" && !args.length) {
    console.log(JSON.stringify({default: catalog.default, studios: Object.fromEntries(catalog.studios)}));
    return;
  }
  const dispatch = planner(catalog);
  if (command === "batch" && args.length === 1) {
    const operations = JSON.parse(readFileSync(args[0], "utf8"));
    if (!Array.isArray(operations)) throw new Error("expected an array");
    console.log(JSON.stringify(operations.map(op => apply(dispatch, op))));
    return;
  }
  if (command === "stream" && !args.length) {
    const lines = createInterface({input: process.stdin, crlfDelay: Infinity});
    for await (const line of lines) {
      if (line.trim()) console.log(JSON.stringify(apply(dispatch, JSON.parse(line))));
    }
    return;
  }
  throw new Error("usage: node replay.mjs catalog | batch <file> | stream | stage <release>");
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main(process.argv.slice(2)).catch(error => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
