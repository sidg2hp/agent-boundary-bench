# Caption desk and roll printer

The caption desk keeps numbered or lettered versions of the wall text. Visitors and staff can both suggest titles on reader slips. The desk typesets a suggestion as a working proof so the curator can see it in context. The curator's selection for the wall is recorded in `edition`. The working comparison on the desk uses `proof`. Both are keys into the same object's `versions` table.

An object may go on display before the naming meeting. A null edition means the curator has chosen no title yet. Its wall label carries the accession number alone until a title is adopted.

The next shift delivers the press file straight to the wall-label printer. It accepts UTF-8 CSV with the header `stock,slot,room,work,caption`. Each installed work gets one label. Sort by stock, then room, then work code, ascending. Slots start at 1 on each stock roll. Use standard CSV quoting for captions containing punctuation or line breaks. Storage does not have a wall-label roll.
