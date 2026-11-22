# Caption desk and roll printer

The caption desk keeps numbered or lettered versions of the wall text. Visitors and staff can both suggest titles on reader slips. The desk typesets a suggestion as a working proof so the curator can see it in context. The curator's selection for the wall is recorded in `edition`. The working comparison on the desk uses `proof`. Both are keys into the same object's `versions` table.

An object may go on display before the naming meeting. A null edition means the curator has chosen no title yet. Its wall label carries the accession number alone until a title is adopted.

The next shift delivers the press file straight to the wall-label printer. It accepts UTF-8 CSV with the header `stock,slot,room,work,caption`. Each installed work gets one label. Sort by stock, then room, then work code, ascending. Slots start at 1 on each stock roll. Use standard CSV quoting for captions containing punctuation or line breaks. Storage does not have a wall-label roll.

The counter records impressions on paper. It takes a roll file and the stack of copy slips at the desk. Its default stack is the intake basket, where anyone can leave a slip. The registrar commissions production extras on the batch docket. The copy for the collection file is part of the job even when the show has only a few works. A courtesy request stays in the basket for the registrar's next meeting unless the docket includes it. The counter records one wall impression per installed work plus one impression per physical extra. Submitting the same batch twice preserves the original counter readings.
