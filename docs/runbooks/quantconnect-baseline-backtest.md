# Runbook: baseline backtest on QuantConnect

The first runbook in this repo and the template for the rest: numbered steps, one action each, the exact label to click or value to type, one line on why, and what success looks like. Anything hard to undo is flagged before the step.

Time: about 40 minutes the first time, about 10 minutes for later runs. Cost: $0.

## Before you start

- The hold-out is 2025-01-01 onward. `IN_SAMPLE_YEAR` must be 2019 to 2024. The algorithm refuses anything later.
- You are pasting from `build/quantconnect/`, never from `src/`. The tree is rebuilt every time, so it always matches Git.

## A. Build the tree

1. Open a terminal in `C:\Dev\Git\auto_invest` and run:

   ```
   uv run python scripts/build_quantconnect_project.py
   ```

   Why: it copies the rubric byte for byte and turns the two TOML files into `settings_snapshot.py`, which the web editor can hold.

   Success: three lines, `wrote 13 files to …`, `rubric sha256 …`, `git commit …`. Copy the first eight characters of the hash and the commit into a scratch note; the research log needs both.

## B. Create the project (first run only)

2. Go to https://www.quantconnect.com/ and sign in.
3. Open the algorithm lab from the left menu and click the button to create a new project. Choose **Python** and name it `auto_invest`.

   Why: one project per strategy; every year's run reuses it.

   Success: the editor opens with a `main.py` containing a sample algorithm.

4. Click the **Explorer** icon (two overlapping pages) in the vertical strip on the right edge of the editor, expand **Workspace**, hover over its heading, and click the **New Directory** icon (a folder with a `+`). Type `rubric` and press Enter.

   Why: the rubric files use relative imports, so they must sit in a folder with an `__init__.py`, never loose.

   Success: an empty `rubric` folder appears under the project.

5. Inside `rubric`, add one file per file in `build\quantconnect\rubric\`, with the identical name, and paste each file's full contents. Do `__init__.py` first.

   Success: nine files under `rubric`, names matching the folder on disk exactly.

6. At the project root, add `lean_adapter.py`, `settings.py`, and `settings_snapshot.py` and paste each from `build\quantconnect\`.
7. Open the project's `main.py`, select all, delete, and paste `build\quantconnect\main.py`.

   Success: the project shows 13 files. Nothing else.

## C. Run one in-sample year

8. In `main.py`, find `IN_SAMPLE_YEAR = 2019` near the top. For the baseline leave it at 2019; for later years change only that number.

   Flag: never type 2025 or later. The algorithm will refuse, but the rule is yours, not the code's.

9. Click **Build**, then **Backtest**.

   Why: Build compiles; Backtest runs on the free node.

   Success: the backtest page opens and the equity chart starts drawing. A one-year run takes roughly 30 minutes.

10. When the run finishes, open the **Logs** tab. The first lines read `rubric 0.1.0 sha256 …`, then one `rubric/<file> <bytes> <hash>` line per rubric file, then `object store max size … bytes`.

    Why: the Logs tab fills only when the run ends; while it runs, watch the Cloud Terminal at the bottom of the editor for red text.

    Success: the first eight characters of the hash match your scratch note. If they do not, compare the nine `rubric/…` lines with the build output: the file whose hash differs is the one to re-paste. Re-paste it and run again.

11. Read the last four log lines: `decisions N`, `rejections {…}`, `orders N`, and `object store save failed: …`.

    Why: the free plan cannot write to the Object Store, so the per-decision file is not saved; the `rejections` line is the record. The last line is expected, not an error.

    Success: `orders` is under 10,000 and `decisions` is in the tens of thousands. Copy the `rejections` line to the scratch note. In the trades download (step 14), no trade's exit time is on a later date than its entry time.

12. On the **Overview** tab note Total Trades, Net Profit, and Drawdown.

## D. Download the evidence

13. On the backtest page open the **Orders** tab and use its download control to save the orders list next to your scratch note.

    Why: Phase 3 needs the trade list.

14. Use the same download control to save the trades list and the log file next to the orders list.

    Why: the trades list carries entry and exit times; the log file carries the hash lines and the `rejections` line.

    Success: three files next to your scratch note.

15. Only on a paid organization: open **Object Store** from the top-right organization menu, download `decisions.jsonl`, and count rejections locally with `uv run python scripts/count_rejections.py <path to decisions.jsonl>`. The free plan cannot write to the Object Store, so skip this step there.

## E. Record the run

16. Add one row to `docs/research-log.md`: today's date, the year, "baseline" (or what changed), the eight-character hash, trades, net return, max drawdown, the top rejecting check and its count.
17. Commit the research log:

    ```
    git add docs/research-log.md
    git commit -m "docs: research log, <year> <what changed>"
    ```

## Every later variation

Change the repo, commit, run section A, re-paste only the files whose contents changed (the build prints nothing about that, so compare in the editor), then sections C to E. If the rubric changed, step 10's hash changes too and the research log records the new one.
