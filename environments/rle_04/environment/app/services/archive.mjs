import {booking} from "../common/request.mjs";
import {reserve} from "../common/limits.mjs";

export function bookArchive(ledger, input) {
  return reserve(ledger, booking(input));
}
