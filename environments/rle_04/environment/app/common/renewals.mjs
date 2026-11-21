/** Carry a previous reservation into the next period. Both desks share this import. */
import {booking} from "./request.mjs";
import {reserve} from "./limits.mjs";

export function renew(ledger, operation, catalog) {
  const previous = ledger.inspect(operation.previous);
  if (!previous || !previous.active) {
    return {status: "missing", id: operation.previous};
  }
  const next = booking({
    id: operation.id,
    day: operation.day,
    tenant: previous.tenant,
    units: operation.units ?? previous.units
  });
  return reserve(ledger, next);
}
