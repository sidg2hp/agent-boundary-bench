import {booking} from "../common/request.mjs";
import {reserve} from "../common/limits.mjs";

export function bookStudio(ledger, input, catalog) {
  const request = booking(input);
  return reserve(ledger, request);
}
