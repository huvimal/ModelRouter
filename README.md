# ModelRouter

FastAPI prototype that routes Vietnamese support tasks between GPT-OSS 20B
and GPT-OSS 120B, with a benchmark for accuracy, latency and estimated usage cost.

## Run on Windows

The offline benchmark needs Python 3.11 and no extra packages.

```powershell
python evaluate.py
Get-Content reports/demo-test.json -Encoding utf8
```

Demo replays synthetic responses and token counts. It includes a simulated
timeout that triggers fallback and a valid but incorrect label that does not.
Demo metrics describe the fixture, and demo latency is null.

To run the API locally:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8505
```

Open http://127.0.0.1:8505/docs and try POST /route with this body:

```json
{
  "task": "extract_order",
  "text": "Tôi không còn nhớ mã đơn, có thể tra qua số điện thoại không?",
  "strategy": "router"
}
```

Without a key, the API recognizes exact bundled demo inputs only. For this
input it attempts 20B, falls back to 120B, and returns a successful null
value because the text has no order ID.

## Run a live comparison

```powershell
$routerKey = Read-Host "Groq API key" -AsSecureString
$env:GROQ_API_KEY = [System.Net.NetworkCredential]::new('', $routerKey).Password
python evaluate.py --mode live --case test-order
python evaluate.py --mode live
Get-Content reports/live-test.json -Encoding utf8
Remove-Item Env:GROQ_API_KEY
```

Start the API in a terminal with GROQ_API_KEY set to enable live requests there
as well. Live mode sends the input text to Groq. Use public or synthetic inputs.
The full test split makes 16 initial requests plus at most five fallbacks.
Use the three dev cases to check changes to routing rules. Keep the eight test
cases separate when measuring a revised rule, or create a new held-out set
if the bundled test results influence changes.

## Routing and fallback

The baseline uses 120B for every task. The router starts with 20B for
classification and order extraction inputs of at most 200 characters.
Calculation and longer inputs go to 120B. A transient provider failure or
invalid output from 20B can trigger one attempt with 120B. The code does not
retry the same model. Each provider call has a 20-second socket timeout.

The API validates the shape and type of the returned value. Order IDs must
also match the request text. Category and arithmetic correctness are scored
against reference answers by the benchmark. A wrong but valid result can
pass the API check, which is why the benchmark is separate.

## Read the report

- **Pass rate** uses all evaluated cases. A failed request counts as a miss.
- **P95 latency** is the nearest-rank percentile of live end-to-end timings,
  including fallbacks and failed cases. With eight cases it equals the maximum.
- **Known usage cost** sums estimates for attempts with reported token usage.
  Prices are a snapshot of Groq's public list prices on 2026-11-09.
- **Estimated cost per pass** divides total estimated cost by passed cases.
  It is null if any attempt lacks usage or if no case passed. Estimates
  exclude account-specific discounts and are not billing records.

Compare both strategies on the same cases and investigate any regression.
The paired run alternates which strategy goes first. A single small trial
is sensitive to traffic and variation in model responses.

## Live pilot results

| Strategy | Correct cases | Estimated usage cost (USD) | P95 latency | Fallbacks |
| --- | ---: | ---: | ---: | ---: |
| Always use GPT-OSS 120B | 8/8 | 0.00045195 | 763.4 ms | 0 |
| Route between GPT-OSS 20B and 120B | 8/8 | 0.00033630 | 831.1 ms | 0 |

In this run on eight synthetic test cases, routing used about 25.6% less
estimated token cost and had a P95 about 68 ms higher. With eight cases,
P95 is the slowest observed request. The live run did not trigger a fallback;
the offline demo exercises that path.

This is a localhost prototype with no authentication or persistent logs.
