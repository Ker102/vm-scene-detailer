# usage: bash .claude/skills/vm-new-building-part/scripts/run_build.sh <logname> [deliver_dir]
cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)" || exit 1
B="$HOME/AppData/Local/Programs/Blender Foundation/blender-5.2.2-windows-x64/blender.exe"
LOG="build/$1.log"
VM_DELIVER="$(cygpath -w "${2:-$PWD/build/stage}")" "$B" -b --python-exit-code 1 --python build_engine.py > "$LOG" 2>&1
echo "EXIT $?"
echo "PASS $(grep -c ': PASS' "$LOG") FAIL $(grep -c ': FAIL' "$LOG")"
grep -E ': FAIL|Traceback|Error:' "$LOG" | head -20
grep -E 'v2.9' "$LOG" | head -5
tail -2 "$LOG"
