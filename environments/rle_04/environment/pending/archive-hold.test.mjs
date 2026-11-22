import test from "node:test";
import assert from "node:assert/strict";
import {Ledger} from "./common/ledger.mjs";
import {readCatalog} from "./common/limits.mjs";
import {holdArchive} from "./services/archive.mjs";

const hold = {id:"room-b", tenant:"orchid", units:2, day:"2025-04-02", until:"2025-04-05"};

test("a reading-room hold reserves its units until the release day", () => {
  const held = holdArchive(new Ledger(readCatalog()), hold);
  assert.equal(held.status, "booked");
  assert.equal(held.until, "2025-04-05");
});

test("a hold that outlasts the retention window is refused", () => {
  const held = holdArchive(new Ledger(readCatalog()), {...hold, until:"2025-09-30"});
  assert.equal(held.status, "refused");
});
