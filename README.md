# feed-password-daemon

When run, feed-password-daemon:

- takes as arguments: a command that will be wrapped and its arguments
- reads a password on TTY and caches it
- then run this forever:
    - waits for `SIGUSR1` to be received
    - when `SIGUSR1` is received, it runs the wrapped command that was specified as argument
    - waits for a password prompt coming from the wrapped command
    - feeds the cached password to the wrapped command

## But why?

Here's an example, concrete use case:
[vdirsyncer](https://vdirsyncer.pimutils.org/en/stable/index.html) and [Thunderbird](https://www.thunderbird.net) can both perform periodic remote calendar synchronization (thanks to CalDAV) which is often password-protected.
However:

- being a GUI app, Thunderbird stays open, reads the password at start and caches it in RAM, so it can use the password when needed, without asking it again
- being a command-line, non-TUI app, vdirsyncer has no means to cache the password and is forced to ask it at every sync (possibly delegating to [pass](https://www.passwordstore.org), but the problem still stands)

This is where `feed-password-daemon` helps: it will cache the CalDAV password and wrap vdirsyncer to run it when desired and feeds it the password, without asking it again, à la Thunderbird.
`SIGUSR1` can then be sent on-demand to `feed-password-daemon` or periodically.

## Options

By default the initial password is read from the TTY.

- `--password-from-env=VARIABLE`: read password from environment VARIABLE instead of TTY
- `--password-from-file=FILE`: read password from FILE instead of TTY
- `--password-from-stdin`: read password from stdin instead of TTY
- `--confirm-password`: ask the password twice on TTY at startup, to avoid typos

Other:

- `--reply-to-prompt=PROMPT`: feed password when PROMPT is found (this is used to detect when the wrapped command requires a password)
- `--pid-file=FILE`: write pid of daemon to FILE
- `--check-at-start`: run the wrapped command a first time when `feed-password-daemon` is started, as if `SIGUSR1` was received, useful to verify the password validity as quickly as possible
