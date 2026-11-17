"""CI smoke test for a packaged Audiovane build.

    python ci_smoke.py <path to the packaged executable>

Starts the executable as `--mcp` (an MCP server on stdin/stdout), does the
handshake and lists the tools. It needs no models and no running app, so it
proves the frozen build starts, imports mcp_server and speaks the protocol.
Exits 0 on success, 1 on any failure. Stdlib only.
"""
import json
import subprocess
import sys
import threading

EXPECTED_TOOLS = {"speak", "list_voices", "transcribe", "status"}
TIMEOUT = 120      # a frozen build can take a while on its first start


def main(exe):
    env = dict(__import__("os").environ, AVS_MCP_NO_LAUNCH="1")   # never start the app from here
    p = subprocess.Popen([exe, "--mcp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, env=env)
    err = []
    threading.Thread(target=lambda: err.extend(p.stderr), daemon=True).start()
    watchdog = threading.Timer(TIMEOUT, p.kill)
    watchdog.start()

    def send(obj):
        p.stdin.write(json.dumps(obj) + "\n")
        p.stdin.flush()

    def reply():
        line = p.stdout.readline()
        if not line:
            raise RuntimeError("the server closed its output (crashed or timed out)")
        return json.loads(line)

    try:
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "ci-smoke", "version": "0"}}})
        info = reply()["result"]["serverInfo"]
        assert info["name"] == "audiovane", f"unexpected server name {info!r}"
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tools = {t["name"] for t in reply()["result"]["tools"]}
        missing = EXPECTED_TOOLS - tools
        assert not missing, f"tools missing: {sorted(missing)}"
        print(f"OK: {info['name']} {info['version']}, tools: {', '.join(sorted(tools))}")
        return 0
    except Exception as e:                       # noqa: BLE001 - report anything, exit 1
        print(f"FAIL: {type(e).__name__}: {e}")
        print("---- server stderr ----")
        print("".join(err)[-3000:])
        return 1
    finally:
        watchdog.cancel()
        try:
            p.stdin.close()
            p.wait(timeout=10)
        except Exception:                        # noqa: BLE001
            p.kill()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
