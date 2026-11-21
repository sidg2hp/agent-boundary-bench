import {readFileSync} from "node:fs";
import {quantity} from "./request.mjs";

const path = new URL("../config/catalog.json", import.meta.url);

export function readCatalog(location = path) {
  const obj = JSON.parse(readFileSync(location, "utf8"));
  const cap = quantity(obj.default, "default");
  const overrides = new Map();
  for (const [tenant, value] of Object.entries(obj.studios)) {
    overrides.set(tenant, quantity(value, "studio quota"));
  }
  return {default: cap, studios: overrides};
}

export function reserve(ledger, request, cap = readCatalog().default) {
  return ledger.reserve(request, cap);
}
