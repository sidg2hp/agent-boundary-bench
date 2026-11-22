# Caption desk and roll printer

The caption desk keeps numbered or lettered versions of the wall text. Visitors and staff can both suggest titles on reader slips. The desk typesets a suggestion as a working proof so the curator can see it in context. The curator's selection for the wall is recorded in `edition`. The working comparison on the desk uses `proof`. Both are keys into the same object's `versions` table.

An object may go on display before the naming meeting. A null edition means the curator has chosen no title yet. Its wall label carries the accession number alone until a title is adopted.

The next shift delivers the press file straight to the wall-label printer. It accepts UTF-8 CSV with the header `stock,slot,room,work,caption`. Each installed work gets one label. Sort by stock, then room, then work code, ascending. Slots start at 1 on each stock roll. Use standard CSV quoting for captions containing punctuation or line breaks. Storage does not have a wall-label roll.

The desk press uses a four-position frame. Type can stay mounted between jobs. A pull makes an impression of every mounted form on the selected paper. The batch code identifies the pull in the production register. Each card also carries the job code of its own form. Empty positions consume paper and leave no card. The layout view displays the planned sheets without booking stock.

The production register `press.db` is the print room's stock account. It keeps one run per batch code, with every card and sheet that run used, and the press does not book a second layout under a code that already has a run. `press.py runs` lists the booked runs and who booked them. The print room writes a run off once its sheets are accounted for in the stock count.
