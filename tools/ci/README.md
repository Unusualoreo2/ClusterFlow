# Automatic tests on GitHub (not active yet)

`tests.yml` runs all tests on Python 3.12 and the cluster tool on Python 3.8 on every push.

It is parked here because GitHub only accepts files in `.github/workflows/` from a sign-in with the
`workflow` permission. To activate it:

1. `gh auth refresh -h github.com -s workflow` and approve the one-time code at https://github.com/login/device
2. Move the file: `mkdir .github\workflows` then `git mv tools/ci/tests.yml .github/workflows/tests.yml`
3. Commit: the automatic backup pushes it and GitHub starts running the tests.

Do not commit it to `.github/workflows/` before step 1: every automatic push would be rejected.
