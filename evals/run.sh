#!/usr/bin/env bash
# Run eval suites through the Claude CLI, locally or in CI.
#   evals/run.sh [suite|all] [mode] [model] [effort] [repetitions]
#   evals/run.sh lgtm-ish skill sonnet medium 3
#   evals/run.sh all
# Codex suites (pick-codex-crew*) need the codex provider and are not included in "all".
set -euo pipefail

suite="${1:-all}"
mode="${2:-skill}"
model="${3:-sonnet}"
effort="${4:-medium}"
reps="${5:-1}"

cd "$(dirname "$0")/.."

if [[ "$suite" == "all" ]]; then
  suites=(babysit-pr lgtm-ish pick-claude-crew pick-claude-crew-opus pick-crew)
else
  suites=("$suite")
fi

PYTHONDONTWRITEBYTECODE=1 python3 -m unittest evals/test_skill_eval.py

status=0
for s in "${suites[@]}"; do
  echo "::group::$s ($mode, $model/$effort, x$reps)"
  python3 evals/skill_eval.py run \
    --provider claude \
    --cases "evals/cases/$s.json" \
    --mode "$mode" \
    --model "$model" \
    --effort "$effort" \
    --repetitions "$reps" \
    --output-dir "evals/results/$s-$mode" > /dev/null || status=1
  python3 - "evals/results/$s-$mode/summary.json" <<'EOF'
import json, sys
d = json.load(open(sys.argv[1]))
rates = d["case_pass_rates"]
print(f'{d["skill"]}: {d["passed_repetitions"]}/{d["repetitions"]} runs fully passed, mean case pass rate {sum(rates.values())/len(rates):.2f}')
for case, rate in rates.items():
    if rate < 1:
        print(f"  {case}: {rate:.2f}")
EOF
  echo "::endgroup::"
done
exit $status
