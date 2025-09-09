import pytest
import pytest_html

# Hook to add extra information into pytest-html reports
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    # Only log extra for test call (not setup/teardown)
    if report.when == "call":
        extras = getattr(report, "extras", [])

        # Attach custom test info if available
        if "response_data" in item.funcargs:
            response_data = item.funcargs["response_data"]
            extras.append(pytest_html.extras.text(str(response_data), "Response Data"))

        report.extras = extras
