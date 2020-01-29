@Library('komodo') _

komodo(
    agent_labels: env.AGENT_LABELS,
    config_token_name: env.CONFIG_TOKEN_NAME,
    deploy: env.deploy,
    python_version: env.PYTHON_VERSION,
    release_base: env.RELEASE_BASE,
    build_python: "${env.PYTHON_VERSION == "2.7" ? env.BUILD_PYTHON_VERSION_27 : env.BUILD_PYTHON_VERSION_36}",
)
