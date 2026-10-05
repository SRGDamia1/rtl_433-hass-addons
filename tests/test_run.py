"""Exercise the startup script with fake radios and Supervisor services."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASH = os.environ.get("TEST_BASH") or shutil.which("bash")
if os.name == "nt" and Path("C:/msys64/usr/bin/bash.exe").exists():
    BASH = "C:/msys64/usr/bin/bash.exe"

PRELUDE = r"""
export PATH="/usr/bin:$PATH"
bashio::services.available() { [[ "$TEST_MQTT" == 1 ]]; }
bashio::services() {
    case "$2" in
        host) echo broker ;; port) echo 1883 ;;
        username) echo user ;; password) echo password ;;
    esac
}
bashio::config() { [[ "$1" == rtl_433_conf_file ]] && printf '%s' "$TEST_LEGACY"; return 0; }
bashio::config.true() {
    case "$1" in
        retain) [[ "$TEST_RETAIN" == 1 ]] ;;
        allow_commands) [[ "$TEST_COMMANDS" == 1 ]] ;;
    esac
}
bashio::log.info() { echo "$*"; }
bashio::log.warning() { echo "$*"; }
bashio::log.error() { echo "$*"; }
bashio::log.fatal() { echo "$*"; }
mosquitto_pub() { printf '%s\n' "$*" >> "$TEST_ROOT/mqtt.log"; }
mock_radio() {
    cp "$2" "$TEST_ROOT/captured/$(basename "$2")"
    if [[ "$TEST_CRASH_ALL" == 1 ]] || grep -q crash "$2"; then
        sleep "${TEST_CRASH_DELAY:-1}"
        return 7
    fi
    trap 'echo stopped >> "$TEST_ROOT/stopped"; exit 0' TERM
    while :; do sleep 0.05; done
}
export -f mock_radio
# Fake only the JSON parser when jq is unavailable on the test host.
if ! command -v jq >/dev/null; then
    jq() {
        python -c 'import json,sys; x=json.load(sys.stdin); sys.exit(1) if not isinstance(x,str) or not x else None; print(x)'
    }
