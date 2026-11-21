import {booking} from "../common/request.mjs";

export function bookArchive(ledger, input) {
  return ledger.reserve(booking(input));
}
