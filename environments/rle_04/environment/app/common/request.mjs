/** Validate incoming booking requests before they reach the reservation engine. */
export class InputError extends Error {
  constructor(field, message) {
    super(field + " " + message);
    this.field = field;
  }
}

export function name(value, field) {
  if (typeof value !== "string" || !/^[a-z][a-z0-9-]{0,47}$/.test(value)) {
    throw new InputError(field, "must be a lowercase identifier");
  }
  return value;
}

export function quantity(value, field) {
  if (!Number.isSafeInteger(value) || value < 1) {
    throw new InputError(field, "must be a positive integer");
  }
  return value;
}

export function day(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    throw new InputError("day", "must use YYYY-MM-DD");
  }
  const date = new Date(value + "T00:00:00Z");
  if (Number.isNaN(date.getTime()) || date.toISOString().slice(0, 10) !== value) {
    throw new InputError("day", "is not a calendar date");
  }
  return value;
}

export function booking(value) {
  if (value == null || typeof value !== "object" || Array.isArray(value)) {
    throw new InputError("request", "must be an object");
  }
  return {
    id: name(value.id, "id"),
    tenant: name(value.tenant, "tenant"),
    day: day(value.day),
    units: quantity(value.units, "units")
  };
}

export function equivalent(a, b) {
  return a.id === b.id && a.tenant === b.tenant &&
         a.day === b.day && a.units === b.units;
}