fi
"""

@unittest.skipUnless(BASH, "Bash is required")
class StartupTests(unittest.TestCase):
    def run_script(self, files, mqtt=True, retain=True, commands=False,
                   crash_all=False, legacy="", stdin="", crash_delay=1, stop_after=None):
        with tempfile.TemporaryDirectory(prefix="rtl433-test-", dir=ROOT / "tests") as directory:
            root = Path(directory)
            root_path = root.relative_to(ROOT).as_posix()
            conf_path = root_path + "/config"
            conf = root / "config"
            conf.mkdir()
            (root / "captured").mkdir()
            (root / "bin").mkdir()
            radio = root / "bin/rtl_433"
            radio.write_text('#!/usr/bin/env bash\nmock_radio "$@"\n', encoding="utf-8")
            radio.chmod(0o755)
            for name, content in files.items():
                (conf / name).write_text(content, encoding="utf-8")
            script = (ROOT / "rtl_433/run.sh").read_text(encoding="utf-8")
            script = script.replace('conf_directory="/config/rtl_433"',
                                    f'conf_directory="{conf_path}"')
            script = script.replace('runtime_directory="/tmp/rtl_433"',
                                    f'runtime_directory="{root_path}/runtime"')
            script = script.replace('conf_file="/config/$conf_file"',
                                    f'conf_file="{conf_path}/$conf_file"')
            runner = root / "run.sh"
            runner.write_text(PRELUDE + f'\nexport PATH="$PWD/{root_path}/bin:$PATH"\n' + script, encoding="utf-8")
            env = dict(os.environ, TEST_ROOT=root_path,
                       TEST_MQTT=str(int(mqtt)), TEST_RETAIN=str(int(retain)),
                       TEST_COMMANDS=str(int(commands)), TEST_CRASH_ALL=str(int(crash_all)),
                       TEST_LEGACY=legacy, TEST_CRASH_DELAY=str(crash_delay))
            args = [BASH, runner.as_posix()]
            if stop_after is not None:
                args = [BASH, "-c", 'export PATH="/usr/bin:$PATH"; "$1" "$2" & child=$!; sleep "$3"; kill -TERM "$child"; wait "$child"',
                        "test", BASH, runner.as_posix(), str(stop_after)]
            result = subprocess.run(args, input=stdin,
                                    text=True, capture_output=True, env=env, timeout=8, cwd=ROOT)
            captured = {p.name: p.read_text() for p in (root / "captured").iterdir()}
            mqtt_log = (root / "mqtt.log").read_text() if (root / "mqtt.log").exists() else ""
            stopped = (root / "stopped").exists()
            remaining = {p.name: p.read_text() for p in conf.iterdir()}
            return result, captured, mqtt_log, stopped, remaining

    def test_multiple_radios_stop_when_one_exits_and_keep_conf(self):
        result, captured, log, stopped, remaining = self.run_script({
            "crash radio.conf.template": "crash\nretain ${retain}",
            "healthy.conf.template": "healthy\n",
            "manual.conf": "do not delete\n",
        }, retain=False)
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertTrue(stopped)
        self.assertEqual(captured["crash radio.conf"], "crash\nretain 0\n")
        self.assertEqual(remaining["manual.conf"], "do not delete\n")
        self.assertIn("rtl_433/process_id/crash radio", log)

    def test_external_broker_skips_status_and_expands_retain(self):
        result, captured, log, _, _ = self.run_script({
            "radio.conf.template": "crash\nretain ${retain}\n"
        }, mqtt=False)
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertIn("retain 1", captured["radio.conf"])
        self.assertEqual(log, "")

    def test_exit_during_startup_is_detected(self):
        result, _, _, _, _ = self.run_script({
            "a.conf.template": "crash", "b.conf.template": "healthy"
        }, crash_delay=0)
        self.assertEqual(result.returncode, 7, result.stderr)

    def test_shutdown_terminates_radio(self):
        result, _, _, stopped, _ = self.run_script({
            "radio.conf.template": "healthy"
        }, stop_after=2)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(stopped)

    def test_missing_templates_fails_without_deleting_config(self):
        result, captured, _, _, remaining = self.run_script({"manual.conf": "keep"})
        self.assertEqual(result.returncode, 1)
        self.assertIn("No .conf.template files", result.stdout)
        self.assertFalse(captured)
        self.assertEqual(remaining["manual.conf"], "keep")

    def test_default_template_is_created_and_rendered(self):
        result, captured, _, _, remaining = self.run_script({}, crash_all=True)
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertIn("mqtt://broker:1883,user=user,pass=password,retain=1", captured["rtl_433.conf"])
        self.assertIn("${host}", remaining["rtl_433.conf.template"])
        self.assertIn("protocol -$1", remaining["rtl_433.conf.template"])

    def test_stdin_commands_require_opt_in(self):
        result, _, log, _, _ = self.run_script({"radio.conf.template": "crash"},
                                              stdin='"printf executed"\n')
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertNotIn("rtl_433/stdin", log)

    def test_enabled_stdin_rejects_objects_and_publishes_results(self):
        result, _, log, _, _ = self.run_script({"radio.conf.template": "crash"},
                        commands=True, stdin='{}\n"printf executed"\n')
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertIn("Ignoring stdin input", result.stdout)
        self.assertIn("rtl_433/stdin/result -m executed", log)

    def test_legacy_configuration_runs_directly(self):
        result, captured, log, _, remaining = self.run_script({"manual.conf": "legacy"},
                                             legacy="manual.conf", crash_all=True)
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertEqual(captured["manual.conf"], "legacy")
        self.assertEqual(log, "")
        self.assertEqual(remaining["manual.conf"], "legacy")

if __name__ == "__main__":
    unittest.main()
