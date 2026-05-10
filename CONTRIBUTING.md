# Contributing to SLZ

Thank you for your interest in contributing to SLZ! We welcome contributions from everyone.

## Getting Started

1.  **Fork the repository** on GitHub.
2.  **Clone your fork** locally:
    ```bash
    git clone https://github.com/your-username/slz.git
    cd slz
    ```
3.  **Install in editable mode**:
    ```bash
    pip install -e .
    ```

## Running Tests

We use the standard `unittest` library. Run all tests with:

```bash
python3 -m unittest discover tests
```

Please ensure all tests pass before submitting a pull request.

## Submitting a Pull Request

1.  Create a new branch for your feature or bug fix:
    ```bash
    git checkout -b my-new-feature
    ```
2.  Commit your changes with descriptive messages.
3.  Push your branch to your fork.
4.  Open a Pull Request on the main `slz` repository.

## Code Style

- Follow PEP 8 guidelines.
- Add type hints to all new functions.
- Ensure any UI changes handle small terminal sizes gracefully (wrap `addstr` in try-except).

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
