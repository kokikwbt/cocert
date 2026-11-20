"""Enforce the declared query wall budget even if a solver overruns timeout.

Query time includes dispatch, solving, result checking, and timeout cleanup.
Worker startup is excluded; each query uses a fresh solver.
"""

import multiprocessing as mp
import time


def worker(connection):
    from .symbolic import decide

    connection.send("ready")
    while True:
        message = connection.recv()
        if message is None:
            break
        try:
            connection.send(decide(**message))
        except Exception as error:
            connection.send(dict(status="error", error=repr(error)))


class IsolatedSMT:
    def __init__(self):
        self.process = None
        self.connection = None
        self.start()

    def start(self):
        ctx = mp.get_context("spawn")
        self.connection, child = ctx.Pipe()
        self.process = ctx.Process(target=worker, args=(child,), daemon=True)
        self.process.start()
        child.close()
        if not self.connection.poll(30):
            self.close()
            raise RuntimeError("SMT worker failed to start")
        assert self.connection.recv() == "ready"

    def close(self):
        if self.process is not None:
            if self.process.is_alive():
                self.process.kill()
            self.process.join()
            self.process = None
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def decide(self, q, epsilon, total=None, timeout_ms=1000, seed=20261020, domain="real"):
        if self.process is None:
            self.start()
        start = time.perf_counter()
        self.connection.send(
            dict(q=q, epsilon=epsilon, total=total, timeout_ms=timeout_ms, seed=seed, domain=domain)
        )
        remaining = max(0, timeout_ms / 1000 - (time.perf_counter() - start))
        if self.connection.poll(remaining):
            result = self.connection.recv()
            if result["status"] == "error":
                raise RuntimeError(result["error"])
            result["worker_seconds"] = result["seconds"]
            result["seconds"] = time.perf_counter() - start
            result["wall_watchdog"] = False
            return result
        self.close()
        return dict(
            status="undecided",
            smt_status="unknown",
            reason="external_wall_timeout",
            allocation=None,
            rational_model_verified=False,
            construction_seconds=None,
            solve_seconds=None,
            seconds=time.perf_counter() - start,
            timeout_ms=timeout_ms,
            wall_watchdog=True,
        )
