import {booking, day, span} from "../common/request.mjs";

export function bookArchive(ledger, input) {
  return ledger.reserve(booking(input));
}

// Reading-room holds for the archive desk. Not dispatched from replay.mjs yet.
export function holdArchive(ledger, input, catalog) {
  const request = booking(input);
  const until = day(input.until);
  if (span(request.day, until) > catalog.retention) {
    return {status: "refused", id: request.id};
  }
  return {...ledger.reserve(request), until};
}
