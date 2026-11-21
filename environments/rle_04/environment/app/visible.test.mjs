import test from "node:test";
import assert from "node:assert/strict";
import {planner} from "./replay.mjs";
import {readCatalog} from "./common/limits.mjs";

test("Orchid can use its new studio allocation", () => {
  const dispatch = planner(readCatalog());
  const req = {action:"book", service:"studio", id:"sample", tenant:"orchid",
               units:7, day:"2025-04-02"};
  assert.deepEqual(dispatch(req), {status:"booked", id:"sample", remaining:1});
  assert.equal(dispatch(req).status, "replay");
});
