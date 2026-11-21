import {booking} from "../common/request.mjs";

export function bookStudio(ledger, input, catalog) {
  const request = booking(input);
  return ledger.reserve(request);
}
