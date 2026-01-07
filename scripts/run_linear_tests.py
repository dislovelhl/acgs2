import subprocess


def run_tests():
    cmd = [
        "python3",
        "-m",
        "pytest",
        "src/integration-service/integration-service/tests/integrations/test_linear_client.py",
        "-v",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        with open("pytest_results.log", "w") as f:
            f.write("STDOUT:\n")
            f.write(result.stdout)
            f.write("\nSTDERR:\n")
            f.write(result.stderr)
            f.write(f"\nReturn Code: {result.returncode}\n")
        print(f"Results written to pytest_results.log. Return code: {result.returncode}")
    except Exception as e:
        with open("pytest_results.log", "w") as f:
            f.write(f"Error running tests: {str(e)}")
        print(f"Error: {e}")


if __name__ == "__main__":
    run_tests()
