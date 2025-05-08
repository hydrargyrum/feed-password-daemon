
import os
from pathlib import Path
import signal
import subprocess
import time

import pytest


@pytest.fixture
def runner():
	procs = []

	def run(args, env):
		procs.append(subprocess.Popen(
			[str(Path(__file__).parent.parent / "feed-password-daemon.py"), *args],
			env=env,
		))
		return procs[-1]

	yield run

	for proc in procs:
		with proc:
			proc.send_signal(signal.SIGINT)
			try:
				proc.wait(2)
			except subprocess.TimeoutExpired:
				proc.terminate()
				assert False, "process did not quit on SIGINT"


def wait_exists(proc, path, steps):
	for _ in range(steps):
		assert proc.poll() is None
		if path.exists():
			return
		time.sleep(.1)
	assert False, f"{path} does not exist"


def test_standard(tmp_path, runner):
	gotfile = tmp_path / "output.txt"
	proc = runner([
		"--password-from-env=FOO",
		f"--pid-file={tmp_path}/pid",
		"--",
		"sh",
		"-c",
		f"echo 'Password: ' && read -r reply && echo $reply > {gotfile}",
	], {**os.environ, "FOO": "secret"})

	wait_exists(proc, tmp_path / "pid", 20)
	assert not gotfile.exists()

	proc.send_signal(signal.SIGUSR1)
	wait_exists(proc, gotfile, 20)
	assert gotfile.exists()
	assert gotfile.read_text() == "secret\n"

	gotfile.unlink()
	proc.send_signal(signal.SIGUSR1)
	wait_exists(proc, gotfile, 20)
	assert gotfile.exists()
	assert gotfile.read_text() == "secret\n"


def test_pid_file(tmp_path, runner):
	pidfile = tmp_path / "pid"
	proc = runner([
		"--password-from-env=FOO",
		f"--pid-file={pidfile}",
		"--",
		"sh",
		"-c",
		":",
	], {**os.environ, "FOO": "secret"})

	wait_exists(proc, pidfile, 20)
	proc.send_signal(signal.SIGINT)
	proc.wait(2)
	assert not pidfile.exists()
