import {booking, day} from "../common/request.mjs";

export function bookArchive(ledger, input) {
  return ledger.reserve(booking(input));
}

// Reading-room holds for the archive desk. Not dispatched from replay.mjs yet.
export function holdArchive(ledger, input) {
  const request = booking(input);
  const until = day(input.until);
  // TODO: refuse holds that outlast the retention window once the catalog carries one.
  return {...ledger.reserve(request), until};
}
