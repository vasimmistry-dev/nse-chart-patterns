# Contributing

Thanks for helping! Issues and pull requests are welcome.

1. Fork the repository and create a branch.
2. Set it up with `pip install -e ".[test]"`, then run `pytest -q`. All tests must pass.
3. If you add a pattern or change a rule:
   - add a test that **fires** and a near miss that **does not fire**, using hand-built bars (see `tests/conftest.py`);
   - document the exact rule in the README's *Rules* section;
   - use only data up to and including the signal bar (no look-ahead).
4. Keep the runtime free of dependencies (standard library only).
5. Keep pull requests small and focused, and describe *why* the change helps.

Please do not add buy or sell recommendations, price targets or performance claims to the code or the docs.
