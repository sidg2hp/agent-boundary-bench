/** An in-memory journal scoped to one replay. Admission for every desk is decided here. */
import {equivalent} from "./request.mjs";
import {capFor} from "./limits.mjs";

export class Ledger {
  constructor(catalog) {
    this.catalog = catalog;
    this.byId = new Map();
    this.events = [];
  }

  usage(tenant, day) {
    let used = 0;
    for (const entry of this.byId.values()) {
      if (entry.tenant === tenant && entry.day === day && entry.active) {
        used += entry.units;
      }
    }
    return used;
  }

  inspect(id) {
    const entry = this.byId.get(id);
    return entry ? {...entry} : null;
  }

  /** Append a booking exactly as given. Backfills use this; it performs no admission. */
  post(request) {
    if (this.byId.has(request.id)) {
      return {status: "conflict", id: request.id};
    }
    this.byId.set(request.id, {...request, active: true});
    this.events.push({type: "booked", ...request});
    return {status: "imported", id: request.id};
  }

  reserve(request) {
    const previous = this.byId.get(request.id);
    if (previous) {
      if (!equivalent(previous, request)) {
        return {status: "conflict", id: request.id};
      }
      return {status: previous.active ? "replay" : "cancelled", id: request.id};
    }
    const cap = capFor(this.catalog, request);
    const used = this.usage(request.tenant, request.day);
    if (used + request.units > cap) {
      return {status: "full", id: request.id, remaining: Math.max(0, cap - used)};
    }
    this.post(request);
    return {status: "booked", id: request.id, remaining: cap - used - request.units};
  }

  cancel(id) {
    const entry = this.byId.get(id);
    if (!entry) return {status: "missing", id};
    if (!entry.active) return {status: "replay", id};
    entry.active = false;
    this.events.push({type: "cancelled", id});
    return {status: "cancelled", id};
  }

  summary() {
    const occupied = [];
    for (const entry of this.byId.values()) {
      if (entry.active) occupied.push({...entry});
    }
    occupied.sort((a, b) => a.id.localeCompare(b.id));
    return {occupied, events: this.events.map(event => ({...event}))};
  }
}
