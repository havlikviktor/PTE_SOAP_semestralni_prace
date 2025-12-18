import itertools
import os
import subprocess
from dotenv import load_dotenv
from report_to_json import process_test_suites
from upload_to_elastic import Elastic


def run_soap_tests(test_runner_path, export_dir: str, soap_file: str, properties_params: str):
    try:
        result = subprocess.run(
            [test_runner_path, "-jMIr", "-f", export_dir, *properties_params.split(), soap_file],
            check=True,
            text=True,
            capture_output=True
        )
        print("Command output:", result.stdout)
    except subprocess.CalledProcessError as e:
        print("Error occurred:", e.stderr)


def test_params(test_runner_path, export_dir, soap_file):
    if not test_runner_path:
        print("Test runner path is not provided.")
        return False
    if not os.path.isfile(soap_file):
        print("Test runner file does not exist.")
        return False
    if not export_dir:
        print("Export directory path is not provided.")
        return False
    if not os.path.isdir(export_dir):
        print("Creating export directory.")
        os.makedirs(export_dir)
    return True


def generate_properties():
    usernameDELETE_values = ["pepazdepa", "pepa"]
    sla_values = ["700", "10"]
    slaGET_values = ["700", "10"]

    combinations = list(itertools.product(usernameDELETE_values, sla_values, slaGET_values))

    return combinations


def main():
    load_dotenv()
    test_runner_path = os.getenv("TEST_RUNNER_PATH", "")
    export_dir = os.getenv("EXPORT_DIR", "")
    soap_file = os.getenv("SOAP_TEST_FILE", "")
    if not test_params(test_runner_path, export_dir, soap_file):
        exit(-1)

    combinations = generate_properties()
    for round_num in range(5):
        usernameDELETE, sla, slaGET = combinations[round_num]
        properties_params = f"-PusernameDELETE={usernameDELETE} -Psla={sla} -PslaGET={slaGET}"
        print(f"Running tests with parameters: {properties_params}")
        export_path = os.path.join(export_dir, f"round_{round_num}")
        if not os.path.exists(export_path) or len(os.listdir(export_path)) == 0:
            run_soap_tests(test_runner_path, export_path, soap_file, properties_params)
        else:
            print(f"Round {round_num} already executed. Skipping...")

    json_output_dir = export_dir + "_json"
    process_test_suites(export_dir, json_output_dir)
    elastic = Elastic()
    elastic.write_directory_to_elastic("pte-index", "data_json")


if __name__ == "__main__":
    main()
