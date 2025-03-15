from nox import Session, options, project, session

options.default_venv_backend = "uv"
options.reuse_venv = "yes"
options.sessions = ["tests"]

PYPROJECT = project.load_toml("pyproject.toml")
PYTHON_VERSIONS = project.python_versions(PYPROJECT)


@session(python=PYTHON_VERSIONS)
def test(session: Session):
    session.run_install(
        "uv",
        "sync",
        "--group=test",
        "--no-dev",
        env={"UV_PROJECT_ENVIRONMENT": session.virtualenv.location},
    )

    if session.posargs:
        test_files = session.posargs
    else:
        test_files = ["tests"]

    session.run("pytest", *test_files)


@session(python=PYTHON_VERSIONS)
def cov(session: Session):
    session.run_install(
        "uv",
        "sync",
        "--group=test",
        "--group=cov",
        "--no-dev",
        env={"UV_PROJECT_ENVIRONMENT": session.virtualenv.location},
    )

    if session.posargs:
        test_files = session.posargs
    else:
        test_files = ["tests"]

    session.run(
        "pytest",
        "--cov=.",
        "--cov-branch",
        "--cov-report=xml",
        "--cov-report=html",
        *test_files,
    )
