/** An in-memory journal scoped to one replay. Input operations are immutable. */
import {equivalent} from "./request.mjs";

export class Ledger {
  constructor() {
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

  reserve(request, cap) {
    const previous = this.byId.get(request.id);
    if (previous) {
      if (!equivalent(previous, request)) {
        return {status: "conflict", id: request.id};
      }
      return {status: previous.active ? "replay" : "cancelled", id: request.id};
    }
    const used = this.usage(request.tenant, request.day);
    if (used + request.units > cap) {
      return {status: "full", id: request.id, remaining: Math.max(0, cap - used)};
    }
    this.byId.set(request.id, {...request, active: true});
    this.events.push({type: "booked", ...request});
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
